"""
平台扩展接口：社区反馈、综合鉴伪报告、模型配置、举报、评论点赞、终止审核、多模态融合等。
"""
from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.paginator import Paginator
from django.http import FileResponse
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import (
    DetectionModelConfig,
    DetectionResult,
    DetectionTask,
    Feedback,
    ImageReview,
    ImageUpload,
    Log,
    ManualReview,
    Notification,
    ReviewRequest,
    SubDetectionResult,
    User,
    UserReport,
)
from ..util import detection_history_url, detection_task_type_label
from ..utils.report_generator import _load_result_json, _risk_label, generate_comprehensive_forgery_pdf
from .views_manual_review_adapter import _aggregate_manual_review_status

DEFAULT_MODEL_CATALOG = {
    "text_model": {"name": "Text-AIGC-Detector", "version": "1.2.0", "modes": ["fast", "precise"]},
    "image_model": {"name": "Academic-Image-Forensics", "version": "2.0.1", "modes": ["fast", "precise"]},
    "review_model": {"name": "Peer-Review-Guard", "version": "1.0.3", "modes": ["fast", "precise"]},
    "default_mode": "fast",
}


def _ensure_model_catalog():
    obj, _ = DetectionModelConfig.objects.get_or_create(
        key="catalog",
        defaults={"value": DEFAULT_MODEL_CATALOG},
    )
    if not obj.value:
        obj.value = DEFAULT_MODEL_CATALOG
        obj.save(update_fields=["value"])
    return obj.value


def _publisher_cancelled(rr: ReviewRequest) -> bool:
    return (rr.check_reason or "").strip() == "publisher_cancelled"


def _ui_status_from_rr(rr: ReviewRequest) -> str:
    if _publisher_cancelled(rr):
        return "cancelled"
    if rr.status2 == "refused" and (rr.check_reason or "").strip() not in ("publisher_cancelled", ""):
        return "failed"
    if rr.status2 == "refused":
        return "failed"
    if rr.status2 == "pending":
        return "pending"
    if rr.status1 == "completed":
        return "completed"
    return "in_progress"


