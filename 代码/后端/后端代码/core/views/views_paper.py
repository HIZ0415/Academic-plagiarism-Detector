"""论文 / Review 检测视图
============================

任务 015 – 论文检测链路 (paper_aigc + resource_check)
任务 017 – Review 检测链路 (review_detection)

改动要点（相对原版）：
  * submit 接口改为派发 Celery 异步任务（tasks_paper.py）
  * status 接口直接读取 DB 状态，去掉基于时间的模拟
  * result 接口读取 Celery 写入的 JSON 文件
  * 新增 get_review_detection_result 接口
"""
import json
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import DetectionTask, FileManagement, Log, User
from ..utils.paper_preprocessing import preprocess_pdf_paper
from ..utils.review_preprocessing import preprocess_review_bytes, preprocess_review_text

ALPHA_ALLOWED_PAPER_EXT = {".pdf"}
ALPHA_ALLOWED_REVIEW_FILE_EXT = {".txt"}

MEDIA = Path(settings.MEDIA_ROOT)


# ═══════════════════════════════════════════════════════════════════════════════
#  通用辅助
# ═══════════════════════════════════════════════════════════════════════════════

def _now_str(dt):
    if not dt:
        return None
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")


# ---- Paper meta ----

def _paper_meta_path(file_id):
    return MEDIA / "paper_uploads" / f"{file_id}_meta.json"


