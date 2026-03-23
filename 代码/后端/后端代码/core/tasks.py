from celery import shared_task
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from .models import DetectionResult, SubDetectionResult, DetectionTask
import time, json
import numpy as np
import pickle
from django.conf import settings
from pathlib import Path

from .utils.report_generator import generate_detection_task_report
from .utils.image_saver import save_ndarray_as_image
from .utils.fanyi import fanyi_text
from .call_figure_detection import get_result, reconnect

from django.db import transaction
import shutil
from PIL import Image
import time




from .util import send_ai_detection_complete_notification

def process_image(source_path, target_path):
    """处理图片复制和格式转换"""
    target_path = Path(target_path)
    target_dir = target_path.parent

    # 确保目标目录存在
    target_dir.mkdir(parents=True, exist_ok=True)

    # 获取文件扩展名并比较
    src_ext = Path(source_path).suffix.lower()
    tgt_ext = target_path.suffix.lower()

    try:
        if src_ext == tgt_ext:
            # 直接复制文件
            shutil.copy(source_path, target_path)
        else:
            # 使用Pillow转换格式
            with Image.open(source_path) as img:
                # 转换CMYK模式为RGB
                if img.mode == 'CMYK':
                    img = img.convert('RGB')
                # 处理PNG的透明度问题（可选）
                if tgt_ext == '.png' and img.mode == 'RGBA':
                    img.load()  # 解决"too many palette entries"错误
                img.save(target_path, format=tgt_ext[1:].upper())  # 去掉扩展名前的点并转大写
        return True
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return False


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task
def run_ai_detection(detection_result_id, cmd_block_size=64, urn_k=0.3, if_use_llm=False):
    """单张图片的检测流程"""
    dr = DetectionResult.objects.select_related('detection_task').get(id=detection_result_id)

    # 先将dr的status改为in_progress
    dr.status = 'in_progress'
    dr.save(update_fields=['status'])

    task = dr.detection_task
    task.status = 'in_progress'
    task.save(update_fields=['status'])

    # ─── 1. 获取检测结果 ───────────────
    path = dr.image_upload.image.path
    new_path = Path(settings.MEDIA_ROOT) / 'temp' / 'img2.png'
    # 将位于path的图片复制到media下的temp目录，命名为img2.png
    process_image(path, new_path)

    data = {'cmd_block_size': cmd_block_size, 'urn_k': urn_k, 'if_use_llm': if_use_llm}
    data_path = Path(settings.MEDIA_ROOT) / 'temp' / 'data.json'
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    result = get_result(new_path, data_path)
    while result is None:
        reconnect()
        result = get_result(new_path, data_path)
    # PICKLE_PATH = Path(settings.BASE_DIR) / 'fake_image_detector' / 'core' / 'data.pkl'
    # with PICKLE_PATH.open('rb') as f:
    #     result = pickle.load(f)

    if result[0][1] is not None:
        llm_text = result[0][1][0][0]['outputs']
        llm_text = fanyi_text(result[0][1][0][0]['outputs'])
        llm_img = result[0][1][1]  # (n, m, 3)的ndarray，表示llm的mask图
    else:
        llm_text = '无'
        llm_img = None
    ela_result = result[1][1]  # (266, 126)的ndarray，表示mask图
    exif_result = result[2][1]
    urn_splicing_result = result[4][1]
    urn_blurring_result = result[5][1]
    urn_bruteforce_result = result[6][1]
    urn_contrast_result = result[7][1]
    urn_inpainting_result = result[8][1]

    # 存储ela_result
    ela_img_path = save_ndarray_as_image(ela_result,
                                            subdir='ela_results',
                                            prefix=f"ela_{dr.id}")

    # 存储llm_img
    if llm_img is not None:
        llm_img_path = save_ndarray_as_image(llm_img,
                                            subdir='llm_results',
                                            prefix=f"llm_{dr.id}")

    # 检测返回结果
    bar = 0.5
    overall_is_fake        = urn_splicing_result[1].tolist()[0] > bar or urn_blurring_result[1].tolist()[0] > bar or urn_bruteforce_result[1].tolist()[0] > bar or urn_contrast_result[1].tolist()[0] > bar or urn_inpainting_result[1].tolist()[0] > bar or exif_result is not None
    overall_confidence     = max(urn_splicing_result[1].tolist()[0], urn_blurring_result[1].tolist()[0], urn_bruteforce_result[1].tolist()[0], urn_contrast_result[1].tolist()[0], urn_inpainting_result[1].tolist()[0])
    # llm_text               = "The image appears authentic."
    # ela_img_path           = 'ela_results/{}.png'.format(dr.image_upload.id)
    exif_flags             = {'photoshop': False, 'time_modified': False}
    if exif_result is not None:
        if "使用了Photoshop进行修改" in exif_result:
            exif_flags['photoshop'] = True
        if "修改了拍摄或制作时间" in exif_result:
            exif_flags['time_modified'] = True
        overall_confidence = 1.0

    # 示例 mask，实际应由模型生成，为0-1的256x256矩阵
    mask_splicing_np = urn_splicing_result[0][0]
    mask_splicing_path = save_ndarray_as_image(mask_splicing_np, subdir='masks', prefix=f"mask_splicing_{dr.id}")
    mask_blurring_np = urn_blurring_result[0][0]
    mask_blurring_path = save_ndarray_as_image(mask_blurring_np, subdir='masks', prefix=f"mask_blurring_{dr.id}")
    mask_bruteforce_np = urn_bruteforce_result[0][0]
    mask_bruteforce_path = save_ndarray_as_image(mask_bruteforce_np, subdir='masks', prefix=f"mask_bruteforce_{dr.id}")
    mask_contrast_np = urn_contrast_result[0][0]
    mask_contrast_path = save_ndarray_as_image(mask_contrast_np, subdir='masks', prefix=f"mask_contrast_{dr.id}")
    mask_inpainting_np = urn_inpainting_result[0][0]
    mask_inpainting_path = save_ndarray_as_image(mask_inpainting_np, subdir='masks', prefix=f"mask_inpainting_{dr.id}")

    sub_method_results = [
        # (method_key, prob, mask_img_path, mask_matrix_ndarray)
        ('splicing', urn_splicing_result[1].tolist()[0], mask_splicing_path, mask_splicing_np),
        ('blurring', urn_blurring_result[1].tolist()[0], mask_blurring_path, mask_blurring_np),
        ('bruteforce', urn_bruteforce_result[1].tolist()[0], mask_bruteforce_path, mask_bruteforce_np),
        ('contrast', urn_contrast_result[1].tolist()[0], mask_contrast_path, mask_contrast_np),
        ('inpainting', urn_inpainting_result[1].tolist()[0], mask_inpainting_path, mask_inpainting_np)
    ]
    # ─────────────────────────────────────────────────────────────────────

    # ─── 2. 更新 DetectionResult 主表 ───────────────────────────────────
    dr.is_fake          = overall_is_fake
    dr.confidence_score = overall_confidence
    dr.llm_judgment     = llm_text
    dr.ela_image        = ela_img_path
    if llm_img is not None:
        dr.llm_image        = llm_img_path
    dr.exif_photoshop   = exif_flags['photoshop']
    dr.exif_time_modified = exif_flags['time_modified']
    dr.detection_time   = timezone.now()
    dr.save()

    # ─── 3. 子检测方法结果逐条写入子表 ────────────────────────────────
    for method_key, prob, mask_img, mask_np in sub_method_results:
        SubDetectionResult.objects.update_or_create(
            detection_result=dr, method=method_key,
            defaults={
                'probability': prob,
                'mask_image': mask_img,
                'mask_matrix': json.loads(
                    json.dumps(mask_np.tolist()))  # ndarray→list→json
            }
        )
    dr.status = 'completed'
    dr.save(update_fields=['status'])

    # 更新dr对应的imageupload表的isFake参数和isDetect参数
    image_upload = dr.image_upload
    image_upload.isFake = overall_is_fake
    image_upload.isDetect = True
    image_upload.save(update_fields=['isFake', 'isDetect'])

    # ─── 4. 若同一 DetectionTask 全部图片都完成，则标记任务完成 ─────────
    task = dr.detection_task
    # 获取任务中的所有检测结果
    all_results = DetectionResult.objects.filter(detection_task=task)
    if all(result.status == 'completed' for result in all_results):  # 使用正确的判断方式
        # 使用事务确保任务状态的更新被提交到数据库
        with transaction.atomic():
            task.status = 'completed'  # 设置任务状态为已完成
            task.completion_time = timezone.now()  # 记录完成时间
            task.save(update_fields=['status', 'completion_time'])
            generate_report_for_task(task.id)

            print('send message')

        # 通知用户任务已完成
        send_task_completion_notification(task.user, task.id)

    return f"Detection finished for DetectionResult #{dr.id}"

