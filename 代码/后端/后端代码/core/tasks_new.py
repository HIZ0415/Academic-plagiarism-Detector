"""Celery pipeline (GPU + CPU) for fake‑image‑detector
====================================================

此文件演示 **完整** 的 3‑阶段拆分方案：
    1. `fetch_batch`  与 AI/GPU 服务通信（独占 GPU）
    2. `process_single_result`  CPU & I/O 后处理（并行）
    3. `finalize_task`  统计收尾、生成报告

> ❗ 如需拆文件，可把辅助函数移到 utils.py / services.py，
>   为了示例完整性全部写在同一文件。
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
from celery import shared_task, group, chord
from django.db import transaction
from django.utils import timezone

# ───────────────────────────────────────────────────────────────────────────────
#  Model & 服务导入
#   实际项目请根据 app 名称修改 import 路径即可。
# ───────────────────────────────────────────────────────────────────────────────
from core.models import (
    DetectionResult,      # 主结果表
    SubDetectionResult,   # 子检测方法结果表
    DetectionTask,        # 整体任务表
)
from .utils.report_generator import generate_detection_task_report
from .utils.image_saver import save_ndarray_as_image
from .utils.fanyi import fanyi_text
from .utils.ai_result_schema import (
    AIResultFormatError,
    is_ai_batch_complete,
    normalize_ai_batch_results,
)
from .utils.ai_gateway import AIGatewayError, reconnect_ai_gateway, run_image_detection_batch

from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_task_completion_notification(user, task_id):
    channel_layer = get_channel_layer()
    group_name = f"user_{user.id}_notifications"  # 为每个用户创建唯一的组名

    # 获取当前时间并格式化为字符串
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 创建消息内容，分开任务ID和完成时间
    notification_data = {
        'task_id': task_id,
        'completion_time': current_time
    }

    # # wyt shit here
    # send_ai_detection_complete_notification(user.id, user.username,task_id)

    # 发送通知到 WebSocket 群组
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',  # 调用消费者中的 send_notification 方法
            'notification': notification_data  # 使用 JSON 格式传递字段
        }
    )

# 若使用 redis-lock 之类库，也可以导入 lock 来替代 queue=\'ai\' 的单并发做法
# from redis_lock import Lock

# ───────────────────────────────────────────────────────────────────────────────
# 1.  GPU 阶段 – 串行
# ───────────────────────────────────────────────────────────────────────────────

@shared_task(queue="ai", bind=True, acks_late=True, max_retries=3, default_retry_delay=15)
def fetch_batch(
    self,
    detection_result_ids: List[int],
    batch_dir: str | Path,
    image_num: int,
    task_pk: int,
) -> None:
    """同 AI 服务器通信，只负责拿到整批结果，不做大量 I/O。"""

    t0 = time.time()
    batch_dir = Path(batch_dir)
    zip_path = batch_dir / "img.zip"
    data_path = batch_dir / "data.json"

    # 1️⃣  标记任务 & 子结果为 in_progress（DB I/O 很少，可以接受）
    dr_qs = (
        DetectionResult.objects.select_related("detection_task")
        .filter(id__in=detection_result_ids)
        .order_by("id")
    )
    if not dr_qs:
        return

    task = dr_qs[0].detection_task
    if task.status != "in_progress":
        task.status = "in_progress"
        task.save(update_fields=["status"])
    dr_qs.update(status="in_progress")

    # 2️⃣  GPU / 网络 调用
    try:
        results = run_image_detection_batch(zip_path, data_path)
    except AIGatewayError as exc:
        raise self.retry(exc=exc)
    retry_count = 0
    while not is_ai_batch_complete(results, len(detection_result_ids)) and retry_count < 3:
        reconnect_ai_gateway()
        retry_count += 1
        try:
            results = run_image_detection_batch(zip_path, data_path)
        except AIGatewayError as exc:
            raise self.retry(exc=exc)

    if not is_ai_batch_complete(results, len(detection_result_ids)):
        raise self.retry(exc=RuntimeError("AI 服务器返回为空或结果数量不匹配"))

    try:
        normalized_results = normalize_ai_batch_results(results, expected_count=len(detection_result_ids))
    except AIResultFormatError as exc:
        raise self.retry(exc=exc)

    # 3️⃣  将每张图片拆成独立 payload，fan‑out 给 CPU worker
    subtasks = []
    for dr_id, one_result in zip(detection_result_ids, normalized_results):
        subtasks.append(process_single_result.s(dr_id, one_result))

    # 4️⃣  fan‑in：全部子任务结束后触发收尾
    chord(group(subtasks), finalize_task.s(task_pk, image_num)).delay()
    # finalize_task(task_pk, image_num)

    # 5️⃣  （可选）清理批次临时文件 – 放到 GPU 任务尾部即可
    try:
        zip_path.unlink(missing_ok=True)
        data_path.unlink(missing_ok=True)
        batch_dir.rmdir()  # 目录为空才会删除
    except OSError:
        pass

    print("[fetch_batch] 完成，用时", time.time() - t0, "s")


# ───────────────────────────────────────────────────────────────────────────────
# 2.  CPU & I/O 阶段 – 并行
# ───────────────────────────────────────────────────────────────────────────────

@shared_task(queue="cpu", acks_late=True)
def process_single_result(dr_pk: int, result_dict: Dict[str, Any]) -> bool:
    """把单张图片的检测结果写入数据库 & 文件系统。"""

    dr = DetectionResult.objects.select_related("image_upload").get(pk=dr_pk)

    # --- 还原 ndarray ---------------------------------------
    ela_np = np.array(result_dict["ela"], dtype=np.float32)
    llm_img_np = None
    if result_dict.get("llm_img") is not None:
        llm_img_np = np.array(result_dict["llm_img"], dtype=np.float32)

    # 2‑1  文件写入（磁盘 I/O）
    ela_path = save_ndarray_as_image(ela_np, subdir="ela_results", prefix=f"ela_{dr_pk}")
    llm_image_path = None
    if llm_img_np is not None:
        # print('llm info:')
        # print(type(llm_img_np))
        # print(llm_img_np.shape)
        # print(llm_img_np)
        # # 保存llm_img_np
        # import pickle
        # with open(f"llm_img_np.pkl", "wb") as f:
        #     pickle.dump(llm_img_np, f)
        llm_image_path = save_ndarray_as_image(llm_img_np, subdir="llm_results", prefix=f"llm_{dr_pk}")

    # 2‑2  更新 DetectionResult 主表
    dr.is_fake = result_dict["overall_is_fake"]
    dr.confidence_score = result_dict["overall_confidence"]
    dr.llm_judgment = fanyi_text(result_dict["llm_text"])
    dr.ela_image = ela_path
    if llm_image_path:
        dr.llm_image = llm_image_path
    dr.exif_photoshop = result_dict["exif_flags"]["photoshop"]
    dr.exif_time_modified = result_dict["exif_flags"]["time_modified"]
    dr.detection_time = timezone.now()
    dr.status = "completed"
    dr.save(
        update_fields=[
            "is_fake",
            "confidence_score",
            "llm_judgment",
            "ela_image",
            "llm_image",
            "exif_photoshop",
            "exif_time_modified",
            "detection_time",
            "status",
        ]
    )

    # 2‑3  子检测方法批量写入
    subs = []
    for sub in result_dict["sub_method_results"]:
        mask_path = save_ndarray_as_image(
            np.array(sub["mask"]), subdir="masks", prefix=f"mask_{sub['method']}_{dr_pk}"
        )
        subs.append(
            SubDetectionResult(
                detection_result=dr,
                method=sub["method"],
                probability=sub["prob"],
                mask_image=mask_path,
                mask_matrix=sub["mask"],
            )
        )
    SubDetectionResult.objects.bulk_create(subs, ignore_conflicts=True)

    # 2‑4  更新 ImageUpload 标志位
    iu = dr.image_upload
    iu.isFake = dr.is_fake
    iu.isDetect = True
    iu.save(update_fields=["isFake", "isDetect"])

    return True


# ───────────────────────────────────────────────────────────────────────────────
# 3.  收尾阶段 – 判断任务是否全部完成，然后生成报告 & 通知
# ───────────────────────────────────────────────────────────────────────────────

@shared_task(queue="cpu", acks_late=True)
def finalize_task(_chord_results: list | None, task_pk: int, image_num: int, _=None) -> None:  # body 签名固定
    task = DetectionTask.objects.get(pk=task_pk)
    completed = (
        DetectionResult.objects.filter(detection_task=task, status="completed").count()
    )
    if completed != image_num:
        # 说明还有图片未完成，直接返回即可
        return

    # 全部完成 – 原子操作
    with transaction.atomic():
        task.status = "completed"
        task.completion_time = timezone.now()
        task.save(update_fields=["status", "completion_time"])
        generate_detection_task_report(task)

    send_task_completion_notification(task.user, task_pk)


# ───────────────────────────────────────────────────────────────────────────────
#  Helper：把 get_result 的原始大 tuple 拆成易于序列化的 dict
# ───────────────────────────────────────────────────────────────────────────────

def _extract_single_result(raw_results: Any, idx: int) -> Dict[str, Any]:
    """Backward-compatible helper for callers that still import the old parser."""
    return normalize_ai_batch_results(raw_results)[idx]


# ───────────────────────────────────────────────────────────────────────────────
#  CELERY 启动示例（写在 README 或部署脚本）
# ───────────────────────────────────────────────────────────────────────────────
# GPU 专用 worker（始终 1 并发）
#   celery -A fake_image_detector worker -Q ai --concurrency 1 -n ai@%h
# CPU/I‑O worker（并发可调）
#   celery -A fake_image_detector worker -Q cpu,default --concurrency 8 -n cpu@%h
# ----------------------------------------------------------------------------