def _load_paper_meta(file_id):
    meta_path = _paper_meta_path(file_id)
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_paper_meta(file_id, payload):
    folder = MEDIA / "paper_uploads"
    folder.mkdir(parents=True, exist_ok=True)
    _paper_meta_path(file_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---- Review meta ----

def _review_meta_path(file_id):
    return MEDIA / "review_uploads" / f"{file_id}_meta.json"


def _load_review_meta(file_id):
    meta_path = _review_meta_path(file_id)
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_review_meta(file_id, payload):
    folder = MEDIA / "review_uploads"
    folder.mkdir(parents=True, exist_ok=True)
    _review_meta_path(file_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---- Result JSON helpers ----

def _paper_result_path(file_id, result_type: str):
    return MEDIA / "paper_uploads" / f"{file_id}_{result_type}_result.json"


def _review_result_path(file_id):
    return MEDIA / "review_uploads" / f"{file_id}_detection_result.json"


def _load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  论文上传（保持原逻辑不变）
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_paper(request):
    user = User.objects.get(id=request.user.id)
    if not user.has_permission("upload"):
        return Response({"detail": "该用户没有上传文件权限。"}, status=403)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"detail": "缺少 file 字段。"}, status=400)

    file_name = uploaded_file.name or "paper_upload"
    suffix = Path(file_name).suffix.lower()
    if suffix not in ALPHA_ALLOWED_PAPER_EXT:
        return Response({"detail": "仅支持 PDF 文件。"}, status=400)

    content_type = uploaded_file.content_type or "application/octet-stream"
    raw_bytes = uploaded_file.read()

    try:
        preprocessed = preprocess_pdf_paper(raw_bytes, source_name=file_name)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    file_management = FileManagement.objects.create(
        organization=user.organization,
        user=request.user,
        file_name=file_name,
        file_size=len(raw_bytes),
        file_type=content_type,
    )

    fs = FileSystemStorage()
    unique_part = uuid.uuid4().hex[:10]
    binary_rel_path = fs.save(
        f"paper_uploads/{file_management.id}_{unique_part}_{file_name}",
        ContentFile(raw_bytes),
    )
    raw_text_rel_path = fs.save(
        f"paper_uploads/{file_management.id}_raw_text.txt",
        ContentFile(preprocessed.raw_text.encode("utf-8")),
    )
    cleaned_text_rel_path = fs.save(
        f"paper_uploads/{file_management.id}_cleaned_text.txt",
        ContentFile(preprocessed.cleaned_text.encode("utf-8")),
    )
    paragraphs = [paragraph.as_dict() for paragraph in preprocessed.paragraphs]
    paragraphs_rel_path = fs.save(
        f"paper_uploads/{file_management.id}_paragraphs.json",
        ContentFile(json.dumps(paragraphs, ensure_ascii=False, indent=2).encode("utf-8")),
    )
    ai_payload_rel_path = fs.save(
        f"paper_uploads/{file_management.id}_ai_input.json",
        ContentFile(json.dumps(preprocessed.ai_payload, ensure_ascii=False, indent=2).encode("utf-8")),
    )

    _save_paper_meta(
        file_management.id,
        {
            "paper_file_id": file_management.id,
            "file_name": file_name,
            "file_type": content_type,
            "binary_path": binary_rel_path,
            "text_path": cleaned_text_rel_path,
            "raw_text_path": raw_text_rel_path,
            "cleaned_text_path": cleaned_text_rel_path,
            "paragraphs_path": paragraphs_rel_path,
            "ai_payload_path": ai_payload_rel_path,
            "paragraph_count": len(paragraphs),
            "cleaned_text_length": len(preprocessed.cleaned_text),
            "upload_time": _now_str(file_management.upload_time),
        },
    )

    Log.objects.create(
        user=request.user,
        operation_type="upload",
        related_model="FileManagement",
        related_id=file_management.id,
    )

    return Response({
        "paper_file_id": file_management.id,
        "file_name": file_management.file_name,
        "upload_time": _now_str(file_management.upload_time),
        "paragraph_count": len(paragraphs),
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  论文检测提交 — 派发 Celery 异步任务
# ═══════════════════════════════════════════════════════════════════════════════

def _submit_paper_task(request, expected_type):
    """通用提交逻辑：paper_aigc / resource_check"""
    user = User.objects.get(id=request.user.id)
    if not user.has_permission("submit"):
        return Response({"detail": "该用户没有提交检测权限。"}, status=403)

    paper_file_id = request.data.get("paper_file_id")
    task_name = (request.data.get("task_name") or "paper-task").strip()
    if not paper_file_id:
        return Response({"detail": "paper_file_id 不能为空。"}, status=400)
    try:
        paper_file_id = int(paper_file_id)
    except Exception:
        return Response({"detail": "paper_file_id 必须为整数。"}, status=400)

    try:
        file_obj = FileManagement.objects.get(id=paper_file_id, user=request.user)
    except FileManagement.DoesNotExist:
        return Response({"detail": "paper_file_id 不存在或无访问权限。"}, status=404)

    meta = _load_paper_meta(file_obj.id)
    if not meta or not meta.get("ai_payload_path") or int(meta.get("paragraph_count") or 0) <= 0:
        return Response({"detail": "Paper preprocessing output is missing or invalid."}, status=400)

    task = DetectionTask.objects.create(
        organization=user.organization,
        user=request.user,
        task_type=expected_type,
        paper_file=file_obj,
        task_name=task_name,
        status="pending",
        error_message="",
        if_use_llm=(expected_type == "paper_aigc"),
    )

    Log.objects.create(
        user=request.user,
        operation_type="detection",
        related_model="DetectionTask",
        related_id=task.id,
    )

    # ★ 派发 Celery 异步任务
    from ..tasks_paper import run_paper_aigc_detection, run_resource_check_detection
    if expected_type == "paper_aigc":
        run_paper_aigc_detection.delay(task.id)
    else:
        run_resource_check_detection.delay(task.id)

    return Response({
        "task_id": task.id,
        "status": task.status,
        "paper_file_id": file_obj.id,
        "paragraph_count": meta.get("paragraph_count", 0),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_aigc_task(request):
    return _submit_paper_task(request, "paper_aigc")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_resource_check_task(request):
    return _submit_paper_task(request, "resource_check")


# ═══════════════════════════════════════════════════════════════════════════════
#  论文检测状态查询 — 直接读 DB，不再时间模拟
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_paper_task_status(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    if task.task_type not in ("paper_aigc", "resource_check"):
        return Response({"detail": "该任务不是论文检测任务。"}, status=400)

    progress_map = {
        "pending": 10,
        "in_progress": 60,
        "completed": 100,
        "failed": 100,
    }

    return Response({
        "task_id": task.id,
        "status": task.status,
        "progress": progress_map.get(task.status, 0),
        "error_message": task.error_message or "",
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  论文检测结果 — 从 Celery 落盘的 JSON 读取
# ═══════════════════════════════════════════════════════════════════════════════

def _ready_result_or_error(task, expected_type):
    """检查任务状态，如果完成则返回 file_id，否则返回错误 Response。"""
    if task.task_type != expected_type:
        return None, Response({"detail": "任务类型不匹配。"}, status=400)
    if not task.paper_file_id:
        return None, Response({"detail": "论文任务缺少 paper_file 关联。"}, status=400)

    if task.status == "failed":
        return None, Response({
            "detail": "任务执行失败。",
            "status": "failed",
            "error_message": task.error_message or "",
        }, status=400)

    if task.status != "completed":
        return None, Response({
            "detail": "任务尚未完成。",
            "status": task.status,
            "error_message": task.error_message or "",
        }, status=202)

    return task.paper_file_id, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_aigc_result(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    file_id, error_resp = _ready_result_or_error(task, "paper_aigc")
    if error_resp is not None:
        return error_resp

    result = _load_json(_paper_result_path(file_id, "aigc"))
    if result is None:
        return Response({"detail": "检测结果文件尚未生成，请稍后重试。"}, status=202)

    return Response(result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_resource_check_result(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    file_id, error_resp = _ready_result_or_error(task, "resource_check")
    if error_resp is not None:
        return error_resp

    result = _load_json(_paper_result_path(file_id, "resource"))
    if result is None:
        return Response({"detail": "检测结果文件尚未生成，请稍后重试。"}, status=202)

    return Response(result)


# ═══════════════════════════════════════════════════════════════════════════════
#  Review 检测提交 — 派发 Celery 异步任务
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_review_detection_task(request):
    user = User.objects.get(id=request.user.id)
    if not user.has_permission("submit"):
        return Response({"detail": "该用户没有提交检测权限。"}, status=403)

    task_name = (request.data.get("task_name") or "review-task").strip()
    raw_text = (request.data.get("text") or "").strip()
    uploaded_file = request.FILES.get("file")

    if not raw_text and not uploaded_file:
        return Response({"detail": "请提供 text 或 txt 文件。"}, status=400)

    file_name = "review_input.txt"
    file_type = "text/plain"
    raw_bytes = (raw_text or "").encode("utf-8")
    try:
        preprocessed = preprocess_review_text(raw_text, source_name=file_name)
    except ValueError:
        preprocessed = None

    if uploaded_file is not None:
        file_name = uploaded_file.name or "review_input.txt"
        suffix = Path(file_name).suffix.lower()
        if suffix not in ALPHA_ALLOWED_REVIEW_FILE_EXT:
            return Response({"detail": "Review 检测仅支持文本输入或 TXT 文件。"}, status=400)
        file_type = uploaded_file.content_type or "text/plain"
        raw_bytes = uploaded_file.read()
        try:
            preprocessed = preprocess_review_bytes(raw_bytes, source_name=file_name)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

    if preprocessed is None:
        return Response({"detail": "未读取到有效的 Review 文本内容。"}, status=400)

    file_management = FileManagement.objects.create(
        organization=user.organization,
        user=request.user,
        file_name=file_name,
        file_size=len(raw_bytes),
        file_type=file_type,
    )

    fs = FileSystemStorage()
    raw_text_rel_path = fs.save(
        f"review_uploads/{file_management.id}_raw_text.txt",
        ContentFile(preprocessed.raw_text.encode("utf-8")),
    )
    cleaned_text_rel_path = fs.save(
        f"review_uploads/{file_management.id}_cleaned_text.txt",
        ContentFile(preprocessed.cleaned_text.encode("utf-8")),
    )
    ai_payload_rel_path = fs.save(
        f"review_uploads/{file_management.id}_ai_input.json",
        ContentFile(json.dumps(preprocessed.ai_payload, ensure_ascii=False, indent=2).encode("utf-8")),
    )
    _save_review_meta(
        file_management.id,
        {
            "review_file_id": file_management.id,
            "file_name": file_name,
            "file_type": file_type,
            "text_path": cleaned_text_rel_path,
            "raw_text_path": raw_text_rel_path,
            "cleaned_text_path": cleaned_text_rel_path,
            "ai_payload_path": ai_payload_rel_path,
            "encoding": preprocessed.encoding,
            "cleaned_text_length": len(preprocessed.cleaned_text),
            "upload_time": _now_str(file_management.upload_time),
        },
    )

    task = DetectionTask.objects.create(
        organization=user.organization,
        user=request.user,
        task_type="review_detection",
        paper_file=file_management,
        task_name=task_name,
        status="pending",
        error_message="",
        if_use_llm=False,
    )
    Log.objects.create(
        user=request.user,
        operation_type="detection",
        related_model="DetectionTask",
        related_id=task.id,
    )

    # ★ 派发 Celery 异步任务
    from ..tasks_paper import run_review_detection
    run_review_detection.delay(task.id)

    return Response({
        "task_id": task.id,
        "status": task.status,
        "cleaned_text_length": len(preprocessed.cleaned_text),
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  Review 检测状态 — 直接读 DB
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_review_task_status(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user, task_type="review_detection")
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    progress_map = {
        "pending": 10,
        "in_progress": 60,
        "completed": 100,
        "failed": 100,
    }

    return Response({
        "task_id": task.id,
        "status": task.status,
        "progress": progress_map.get(task.status, 0),
        "error_message": task.error_message or "",
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  Review 检测结果查询 — 任务 017 新增接口
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_review_detection_result(request, task_id):
    """
    GET /api/review/<task_id>/result/
    返回 Review 检测的 AI 倾向分析结果。
    """
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    if task.task_type != "review_detection":
        return Response({"detail": "该任务不是 Review 检测任务。"}, status=400)
    if not task.paper_file_id:
        return Response({"detail": "Review 任务缺少文件关联。"}, status=400)

    if task.status == "failed":
        return Response({
            "detail": "任务执行失败。",
            "status": "failed",
            "error_message": task.error_message or "",
        }, status=400)

    if task.status != "completed":
        return Response({
            "detail": "任务尚未完成。",
            "status": task.status,
            "error_message": task.error_message or "",
        }, status=202)

    result = _load_json(_review_result_path(task.paper_file_id))
    if result is None:
        return Response({"detail": "检测结果文件尚未生成，请稍后重试。"}, status=202)

    return Response(result)
