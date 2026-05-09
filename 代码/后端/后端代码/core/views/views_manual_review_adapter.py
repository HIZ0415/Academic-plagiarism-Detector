from django.utils import timezone
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import DetectionTask, DetectionResult, FileManagement, ImageUpload, Log, ReviewRequest, User

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_manual_review_request(request):
    user = User.objects.get(id=request.user.id)
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
            file_mgmt = FileManagement.objects.create(user=request.user, organization=user.organization, file_name="review_placeholder", file_size=0, file_type="placeholder")
        img = ImageUpload(detection_task=task, file_management=file_mgmt, extracted_from_pdf=False)
        img.image.save("placeholder.png", ContentFile(b'\x89PNG\r\n\x1a\n'), save=False)
        img.save()
        detection_result = DetectionResult.objects.create(image_upload=img, detection_task=task, is_fake=False, confidence_score=0, status="completed")
    review_request = ReviewRequest.objects.create(detection_result=detection_result, user=request.user, organization=user.organization, reason=reason or "manual review - " + task_type, status1="pending", status2="pending")
    Log.objects.create(user=request.user, operation_type="review_request", related_model="ReviewRequest", related_id=review_request.id)
    return Response({"id": review_request.id, "detection_task_id": task.id, "status": "pending", "reason": review_request.reason, "created_at": timezone.localtime(review_request.request_time).strftime("%Y-%m-%d %H:%M:%S")}, status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_manual_review_by_detection_task(request):
    detection_task_id = request.query_params.get("detection_task_id")
    if not detection_task_id:
        return Response([], status=200)
    try:
        task = DetectionTask.objects.get(id=detection_task_id)
    except DetectionTask.DoesNotExist:
        return Response([], status=200)
    result_ids = task.detection_results.values_list("id", flat=True)
    reviews = ReviewRequest.objects.filter(detection_result_id__in=result_ids).order_by("-request_time")
    data = [{"id": rr.id, "detection_task_id": int(detection_task_id), "status": rr.status1, "admin_status": rr.status2, "reason": rr.reason, "created_at": timezone.localtime(rr.request_time).strftime("%Y-%m-%d %H:%M:%S")} for rr in reviews]
    return Response(data, status=200)