# ── 反馈（评论/点赞）────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    manual_review_id = request.data.get("manual_review_id")
    if not manual_review_id:
        return Response({"error": "manual_review_id is required"}, status=400)
    try:
        mr = ManualReview.objects.select_related("review_request").get(id=manual_review_id)
    except ManualReview.DoesNotExist:
        return Response({"error": "ManualReview not found"}, status=404)

    is_like = bool(request.data.get("is_like", False))
    comment = (request.data.get("comment") or "").strip()
    if not is_like and not comment:
        return Response({"error": "is_like or comment is required"}, status=400)

    fb = Feedback.objects.create(
        manual_review=mr,
        user=request.user,
        is_like=is_like,
        comment=comment or None,
    )
    return Response({"message": "Feedback submitted successfully", "feedback_id": fb.id}, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_feedback(request, manual_review_id: int):
    try:
        mr = ManualReview.objects.get(id=manual_review_id)
    except ManualReview.DoesNotExist:
        return Response({"error": "ManualReview not found"}, status=404)

    qs = Feedback.objects.filter(manual_review=mr).select_related("user").order_by("-feedback_time")
    items = [
        {
            "feedback_id": f.id,
            "user_id": f.user_id,
            "username": f.user.username,
            "avatar": f.user.avatar.url if f.user.avatar else None,
            "is_like": f.is_like,
            "comment": f.comment or "",
            "feedback_time": timezone.localtime(f.feedback_time).strftime("%Y-%m-%d %H:%M:%S"),
        }
        for f in qs
    ]
    like_count = qs.filter(is_like=True).count()
    return Response({
        "manual_review_id": manual_review_id,
        "like_count": like_count,
        "feedbacks": items,
    })


# ── 举报 ────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_user_report(request):
    target_type = request.data.get("target_type", "manual_review")
    target_id = request.data.get("target_id")
    reason = (request.data.get("reason") or "").strip()
    report_type = request.data.get("report_type", "violation")
    if not target_id or not reason:
        return Response({"error": "target_id and reason are required"}, status=400)

    report = UserReport.objects.create(
        reporter=request.user,
        target_type=target_type,
        target_id=int(target_id),
        report_type=report_type,
        reason=reason,
    )
    return Response({"message": "举报已提交", "report_id": report.id}, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_list_user_reports(request):
    if request.user.role != "admin":
        return Response({"error": "Admin only"}, status=403)

    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 10))
    status_filter = request.query_params.get("status", "")

    qs = UserReport.objects.select_related("reporter", "handled_by").order_by("-created_at")
    if request.user.email != "admin@mail.com" and request.user.organization_id:
        org_reviewers = User.objects.filter(organization_id=request.user.organization_id).values_list("id", flat=True)
        qs = qs.filter(reporter_id__in=org_reviewers)
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    items = []
    for r in page_obj.object_list:
        items.append({
            "id": r.id,
            "reporter": r.reporter.username,
            "reporter_id": r.reporter_id,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "report_type": r.report_type,
            "reason": r.reason,
            "status": r.status,
            "admin_resolution": r.admin_resolution,
            "handled_by": r.handled_by.username if r.handled_by else None,
            "handled_at": timezone.localtime(r.handled_at).strftime("%Y-%m-%d %H:%M:%S") if r.handled_at else None,
            "created_at": timezone.localtime(r.created_at).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return Response({
        "reports": items,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "total": paginator.count,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_handle_user_report(request, report_id: int):
    if request.user.role != "admin":
        return Response({"error": "Admin only"}, status=403)
    try:
        report = UserReport.objects.get(id=report_id)
    except UserReport.DoesNotExist:
        return Response({"error": "Report not found"}, status=404)

    action = request.data.get("action", "resolved")
    resolution = (request.data.get("resolution") or "").strip()
    if action not in ("resolved", "dismissed"):
        return Response({"error": "action must be resolved or dismissed"}, status=400)

    report.status = action
    report.admin_resolution = resolution
    report.handled_by = request.user
    report.handled_at = timezone.now()
    report.save()

    Notification.objects.create(
        receiver_id=str(report.reporter_id),
        receiver_name=report.reporter.username,
        sender_id=str(request.user.id),
        sender_name=request.user.username,
        category=Notification.GLOBAL,
        title="举报处理结果",
        content=f"您对 {report.target_type}#{report.target_id} 的举报已{('成立' if action == 'resolved' else '驳回')}。{resolution}",
        status="unread",
        url="/community-feedback",
    )
    return Response({"message": "处理完成", "report_id": report.id})


# ── 终止人工审核 ────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_manual_review_request(request, review_request_id: int):
    user = request.user
    if user.role != "publisher":
        return Response({"error": "Only publishers can cancel"}, status=403)
    try:
        rr = ReviewRequest.objects.get(id=review_request_id, user=user)
    except ReviewRequest.DoesNotExist:
        return Response({"error": "ReviewRequest not found"}, status=404)

    if rr.status1 == "completed" and not _publisher_cancelled(rr):
        return Response({"error": "审核已完成，无法终止"}, status=400)

    rr.status1 = "completed"
    rr.status2 = "refused"
    rr.check_reason = "publisher_cancelled"
    rr.review_end_time = timezone.now()
    rr.save(update_fields=["status1", "status2", "check_reason", "review_end_time"])

    for mr in rr.manual_reviews.filter(status="undo"):
        mr.status = "completed"
        mr.save(update_fields=["status"])

    return Response({"message": "人工审核已终止", "review_request_id": rr.id, "status": "cancelled"})


# ── 社区反馈聚合 ────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def community_feedback_feed(request):
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    uid = str(request.user.id)

    notifs = Notification.objects.filter(receiver_id=uid).order_by("-notified_at")
    items = []
    notified_task_ids = set()
    for n in notifs[:200]:
        cat = "system"
        if n.category == Notification.GLOBAL:
            cat = "admin"
        elif n.category == Notification.SYSTEM:
            cat = "detection"
        elif n.category in (Notification.P2R, Notification.R2P):
            cat = "review"
        url = n.url or ""
        for marker in ("detail_id=", "task_id="):
            if marker in url:
                try:
                    part = url.split(marker, 1)[1].split("&", 1)[0]
                    if part.isdigit():
                        notified_task_ids.add(int(part))
                except Exception:
                    pass
        items.append({
            "id": f"n-{n.id}",
            "source": "notification",
            "category": cat,
            "title": n.title,
            "content": n.content,
            "status": n.status,
            "url": url,
            "time": timezone.localtime(n.notified_at).strftime("%Y-%m-%d %H:%M:%S"),
        })

    # 回填：历史已完成任务若未写入通知，也在「检测反馈」中展示
    completed_tasks = (
        DetectionTask.objects.filter(user=request.user, status="completed")
        .order_by("-completion_time")[:40]
    )
    for task in completed_tasks:
        if task.id in notified_task_ids:
            continue
        if any(f"编号 {task.id}" in (i.get("content") or "") for i in items if i.get("category") == "detection"):
            continue
        label = detection_task_type_label(task.task_type)
        items.append({
            "id": f"t-{task.id}",
            "source": "task_backfill",
            "category": "detection",
            "title": f"{label}已完成",
            "content": f"您的任务「{task.task_name}」（编号 {task.id}）已完成，点击查看检测结果。",
            "status": "read",
            "url": detection_history_url(task),
            "time": timezone.localtime(task.completion_time or task.upload_time).strftime("%Y-%m-%d %H:%M:%S"),
        })

    my_reports = UserReport.objects.filter(reporter=request.user).order_by("-created_at")[:50]
    for r in my_reports:
        items.append({
            "id": f"r-{r.id}",
            "source": "report",
            "category": "report",
            "title": f"举报处理：{r.get_status_display()}",
            "content": r.admin_resolution or r.reason,
            "status": "read" if r.status != "pending" else "unread",
            "url": "/community-feedback",
            "time": timezone.localtime(r.handled_at or r.created_at).strftime("%Y-%m-%d %H:%M:%S"),
        })

    items.sort(key=lambda x: x["time"], reverse=True)
    paginator = Paginator(items, page_size)
    page_obj = paginator.get_page(page)
    return Response({
        "items": list(page_obj.object_list),
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "total": paginator.count,
    })


# ── 综合鉴伪报告（在线）────────────────────────────────────────

def _image_comprehensive_sections(task: DetectionTask) -> dict:
    results = task.detection_results.select_related("image_upload").prefetch_related("sub_results").all()
    suspicious = []
    for dr in results:
        if not dr.is_fake:
            continue
        img = dr.image_upload
        masks = []
        for sub in dr.sub_results.all():
            masks.append({
                "method": sub.method,
                "probability": sub.probability,
                "mask_image": sub.mask_image.url if sub.mask_image else None,
            })
        suspicious.append({
            "image_id": dr.image_upload_id,
            "image_url": img.image.url if img and img.image else None,
            "confidence_score": dr.confidence_score,
            "masks": masks,
            "page_number": img.page_number if img else None,
        })
    fake_n = results.filter(is_fake=True).count()
    total = results.count()
    ratio = round(fake_n / total, 3) if total else 0
    return {
        "ai_contribution_ratio": ratio,
        "suspicious_regions": suspicious,
        "summary": f"共 {total} 张图，{fake_n} 张存在可疑迹象。",
        "risk_level": "high" if ratio > 0.5 else ("medium" if ratio > 0.2 else "low"),
    }


def _text_result_section(task: DetectionTask) -> dict | None:
    raw = _load_result_json(task)
    if not raw:
        return None
    section = {
        "summary": raw.get("summary", ""),
        "risk_level": _risk_label(raw.get("overall_risk_level")),
        "ai_contribution_ratio": raw.get("ai_contribution_ratio"),
        "paragraphs": raw.get("paragraphs", [])[:20],
        "issues": raw.get("issues", raw.get("problems", []))[:15],
        "factual_conclusions": (raw.get("factual_conclusions") or raw.get("factual_issues") or [])[:15],
        "template_signals": raw.get("template_signals", raw.get("template_flags", [])),
    }
    return section


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def comprehensive_forgery_report(request, task_id: int):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在"}, status=404)

    if task.status != "completed":
        return Response({
            "task_id": task.id,
            "status": task.status,
            "ready": False,
            "message": "检测尚未完成，报告生成中",
        })

    ttype = task.task_type or "image_detection"
    sections = {
        "overview": {
            "task_id": task.id,
            "task_name": task.task_name,
            "task_type": ttype,
            "detection_mode": task.detection_mode or ("precise" if task.if_use_llm else "fast"),
            "upload_time": timezone.localtime(task.upload_time).strftime("%Y-%m-%d %H:%M:%S"),
            "completion_time": timezone.localtime(task.completion_time).strftime("%Y-%m-%d %H:%M:%S") if task.completion_time else None,
        },
        "conclusion": {},
        "image": None,
        "paper": None,
        "review": None,
        "manual_review": None,
        "usage_advice": [],
    }

    if ttype == "image_detection":
        img_sec = _image_comprehensive_sections(task)
        sections["image"] = img_sec
        sections["conclusion"] = {
            "headline": img_sec["summary"],
            "risk_level": _risk_label(img_sec["risk_level"]),
            "ai_contribution_ratio": img_sec["ai_contribution_ratio"],
        }
        sections["usage_advice"] = [
            "请结合可疑区域标注与原始实验记录交叉验证。",
            "若用于投稿，建议对高风险图像进行人工复核或替换素材。",
        ]
    elif ttype in ("paper_aigc", "resource_check"):
        paper_sec = _text_result_section(task)
        sections["paper"] = paper_sec
        if paper_sec:
            ratio = paper_sec.get("ai_contribution_ratio")
            sections["conclusion"] = {
                "headline": paper_sec.get("summary") or "论文检测已完成",
                "risk_level": paper_sec.get("risk_level"),
                "ai_contribution_ratio": ratio,
            }
            sections["usage_advice"] = [
                "段落级风险分数较高处建议对照原文与引用来源。",
                "资源规范性条目请按问题表逐项修订参考文献与 DOI。",
            ]
    elif ttype == "review_detection":
        rev_sec = _text_result_section(task)
        sections["review"] = rev_sec
        if rev_sec:
            sections["conclusion"] = {
                "headline": rev_sec.get("summary") or "Review 检测已完成",
                "risk_level": rev_sec.get("risk_level"),
            }
            sections["usage_advice"] = ["关注模板化短语与异常流畅度片段。"]

    rr = (
        ReviewRequest.objects.filter(
            user=request.user, detection_result__detection_task=task
        )
        .order_by("-request_time")
        .first()
    )
    if rr:
        sections["manual_review"] = {
            "review_request_id": rr.id,
            "admin_state": rr.status2,
            "status": _ui_status_from_rr(rr),
            "reason": rr.reason,
        }

    catalog = _ensure_model_catalog()
    effective_mode = task.detection_mode or ("precise" if task.if_use_llm else "fast")
    sections["models_used"] = {
        "text": catalog.get("text_model"),
        "image": catalog.get("image_model"),
        "review": catalog.get("review_model"),
        "mode": effective_mode or catalog.get("default_mode", "fast"),
    }

    return Response({"ready": True, "sections": sections})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_comprehensive_forgery_report(request, task_id: int):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在"}, status=404)
    if task.status != "completed":
        return Response({"detail": "检测尚未完成"}, status=400)
    try:
        rel_path = generate_comprehensive_forgery_pdf(task)
    except Exception as exc:
        return Response({"detail": f"综合报告生成失败: {exc}"}, status=500)
    abs_path = Path(settings.MEDIA_ROOT) / rel_path
    if not abs_path.is_file():
        return Response({"detail": "报告文件不存在"}, status=404)
    return FileResponse(
        open(abs_path, "rb"),
        as_attachment=True,
        filename=f"comprehensive_task_{task.id}.pdf",
        content_type="application/pdf",
    )


# ── 多模态批次融合 ──────────────────────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def multimodal_batch_fusion(request):
    user = request.user
    if request.method == "POST":
        task_ids = request.data.get("task_ids") or []
        batch_session_id = (request.data.get("batch_session_id") or "").strip()
    else:
        raw_ids = request.query_params.get("task_ids", "")
        task_ids = [int(x) for x in raw_ids.split(",") if str(x).strip().isdigit()]
        batch_session_id = (request.query_params.get("batch_session_id") or "").strip()

    qs = DetectionTask.objects.filter(user=user, status="completed")
    if batch_session_id:
        qs = qs.filter(batch_session_id=batch_session_id)
    elif task_ids:
        qs = qs.filter(id__in=task_ids)
    else:
        return Response({"error": "batch_session_id or task_ids required"}, status=400)

    tasks = list(qs.order_by("upload_time")[:30])
    if not tasks:
        return Response({"error": "no completed tasks found"}, status=404)

    dim_scores = {"image": 0.0, "paper": 0.0, "review": 0.0}
    dim_count = {"image": 0, "paper": 0, "review": 0}
    children = []
    notes = []

    for t in tasks:
        child = {"task_id": t.id, "task_type": t.task_type, "task_name": t.task_name}
        if t.task_type == "image_detection":
            sec = _image_comprehensive_sections(t)
            child["risk"] = sec["risk_level"]
            child["score"] = sec["ai_contribution_ratio"]
            dim_scores["image"] += child["score"]
            dim_count["image"] += 1
        elif t.task_type in ("paper_aigc", "resource_check"):
            sec = _text_result_section(t) or {}
            lvl = sec.get("risk_level", "low")
            score = float(sec.get("ai_contribution_ratio") or 0.5 if lvl == "高风险" else 0.3)
            child["risk"] = lvl
            child["score"] = score
            dim_scores["paper"] += score
            dim_count["paper"] += 1
        elif t.task_type == "review_detection":
            sec = _text_result_section(t) or {}
            child["risk"] = sec.get("risk_level", "low")
            child["score"] = 0.4
            dim_scores["review"] += child["score"]
            dim_count["review"] += 1
        children.append(child)

    def avg(dim):
        return round(dim_scores[dim] / dim_count[dim], 3) if dim_count[dim] else None

    cross_modal = []
    if dim_count["image"] and dim_count["paper"]:
        cross_modal.append("图像与论文子任务均已纳入；请核对插图与正文结论是否一致。")
    if dim_count["review"] and dim_count["paper"]:
        cross_modal.append("Review 与论文同时送检；注意评审语气与全文 AIGC 风险是否匹配。")
    if not cross_modal:
        cross_modal.append("当前批次仅包含单一模态任务，联合分析主要体现为风险加总。")

    fusion_score = 0.0
    weight_sum = 0
    for dim, c in dim_count.items():
        if c:
            fusion_score += (dim_scores[dim] / c) * c
            weight_sum += c
    fusion_score = round(fusion_score / weight_sum, 3) if weight_sum else 0

    overall = "low"
    if fusion_score >= 0.55:
        overall = "high"
    elif fusion_score >= 0.3:
        overall = "medium"

    return Response({
        "batch_session_id": batch_session_id or None,
        "task_count": len(tasks),
        "fusion_score": fusion_score,
        "overall_risk": overall,
        "dimension_averages": {k: avg(k) for k in dim_scores},
        "cross_modal_notes": cross_modal,
        "tasks": children,
        "recommendation": "建议优先处理高风险子任务，并在综合鉴伪报告中查看分项证据。",
    })


# ── 检测模型配置 ────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detection_models_catalog(request):
    catalog = _ensure_model_catalog()
    prefs = {}
    try:
        prefs = json.loads(request.user.profile or "{}").get("detection_preferences", {})
    except (json.JSONDecodeError, TypeError):
        prefs = {}
    return Response({
        "catalog": catalog,
        "user_preferences": {
            "mode": prefs.get("mode", catalog.get("default_mode", "fast")),
            "text_model_version": prefs.get("text_model_version"),
            "image_model_version": prefs.get("image_model_version"),
            "review_model_version": prefs.get("review_model_version"),
        },
    })


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_detection_preferences(request):
    mode = request.data.get("mode", "fast")
    if mode not in ("fast", "precise"):
        return Response({"error": "mode must be fast or precise"}, status=400)
    profile = {}
    try:
        profile = json.loads(request.user.profile or "{}")
    except (json.JSONDecodeError, TypeError):
        profile = {}
    profile["detection_preferences"] = {
        "mode": mode,
        "text_model_version": request.data.get("text_model_version"),
        "image_model_version": request.data.get("image_model_version"),
        "review_model_version": request.data.get("review_model_version"),
    }
    request.user.profile = json.dumps(profile, ensure_ascii=False)
    request.user.save(update_fields=["profile"])
    return Response({"message": "ok", "detection_preferences": profile["detection_preferences"]})


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def admin_detection_models(request):
    if request.user.role != "admin":
        return Response({"error": "Admin only"}, status=403)
    if request.method == "GET":
        return Response({"catalog": _ensure_model_catalog()})
    value = request.data.get("catalog") or request.data
    obj, _ = DetectionModelConfig.objects.get_or_create(key="catalog", defaults={"value": value})
    obj.value = value
    obj.save(update_fields=["value", "updated_at"])
    return Response({"message": "saved", "catalog": obj.value})


# ── 管理端专用日志（论文 / Review）──────────────────────────────

def _scoped_detection_task_ids(request, log_scope: str):
    qs = DetectionTask.objects.all()
    if request.user.role == "admin" and request.user.email != "admin@mail.com":
        qs = qs.filter(organization_id=request.user.organization_id)
    elif request.user.role == "admin":
        org_id = request.query_params.get("organization")
        if org_id:
            qs = qs.filter(organization_id=org_id)
    else:
        qs = qs.filter(user=request.user)

    if log_scope == "paper":
        return set(qs.filter(task_type__in=["paper_aigc", "resource_check"]).values_list("id", flat=True))
    if log_scope == "review":
        return set(qs.filter(task_type="review_detection").values_list("id", flat=True))
    if log_scope == "image":
        return set(qs.filter(task_type="image_detection").values_list("id", flat=True))
    return set()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_detection_logs(request):
    if request.user.role != "admin":
        return Response({"error": "Admin only"}, status=403)

    log_scope = request.query_params.get("log_scope", "paper")
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 10))
    task_ids = _scoped_detection_task_ids(request, log_scope)

    logs = Log.objects.filter(related_model="DetectionTask", related_id__in=task_ids).select_related("user")
    logs = logs.order_by("-operation_time")

    status_filter = request.query_params.get("status", "")
    if status_filter:
        matching = DetectionTask.objects.filter(id__in=task_ids, status=status_filter).values_list("id", flat=True)
        logs = logs.filter(related_id__in=matching)

    paginator = Paginator(logs, page_size)
    page_obj = paginator.get_page(page)
    task_map = {
        t.id: t
        for t in DetectionTask.objects.filter(id__in=[lg.related_id for lg in page_obj.object_list]).only(
            "id", "task_name", "task_type", "status", "error_message"
        )
    }
    items = []
    for lg in page_obj.object_list:
        t = task_map.get(lg.related_id)
        items.append({
            "id": lg.id,
            "user": lg.user.username,
            "operation_type": lg.operation_type,
            "task_id": lg.related_id,
            "task_name": t.task_name if t else "",
            "task_type": t.task_type if t else "",
            "task_status": t.status if t else "",
            "error_message": (t.error_message if t else "") or "",
            "operation_time": timezone.localtime(lg.operation_time).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return Response({
        "log_scope": log_scope,
        "logs": items,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "total": paginator.count,
    })
