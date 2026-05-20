from django.utils import timezone
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..models import (
    DetectionTask,
    DetectionResult,
    FileManagement,
    ImageReview,
    ImageUpload,
    Log,
    ManualReview,
    ReviewRequest,
    User,
)


def _aggregate_manual_review_status(review_request: ReviewRequest) -> str:
    """与前端约定：管理端未通过前视为 undo；通过后以全部 ManualReview 是否 completed 为准。"""
    if review_request.status2 != "accepted":
        return "undo"
    mrs = list(review_request.manual_reviews.all())
    if not mrs:
        return "undo"
    if all(m.status == "completed" for m in mrs):
        return "completed"
    return "undo"


def _task_images(task: DetectionTask) -> list:
    imgs = list(ImageUpload.objects.filter(detection_task=task).order_by("id"))
    if imgs:
        return imgs
    dr = task.detection_results.select_related("image_upload").first()
    if dr and dr.image_upload_id:
        return [dr.image_upload]
    return []


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_manual_review_request(request):
    user = User.objects.get(id=request.user.id)
    if user.role != "publisher":
        return Response({"error": "Only publishers can create manual review requests"}, status=403)

    detection_task_id = request.data.get("detection_task_id")
    reason = request.data.get("reason", "")
    task_type = request.data.get("task_type", "")
    if not detection_task_id:
        return Response({"error": "detection_task_id is required"}, status=400)
    try:
        task = DetectionTask.objects.get(id=detection_task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"error": "task not found"}, status=404)
    if task.status != "completed":
        return Response({"error": "task not completed"}, status=400)

    detection_result = task.detection_results.first()
    if not detection_result:
        file_mgmt = task.paper_file
        if not file_mgmt:
            file_mgmt = FileManagement.objects.create(
                user=request.user,
                organization=user.organization,
                file_name="review_placeholder",
                file_size=0,
                file_type="placeholder",
            )
        img = ImageUpload(detection_task=task, file_management=file_mgmt, extracted_from_pdf=False)
        img.image.save("placeholder.png", ContentFile(b"\x89PNG\r\n\x1a\n"), save=False)
        img.save()
        detection_result = DetectionResult.objects.create(
            image_upload=img,
            detection_task=task,
            is_fake=False,
            confidence_score=0,
            status="completed",
        )

    # 若当时组织内已有审稿人则一并写入；允许零审稿人先占位，由管理端「通过」时再绑定（见 handle_review_request）
    reviewers = User.objects.filter(organization=user.organization, role="reviewer", is_active=True)

    images = _task_images(task)
    if not images:
        return Response({"error": "该检测任务下没有可关联的图片记录，无法发起人工审核"}, status=400)

    review_request = ReviewRequest.objects.create(
        detection_result=detection_result,
        user=request.user,
        organization=user.organization,
        reason=reason or "manual review - " + str(task_type),
        status1="pending",
        status2="pending",
        check_reason="",
    )
    review_request.imgs.add(*images)
    for rv in reviewers:
        review_request.reviewers.add(rv)

    Log.objects.create(
        user=request.user,
        operation_type="review_request",
        related_model="ReviewRequest",
        related_id=review_request.id,
    )
    created = timezone.localtime(review_request.request_time).strftime("%Y-%m-%d %H:%M:%S")
    return Response(
        {
            "review_request_id": review_request.id,
            "id": review_request.id,
            "status": "pending_admin",
            "message": "已提交人工审核申请，等待管理端审批",
            "detection_task_id": task.id,
            "task_type": task.task_type,
            "created_at": created,
        },
        status=201,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_manual_review_by_detection_task(request):
    raw_id = request.query_params.get("detection_task_id")
    if raw_id is None or str(raw_id).strip() == "":
        return Response({"found": False, "detection_task_id": ""})

    tid = str(raw_id).strip()
    try:
        task = DetectionTask.objects.get(id=tid, user=request.user)
    except (DetectionTask.DoesNotExist, ValueError):
        return Response({"found": False, "detection_task_id": tid})

    rr = (
        ReviewRequest.objects.filter(user=request.user, detection_result__detection_task=task)
        .prefetch_related("manual_reviews")
        .order_by("-request_time")
        .first()
    )
    if not rr:
        return Response({"found": False, "detection_task_id": tid})

    admin_state = rr.status2
    if (rr.check_reason or "").strip() == "publisher_cancelled":
        manual_review_status = "cancelled"
    else:
        manual_review_status = _aggregate_manual_review_status(rr)
    mr = rr.manual_reviews.order_by("id").first()
    payload = {
        "found": True,
        "review_request_id": rr.id,
        "detection_task_id": tid,
        "task_type": task.task_type,
        "admin_state": admin_state,
        "manual_review_id": mr.id if mr else None,
        "manual_review_status": manual_review_status,
        "admin_reject_reason": rr.check_reason if admin_state == "refused" else None,
        "created_at": timezone.localtime(rr.request_time).strftime("%Y-%m-%d %H:%M:%S"),
    }
    return Response(payload)


def _confidence_from_image_review(ir: ImageReview) -> int:
    scores = []
    for i in range(1, 8):
        v = getattr(ir, f"score{i}", None)
        if v is not None:
            scores.append(float(v))
    if not scores:
        return 0
    avg = sum(scores) / len(scores)
    return int(min(100, max(0, round(avg * 10))))


def _comment_from_image_review(ir: ImageReview) -> str:
    parts = []
    for i in range(1, 8):
        t = getattr(ir, f"reason{i}", None)
        if t:
            parts.append(str(t))
    return "；".join(parts) if parts else "—"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_publisher_manual_review_summary(request, review_request_id: int):
    user = User.objects.get(id=request.user.id)
    if user.role != "publisher":
        return Response({"error": "Only publishers can view this summary"}, status=403)

    try:
        rr = (
            ReviewRequest.objects.select_related("detection_result__detection_task", "user")
            .prefetch_related("imgs", "manual_reviews__reviewer", "manual_reviews__image_reviews__img")
            .get(id=review_request_id, user=request.user)
        )
    except ReviewRequest.DoesNotExist:
        return Response({"error": "ReviewRequest not found"}, status=404)

    task = rr.detection_result.detection_task
    admin_state = rr.status2
    if (rr.check_reason or "").strip() == "publisher_cancelled":
        manual_review_status = "cancelled"
    else:
        manual_review_status = _aggregate_manual_review_status(rr)
    first_mr = rr.manual_reviews.order_by("id").first()

    completed_mrs = [m for m in rr.manual_reviews.all() if m.status == "completed"]
    suspicious = ImageReview.objects.filter(
        manual_review__review_request=rr, manual_review__status="completed", result=True
    ).count()

    reviewer_rows = []
    for mr in completed_mrs:
        irs = list(mr.image_reviews.all())
        any_fake = any(ir.result is True for ir in irs if ir.result is not None)
        decision = "判定存在疑似造假" if any_fake else "未发现明显异常"
        confs = [_confidence_from_image_review(ir) for ir in irs]
        confidence = int(round(sum(confs) / len(confs))) if confs else 0
        comment = _comment_from_image_review(irs[0]) if irs else "—"
        reviewer_rows.append(
            {
                "reviewer": mr.reviewer.username,
                "decision": decision,
                "confidence": confidence,
                "comment": comment,
            }
        )

    segment_rows = []
    task_type_lower = (task.task_type or "").lower()
    is_textual = "paper" in task_type_lower or "review" in task_type_lower
    if is_textual:
        label_base = "论文材料单元" if "paper" in task_type_lower else "Review 材料单元"
        idx = 0
        if (rr.reason or "").strip():
            idx += 1
            segment_rows.append(
                {
                    "segmentId": str(idx),
                    "label": "申请说明",
                    "aiNote": f"自动检测类型：{task.task_type or '—'}",
                    "manualResult": "—",
                    "comment": "发布者申请理由（专家审核针对下方材料单元）",
                    "contentPreview": (rr.reason or "")[:500],
                }
            )
        for mr in completed_mrs:
            for ir in mr.image_reviews.all().order_by("id"):
                idx += 1
                manual_label = (
                    "疑似造假"
                    if ir.result is True
                    else ("未发现明显异常" if ir.result is False else "—")
                )
                segment_rows.append(
                    {
                        "segmentId": str(idx),
                        "label": f"{label_base} {idx}",
                        "reviewer": mr.reviewer.username,
                        "manualResult": manual_label,
                        "comment": _comment_from_image_review(ir),
                        "contentPreview": _comment_from_image_review(ir),
                    }
                )
        if not segment_rows and completed_mrs:
            segment_rows.append(
                {
                    "segmentId": "1",
                    "label": label_base,
                    "manualResult": reviewer_rows[0]["decision"] if reviewer_rows else "—",
                    "comment": reviewer_rows[0]["comment"] if reviewer_rows else "—",
                    "contentPreview": rr.reason or "—",
                }
            )

    image_rows = []
    if not is_textual and (task.task_type == "image_detection" or rr.imgs.exists()):
        for img in rr.imgs.all().order_by("id"):
            dr = img.detection_results.filter(detection_task=task).first() or img.detection_results.first()
            ai_label = "疑似异常" if dr and dr.is_fake else "未见明显异常"
            manual_flags = []
            for mr in completed_mrs:
                ir = mr.image_reviews.filter(img=img).first()
                if ir is not None and ir.result is not None:
                    manual_flags.append(ir.result)
            if not manual_flags:
                manual_label = "—"
                risk = "—"
                note = "专家尚未提交或未覆盖该图"
            else:
                any_fake = any(manual_flags)
                manual_label = "疑似造假" if any_fake else "未见明显异常"
                risk = "高" if any_fake else ("中" if dr and dr.is_fake else "低")
                note = "综合已完成审稿意见"
            image_rows.append(
                {
                    "imageId": str(img.id),
                    "aiResult": ai_label,
                    "manualResult": manual_label,
                    "riskLevel": risk,
                    "note": note,
                }
            )

    if admin_state == "refused":
        final_decision = "管理端已拒绝申请"
    elif manual_review_status != "completed":
        final_decision = "专家审核未完成"
    elif any(r["decision"].startswith("判定存在") for r in reviewer_rows):
        final_decision = "复核：存在疑似造假内容"
    else:
        final_decision = "复核：未发现明显异常"

    payload = {
        "review_request_id": rr.id,
        "detection_task_id": str(task.id),
        "task_type": task.task_type,
        "request_reason": rr.reason or "",
        "admin_state": admin_state,
        "admin_reject_reason": rr.check_reason or "",
        "publisher_status": rr.status1,
        "manual_review_status": manual_review_status,
        "manual_review_id": first_mr.id if first_mr else None,
        "summary": {
            "reviewerCount": len(completed_mrs),
            "suspiciousImageCount": suspicious,
            "finalDecision": final_decision,
        },
        "reviewerRows": reviewer_rows,
        "imageRows": image_rows,
        "segmentRows": segment_rows,
    }
    return Response(payload, status=status.HTTP_200_OK)
