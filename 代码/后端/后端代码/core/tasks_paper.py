"""Celery tasks for paper / review detection chains
=====================================================

任务 015 – 论文检测链路（paper_aigc + resource_check）
任务 017 – Review 检测链路（review_detection）

每个 task 都做三件事：
    1. 从磁盘读取预处理产物
    2. 计算检测结果（Alpha 阶段为确定性 mock）
    3. 将结果写入 JSON 并更新 DetectionTask 状态
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import DetectionTask, Log
from core.util import send_notification
from core.models import Notification

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  通用辅助
# ═══════════════════════════════════════════════════════════════════════════════

MEDIA = Path(settings.MEDIA_ROOT)


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _paper_meta_path(file_id):
    return MEDIA / "paper_uploads" / f"{file_id}_meta.json"


def _review_meta_path(file_id):
    return MEDIA / "review_uploads" / f"{file_id}_meta.json"


def _paper_result_path(file_id, result_type: str):
    """result_type: 'aigc' | 'resource'"""
    return MEDIA / "paper_uploads" / f"{file_id}_{result_type}_result.json"


def _review_result_path(file_id):
    return MEDIA / "review_uploads" / f"{file_id}_detection_result.json"


def _risk_level(score):
    if score >= 0.7:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _complete_task(task: DetectionTask):
    """公共收尾：标记完成 + 生成报告 + 记录日志 + 系统通知。"""
    task.status = "completed"
    task.completion_time = timezone.now()
    task.error_message = ""
    task.save(update_fields=["status", "completion_time", "error_message"])

    # 任务 023 – 状态变更日志
    Log.objects.create(
        user=task.user,
        operation_type="status_change",
        related_model="DetectionTask",
        related_id=task.id,
    )

    # 任务 019 – 自动生成报告
    try:
        from core.utils.report_generator import generate_unified_task_report
        generate_unified_task_report(task)
        Log.objects.create(
            user=task.user,
            operation_type="report_generation",
            related_model="DetectionTask",
            related_id=task.id,
        )
    except Exception as exc:
        logger.warning("报告生成失败 (task %s): %s", task.id, exc)

    # 发系统通知
    try:
        send_notification(
            receiver_id=task.user_id,
            receiver_name=task.user.username,
            category=Notification.SYSTEM,
            title="检测已完成",
            content=f"您的任务「{task.task_name}」已完成，请查看结果。",
            url=f"/task/{task.id}",
        )
    except Exception as exc:
        logger.warning("发送任务完成通知失败: %s", exc)

    # WebSocket 实时推送（与图像检测链路复用同一逻辑）
    try:
        from core.tasks_new import send_task_completion_notification
        send_task_completion_notification(task.user, task.id)
    except Exception:
        pass  # WebSocket 不可用时不影响主流程


def _fail_task(task: DetectionTask, message: str):
    task.status = "failed"
    task.error_message = message
    task.save(update_fields=["status", "error_message"])
    # 任务 023 – 失败状态日志
    try:
        Log.objects.create(
            user=task.user,
            operation_type="status_change",
            related_model="DetectionTask",
            related_id=task.id,
        )
    except Exception:
        pass
    logger.error("Task %s failed: %s", task.id, message)


# ═══════════════════════════════════════════════════════════════════════════════
#  论文 AIGC 检测（task_type = 'paper_aigc'）
# ═══════════════════════════════════════════════════════════════════════════════

def _build_aigc_result(task, paper_text: str, paragraphs_data=None) -> dict:
    """确定性 mock：与 views_paper 旧版逻辑完全一致，保持兼容。"""
    base = f"{task.id}|{paper_text[:2000]}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    ratio = round(0.2 + (int(digest[:8], 16) / 0xFFFFFFFF) * 0.65, 4)

    paragraph_items = paragraphs_data or _split_paragraphs(paper_text)
    paragraphs = []
    for idx, item in enumerate(paragraph_items[:12], start=1):
        para = str(item.get("text", "")).strip() if isinstance(item, dict) else str(item).strip()
        if not para:
            continue
        phash = hashlib.md5(f"{task.id}:{idx}:{para[:200]}".encode("utf-8")).hexdigest()
        score = round(0.2 + (int(phash[:6], 16) / 0xFFFFFF) * 0.75, 3)
        paragraphs.append({
            "index": item.get("index", idx) if isinstance(item, dict) else idx,
            "risk_score": score,
            "risk_level": _risk_level(score),
            "excerpt": para[:180],
            "char_start": item.get("char_start") if isinstance(item, dict) else None,
            "char_end": item.get("char_end") if isinstance(item, dict) else None,
        })

    high_count = sum(1 for p in paragraphs if p["risk_level"] == "high")
    summary = f"检测完成：AI 贡献占比约 {round(ratio * 100, 1)}%，高风险段落 {high_count} 段。"

    return {
        "task_id": task.id,
        "overall_risk_level": _risk_level(ratio),
        "ai_contribution_ratio": ratio,
        "summary": summary,
        "paragraphs": paragraphs,
    }


def _split_paragraphs(text):
    chunks = [x.strip() for x in re.split(r"\n{2,}|(?<=[。！？.!?])\s+", text or "") if x.strip()]
    if not chunks:
        return [{"index": 1, "text": "未提取到有效文本，建议检查文件内容后重试。"}]
    return [{"index": i, "text": c} for i, c in enumerate(chunks[:12], start=1)]


def _load_paper_paragraphs(file_id):
    meta = _load_json(_paper_meta_path(file_id))
    if not meta:
        return []
    paragraphs_rel = meta.get("paragraphs_path", "")
    paragraphs_abs = MEDIA / paragraphs_rel
    if not paragraphs_abs.exists():
        return []
    try:
        payload = json.loads(paragraphs_abs.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict) and item.get("text")]


def _get_paper_text(file_id):
    meta = _load_json(_paper_meta_path(file_id))
    if not meta:
        return "", None
    text_rel = meta.get("cleaned_text_path") or meta.get("text_path", "")
    text_abs = MEDIA / text_rel
    if text_abs.exists():
        try:
            return text_abs.read_text(encoding="utf-8", errors="ignore"), meta
        except Exception:
            pass
    return "", meta


@shared_task(queue="cpu", bind=True, acks_late=True, max_retries=2, default_retry_delay=10)
def run_paper_aigc_detection(self, task_id: int):
    """论文 AIGC 检测异步任务。"""
    try:
        task = DetectionTask.objects.select_related("user").get(pk=task_id)
    except DetectionTask.DoesNotExist:
        logger.error("run_paper_aigc_detection: task %s 不存在", task_id)
        return

    # ① 标记 in_progress
    task.status = "in_progress"
    task.save(update_fields=["status"])

    # ② 读取预处理产物
    file_id = task.paper_file_id
    if not file_id:
        _fail_task(task, "论文任务缺少 paper_file 关联。")
        return

    meta = _load_json(_paper_meta_path(file_id))
    if not meta or not meta.get("ai_payload_path"):
        _fail_task(task, "论文文件元数据缺失或已损坏。")
        return

    paper_text, _ = _get_paper_text(file_id)
    paragraphs_data = _load_paper_paragraphs(file_id)

    # ③ 模拟 AI 推理耗时（Alpha 阶段，实际接入 AI 后替换此段）
    time.sleep(2)

    # ④ 计算结果 & 落盘
    result = _build_aigc_result(task, paper_text, paragraphs_data or None)
    _save_json(_paper_result_path(file_id, "aigc"), result)

    # ⑤ 记录日志
    Log.objects.create(
        user=task.user,
        operation_type="detection",
        related_model="DetectionTask",
        related_id=task.id,
    )

    # ⑥ 标记完成 & 通知
    _complete_task(task)
    logger.info("paper_aigc task %s 完成", task_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  学术资源检测（task_type = 'resource_check'）
# ═══════════════════════════════════════════════════════════════════════════════

def _build_resource_result(task, paper_text: str) -> dict:
    """确定性 mock：与 views_paper 旧版逻辑完全一致。"""
    lines = [x.strip() for x in (paper_text or "").splitlines() if x.strip()]
    doi_regex = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
    ref_lines = [ln for ln in lines if ("[" in ln and "]" in ln) or "doi" in ln.lower() or "参考" in ln]
    if not ref_lines:
        ref_lines = lines[:8]

    issues = []
    doi_found = 0
    doi_invalid = 0
    for i, line in enumerate(ref_lines[:20], start=1):
        doi = doi_regex.search(line)
        if doi:
            doi_found += 1
            if len(doi.group(0)) < 10:
                doi_invalid += 1
                issues.append({
                    "reference_index": i,
                    "issue_type": "doi_invalid",
                    "detail": f"DOI 可能不完整：{doi.group(0)}",
                    "severity": "medium",
                })
        else:
            issues.append({
                "reference_index": i,
                "issue_type": "doi_missing",
                "detail": "未识别到 DOI，建议核验该参考条目来源。",
                "severity": "low",
            })
        if len(line) < 18:
            issues.append({
                "reference_index": i,
                "issue_type": "citation_incomplete",
                "detail": "条目文本较短，可能缺少卷期、页码或作者信息。",
                "severity": "medium",
            })

    issues = issues[:10]
    summary = f"检测完成：共识别 {len(ref_lines)} 条候选参考，疑似风险 {len(issues)} 条。"

    return {
        "task_id": task.id,
        "total_references": len(ref_lines),
        "doi_found_count": doi_found,
        "doi_invalid_count": doi_invalid,
        "suspected_risk_count": len(issues),
        "summary": summary,
        "issues": issues,
        "issues_json": issues,
    }


@shared_task(queue="cpu", bind=True, acks_late=True, max_retries=2, default_retry_delay=10)
def run_resource_check_detection(self, task_id: int):
    """学术资源检测异步任务。"""
    try:
        task = DetectionTask.objects.select_related("user").get(pk=task_id)
    except DetectionTask.DoesNotExist:
        logger.error("run_resource_check_detection: task %s 不存在", task_id)
        return

    task.status = "in_progress"
    task.save(update_fields=["status"])

    file_id = task.paper_file_id
    if not file_id:
        _fail_task(task, "论文任务缺少 paper_file 关联。")
        return

    meta = _load_json(_paper_meta_path(file_id))
    if not meta:
        _fail_task(task, "论文文件元数据缺失或已损坏。")
        return

    paper_text, _ = _get_paper_text(file_id)

    time.sleep(2)

    result = _build_resource_result(task, paper_text)
    _save_json(_paper_result_path(file_id, "resource"), result)

    Log.objects.create(
        user=task.user,
        operation_type="detection",
        related_model="DetectionTask",
        related_id=task.id,
    )

    _complete_task(task)
    logger.info("resource_check task %s 完成", task_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  Review 检测（task_type = 'review_detection'）     ← 任务 017
# ═══════════════════════════════════════════════════════════════════════════════

def _get_review_text(file_id):
    meta = _load_json(_review_meta_path(file_id))
    if not meta:
        return "", None
    text_rel = meta.get("cleaned_text_path") or meta.get("text_path", "")
    text_abs = MEDIA / text_rel
    if text_abs.exists():
        try:
            return text_abs.read_text(encoding="utf-8", errors="ignore"), meta
        except Exception:
            pass
    return "", meta


def _build_review_result(task, review_text: str) -> dict:
    """Review 检测确定性 mock：评估文本的 AI 生成概率 + 模板化倾向。"""
    base = f"review|{task.id}|{review_text[:2000]}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()

    # AI 生成概率
    ai_prob = round(0.1 + (int(digest[:8], 16) / 0xFFFFFFFF) * 0.8, 4)
    # 模板化倾向得分
    tpl_score = round(0.05 + (int(digest[8:16], 16) / 0xFFFFFFFF) * 0.7, 4)

    is_template_like = tpl_score >= 0.5

    # 对 Review 文本按句切分，逐句打分
    sentences = [s.strip() for s in re.split(r'[。！？.!?\n]+', review_text or '') if s.strip()]
    sentence_details = []
    for idx, sent in enumerate(sentences[:20], start=1):
        shash = hashlib.md5(f"{task.id}:sent:{idx}:{sent[:100]}".encode("utf-8")).hexdigest()
        s_score = round(0.1 + (int(shash[:6], 16) / 0xFFFFFF) * 0.85, 3)
        sentence_details.append({
            "index": idx,
            "text": sent[:150],
            "ai_probability": s_score,
            "risk_level": _risk_level(s_score),
        })

    high_count = sum(1 for s in sentence_details if s["risk_level"] == "high")

    summary_parts = [f"AI 生成概率约 {round(ai_prob * 100, 1)}%"]
    if is_template_like:
        summary_parts.append("检测到模板化倾向")
    else:
        summary_parts.append("未检测到明显模板化倾向")
    summary_parts.append(f"高风险句 {high_count} 句")
    summary = "检测完成：" + "，".join(summary_parts) + "。"

    return {
        "task_id": task.id,
        "overall_ai_probability": ai_prob,
        "overall_risk_level": _risk_level(ai_prob),
        "template_score": tpl_score,
        "is_template_like": is_template_like,
        "summary": summary,
        "sentence_count": len(sentence_details),
        "high_risk_count": high_count,
        "sentences": sentence_details,
    }


@shared_task(queue="cpu", bind=True, acks_late=True, max_retries=2, default_retry_delay=10)
def run_review_detection(self, task_id: int):
    """Review 检测异步任务。"""
    try:
        task = DetectionTask.objects.select_related("user").get(pk=task_id)
    except DetectionTask.DoesNotExist:
        logger.error("run_review_detection: task %s 不存在", task_id)
        return

    task.status = "in_progress"
    task.save(update_fields=["status"])

    file_id = task.paper_file_id
    if not file_id:
        _fail_task(task, "Review 任务缺少文件关联。")
        return

    meta = _load_json(_review_meta_path(file_id))
    if not meta or not meta.get("ai_payload_path"):
        _fail_task(task, "Review 文件元数据缺失或已损坏。")
        return

    review_text, _ = _get_review_text(file_id)
    if not review_text.strip():
        _fail_task(task, "未读取到有效的 Review 文本内容。")
        return

    time.sleep(2)

    result = _build_review_result(task, review_text)
    _save_json(_review_result_path(file_id), result)

    Log.objects.create(
        user=task.user,
        operation_type="detection",
        related_model="DetectionTask",
        related_id=task.id,
    )

    _complete_task(task)
    logger.info("review_detection task %s 完成", task_id)