from datetime import datetime

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


@shared_task
def generate_report_for_task(task_id):
    task = DetectionTask.objects.get(id=task_id)
    return generate_detection_task_report(task)


import os
# tasks.py
@shared_task
def run_ai_detection_batch(detection_result_ids, batch_dir, image_num):
    """
    detection_result_ids : 与 zip 内图片顺序一一对应
    zip_path / data_path : 批次文件绝对路径
    """
    celery_start_time = time.time()
    batch_dir = Path(batch_dir)
    zip_path = batch_dir / "img.zip"  # 固定
    data_path = batch_dir / "data.json"  # 固定
    # ----① 把批内所有 DR 标记为 in_progress ------------
    dr_list = list(
        DetectionResult.objects.select_related('detection_task')
        .filter(id__in=detection_result_ids)
    )
    if not dr_list:
        return "No DetectionResult found"

    task = dr_list[0].detection_task
    if task.status != 'in_progress':
        task.status = 'in_progress'
        task.save(update_fields=['status'])

    for dr in dr_list:
        dr.status = 'in_progress'
        dr.save(update_fields=['status'])

    send_request_time = time.time()

    # ----② 调模型 -------------------------------------
    results = get_result(zip_path, data_path)
    # results 长度必须 == len(dr_list)
    if results is None or len(results[1][1]) != len(dr_list):
        # 失败重连（与旧逻辑保持一致）
        while results is None or len(results[1][1]) != len(dr_list):
            reconnect()
            results = get_result(Path(zip_path), Path(data_path))
    # PICKLE_PATH = Path(settings.BASE_DIR) / 'fake_image_detector' / 'core' / 'result_new_none_llm.pkl'
    # with PICKLE_PATH.open('rb') as f:
    #     results = pickle.load(f)

    get_request_time = time.time()

    # ----③ 逐条写回数据库 -----------------------------
    # for dr, result in zip(dr_list, results):
    #     _write_back_single_result(dr, result)   # 见下一小节辅助方法

    for i in range(len(dr_list)):
        dr = dr_list[i]
        if results[0][1][i][1] is not None:
            llm_text = results[0][1][i]['outputs']
            llm_text = fanyi_text(results[0][1][i]['outputs'])
            llm_img = None
            # llm_img = result[0][1][1]  # (n, m, 3)的ndarray，表示llm的mask图
        else:
            llm_text = '无'
            llm_img = None
        ela_result = results[1][1][i][1]  # (266, 126)的ndarray，表示mask图
        exif_result = results[2][1][i][1][1]
        urn_splicing_result = results[4][1][2 * i : 2 * i + 2]
        urn_blurring_result = results[5][1][2 * i : 2 * i + 2]
        urn_bruteforce_result = results[6][1][2 * i : 2 * i + 2]
        urn_contrast_result = results[7][1][2 * i : 2 * i + 2]
        urn_inpainting_result = results[8][1][2 * i : 2 * i + 2]

        # 存储ela_result
        ela_img_path = save_ndarray_as_image(ela_result,
                                             subdir='ela_results',
                                             prefix=f"ela_{dr.id}")

        # 存储llm_img
        if llm_img is not None:
            llm_img_path = save_ndarray_as_image(llm_img,
                                                 subdir='llm_results',
                                                 prefix=f"llm_{dr.id}")

        # 检测返回结果
        bar = 0.5
        overall_is_fake = urn_splicing_result[1] > bar or urn_blurring_result[1] > bar or \
                          urn_bruteforce_result[1] > bar or urn_contrast_result[1] > bar or \
                          urn_inpainting_result[1] > bar or exif_result is not None
        overall_confidence = max(urn_splicing_result[1], urn_blurring_result[1],
                                 urn_bruteforce_result[1], urn_contrast_result[1],
                                 urn_inpainting_result[1])
        # llm_text               = "The image appears authentic."
        # ela_img_path           = 'ela_results/{}.png'.format(dr.image_upload.id)
        exif_flags = {'photoshop': False, 'time_modified': False}
        if exif_result is not None:
            if "使用了Photoshop进行修改" in exif_result:
                exif_flags['photoshop'] = True
            if "修改了拍摄或制作时间" in exif_result:
                exif_flags['time_modified'] = True
            overall_confidence = 1.0

        # 示例 mask，实际应由模型生成，为0-1的256x256矩阵
        mask_splicing_np = np.squeeze(urn_splicing_result[0])
        mask_splicing_path = save_ndarray_as_image(mask_splicing_np, subdir='masks', prefix=f"mask_splicing_{dr.id}")
        mask_blurring_np = np.squeeze(urn_blurring_result[0])
        mask_blurring_path = save_ndarray_as_image(mask_blurring_np, subdir='masks', prefix=f"mask_blurring_{dr.id}")
        mask_bruteforce_np = np.squeeze(urn_bruteforce_result[0])
        mask_bruteforce_path = save_ndarray_as_image(mask_bruteforce_np, subdir='masks',
                                                     prefix=f"mask_bruteforce_{dr.id}")
        mask_contrast_np = np.squeeze(urn_contrast_result[0])
        mask_contrast_path = save_ndarray_as_image(mask_contrast_np, subdir='masks', prefix=f"mask_contrast_{dr.id}")
        mask_inpainting_np = np.squeeze(urn_inpainting_result[0])
        mask_inpainting_path = save_ndarray_as_image(mask_inpainting_np, subdir='masks',
                                                     prefix=f"mask_inpainting_{dr.id}")

        sub_method_results = [
            # (method_key, prob, mask_img_path, mask_matrix_ndarray)
            ('splicing', urn_splicing_result[1], mask_splicing_path, mask_splicing_np),
            ('blurring', urn_blurring_result[1], mask_blurring_path, mask_blurring_np),
            ('bruteforce', urn_bruteforce_result[1], mask_bruteforce_path, mask_bruteforce_np),
            ('contrast', urn_contrast_result[1], mask_contrast_path, mask_contrast_np),
            ('inpainting', urn_inpainting_result[1], mask_inpainting_path, mask_inpainting_np)
        ]
        # ─────────────────────────────────────────────────────────────────────

        # ─── 2. 更新 DetectionResult 主表 ───────────────────────────────────
        dr.is_fake = overall_is_fake
        dr.confidence_score = overall_confidence
        dr.llm_judgment = llm_text
        dr.ela_image = ela_img_path
        if llm_img is not None:
            dr.llm_image = llm_img_path
        dr.exif_photoshop = exif_flags['photoshop']
        dr.exif_time_modified = exif_flags['time_modified']
        dr.detection_time = timezone.now()
        dr.save()

        # ─── 3. 子检测方法结果逐条写入子表 ────────────────────────────────
        for method_key, prob, mask_img, mask_np in sub_method_results:
            SubDetectionResult.objects.update_or_create(
                detection_result=dr, method=method_key,
                defaults={
                    'probability': prob,
                    'mask_image': mask_img,
                    'mask_matrix': json.loads(
                        json.dumps(mask_np.tolist()))  # ndarray→list→json
                }
            )
        dr.status = 'completed'
        dr.save(update_fields=['status'])

        # 更新dr对应的imageupload表的isFake参数和isDetect参数
        image_upload = dr.image_upload
        image_upload.isFake = overall_is_fake
        image_upload.isDetect = True
        image_upload.save(update_fields=['isFake', 'isDetect'])

    write_time = time.time()

    # ----④ 判断整个 DetectionTask 是否完成 ------------
    # all_results = DetectionResult.objects.filter(detection_task=task)
    all_results_qs = DetectionResult.objects.filter(detection_task=task)
    completed_count = all_results_qs.filter(status='completed').count()
    # 只有 “已完成数量 == 任务应检测总数” 才算真正完成
    if completed_count == image_num:
        with transaction.atomic():
            report_start_time = time.time()
            task.status = 'completed'
            task.completion_time = timezone.now()
            task.save(update_fields=['status', 'completion_time'])
            generate_report_for_task(task.id)

            report_end_time = time.time()

        send_task_completion_notification(task.user, task.id)

    # ----⑤ 可选：清理临时文件 --------------------------
        # 任务尾部
        try:
            zip_path.unlink(missing_ok=True)
            data_path.unlink(missing_ok=True)
            batch_dir.rmdir()  # 若目录已空可删除
            final_time = time.time()

            print('celery全过程用时', final_time - celery_start_time)
            print('从celery启动到发送检测用时', send_request_time - celery_start_time)
            print('等待检测结果用时', get_request_time - send_request_time)
            print('结果写入数据库用时', write_time - get_request_time)
            print('再到开始生成报告用时', report_start_time - write_time)
            print('生成报告用时', report_end_time - report_start_time)
            print('剩下的通知和更新task信息用时', final_time - report_start_time)
        except Exception:
            pass


# tasks.py
def _write_back_single_result(dr, result):
    """
    完整复制原 run_ai_detection 中“解析 result & 落库”的那一大段，
    只是把里面的 `result = ...` 行删掉，直接使用传入的 result。
    """
    # ---------------- 原来代码粘贴到此 -----------------
    # (整体与原 run_ai_detection 中除最前面 status 更新、
    #  最后任务完成检查外的内容完全一致)
    # ---------------------------------------------------
    if result[0][1] is not None:
        llm_text = result[0][1][0][0]['outputs']
        llm_text = fanyi_text(result[0][1][0][0]['outputs'])
        llm_img = result[0][1][1]  # (n, m, 3)的ndarray，表示llm的mask图
    else:
        llm_text = '无'
        llm_img = None
    ela_result = result[1][1]  # (266, 126)的ndarray，表示mask图
    exif_result = result[2][1]
    urn_splicing_result = result[4][1]
    urn_blurring_result = result[5][1]
    urn_bruteforce_result = result[6][1]
    urn_contrast_result = result[7][1]
    urn_inpainting_result = result[8][1]

    # 存储ela_result
    ela_img_path = save_ndarray_as_image(ela_result,
                                            subdir='ela_results',
                                            prefix=f"ela_{dr.id}")

    # 存储llm_img
    if llm_img is not None:
        llm_img_path = save_ndarray_as_image(llm_img,
                                            subdir='llm_results',
                                            prefix=f"llm_{dr.id}")

    # 检测返回结果
    bar = 0.5
    overall_is_fake        = urn_splicing_result[1].tolist()[0] > bar or urn_blurring_result[1].tolist()[0] > bar or urn_bruteforce_result[1].tolist()[0] > bar or urn_contrast_result[1].tolist()[0] > bar or urn_inpainting_result[1].tolist()[0] > bar or exif_result is not None
    overall_confidence     = max(urn_splicing_result[1].tolist()[0], urn_blurring_result[1].tolist()[0], urn_bruteforce_result[1].tolist()[0], urn_contrast_result[1].tolist()[0], urn_inpainting_result[1].tolist()[0])
    # llm_text               = "The image appears authentic."
    # ela_img_path           = 'ela_results/{}.png'.format(dr.image_upload.id)
    exif_flags             = {'photoshop': False, 'time_modified': False}
    if exif_result is not None:
        if "使用了Photoshop进行修改" in exif_result:
            exif_flags['photoshop'] = True
        if "修改了拍摄或制作时间" in exif_result:
            exif_flags['time_modified'] = True
        overall_confidence = 1.0

    # 示例 mask，实际应由模型生成，为0-1的256x256矩阵
    mask_splicing_np = urn_splicing_result[0][0]
    mask_splicing_path = save_ndarray_as_image(mask_splicing_np, subdir='masks', prefix=f"mask_splicing_{dr.id}")
    mask_blurring_np = urn_blurring_result[0][0]
    mask_blurring_path = save_ndarray_as_image(mask_blurring_np, subdir='masks', prefix=f"mask_blurring_{dr.id}")
    mask_bruteforce_np = urn_bruteforce_result[0][0]
    mask_bruteforce_path = save_ndarray_as_image(mask_bruteforce_np, subdir='masks', prefix=f"mask_bruteforce_{dr.id}")
    mask_contrast_np = urn_contrast_result[0][0]
    mask_contrast_path = save_ndarray_as_image(mask_contrast_np, subdir='masks', prefix=f"mask_contrast_{dr.id}")
    mask_inpainting_np = urn_inpainting_result[0][0]
    mask_inpainting_path = save_ndarray_as_image(mask_inpainting_np, subdir='masks', prefix=f"mask_inpainting_{dr.id}")

    sub_method_results = [
        # (method_key, prob, mask_img_path, mask_matrix_ndarray)
        ('splicing', urn_splicing_result[1].tolist()[0], mask_splicing_path, mask_splicing_np),
        ('blurring', urn_blurring_result[1].tolist()[0], mask_blurring_path, mask_blurring_np),
        ('bruteforce', urn_bruteforce_result[1].tolist()[0], mask_bruteforce_path, mask_bruteforce_np),
        ('contrast', urn_contrast_result[1].tolist()[0], mask_contrast_path, mask_contrast_np),
        ('inpainting', urn_inpainting_result[1].tolist()[0], mask_inpainting_path, mask_inpainting_np)
    ]
    # ─────────────────────────────────────────────────────────────────────

    # ─── 2. 更新 DetectionResult 主表 ───────────────────────────────────
    dr.is_fake          = overall_is_fake
    dr.confidence_score = overall_confidence
    dr.llm_judgment     = llm_text
    dr.ela_image        = ela_img_path
    if llm_img is not None:
        dr.llm_image        = llm_img_path
    dr.exif_photoshop   = exif_flags['photoshop']
    dr.exif_time_modified = exif_flags['time_modified']
    dr.detection_time   = timezone.now()
    dr.save()

    # ─── 3. 子检测方法结果逐条写入子表 ────────────────────────────────
    for method_key, prob, mask_img, mask_np in sub_method_results:
        SubDetectionResult.objects.update_or_create(
            detection_result=dr, method=method_key,
            defaults={
                'probability': prob,
                'mask_image': mask_img,
                'mask_matrix': json.loads(
                    json.dumps(mask_np.tolist()))  # ndarray→list→json
            }
        )
    dr.status = 'completed'
    dr.save(update_fields=['status'])

    # 更新dr对应的imageupload表的isFake参数和isDetect参数
    image_upload = dr.image_upload
    image_upload.isFake = overall_is_fake
    image_upload.isDetect = True
    image_upload.save(update_fields=['isFake', 'isDetect'])