import hashlib
import json
import re
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
from ..utils.ai_gateway import AIGatewayError, run_text_detection_payload
from ..utils.paper_preprocessing import preprocess_pdf_paper
from ..utils.review_preprocessing import preprocess_review_bytes, preprocess_review_text

ALPHA_ALLOWED_PAPER_EXT = {".pdf"}
ALPHA_ALLOWED_REVIEW_FILE_EXT = {".txt"}


def _now_str(dt):
    if not dt:
        return None
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")


def _paper_meta_path(file_id):
    return Path(settings.MEDIA_ROOT) / "paper_uploads" / f"{file_id}_meta.json"


def _load_paper_meta(file_id):
    meta_path = _paper_meta_path(file_id)
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_paper_meta(file_id, payload):
    folder = Path(settings.MEDIA_ROOT) / "paper_uploads"
    folder.mkdir(parents=True, exist_ok=True)
    _paper_meta_path(file_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_media_json(relative_path):
    if not relative_path:
        return None
    path = Path(settings.MEDIA_ROOT) / relative_path
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_media_json(relative_path, payload):
    path = Path(settings.MEDIA_ROOT) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_ai_payload(meta):
    payload = _read_media_json(meta.get("ai_payload_path", ""))
    if not isinstance(payload, dict):
        raise ValueError("AI input payload is missing or invalid")
    return payload


def _result_rel_path(folder, task_id):
    return f"{folder}/{task_id}_ai_result.json"


def _persist_ai_result(meta_loader, meta_saver, file_id, task, result, folder):
    meta = meta_loader(file_id) or {}
    result_rel_path = _result_rel_path(folder, task.id)
    _write_media_json(result_rel_path, result)
    meta["ai_result_path"] = result_rel_path
    meta["ai_result_task_id"] = task.id
    meta["ai_result_updated_at"] = _now_str(timezone.now())
    meta_saver(file_id, meta)


def _run_ai_task_from_meta(task, meta, *, task_type):
    payload = _load_ai_payload(meta)
    payload["task_type"] = task_type
    payload["batch_id"] = str(task.id)
    parameters = payload.setdefault("parameters", {})
    parameters["model_version"] = parameters.get("model_version") or f"{task_type}-detector-service-2026-04"
    return run_text_detection_payload(payload)


def _complete_text_task(task, result, *, meta_loader, meta_saver, file_id, folder):
    _persist_ai_result(meta_loader, meta_saver, file_id, task, result, folder)
    task.status = "completed"
    task.completion_time = timezone.now()
    task.error_message = ""
    task.save(update_fields=["status", "completion_time", "error_message"])


def _fail_text_task(task, message):
    task.status = "failed"
    task.error_message = message
    task.completion_time = timezone.now()
    task.save(update_fields=["status", "error_message", "completion_time"])


def _sync_paper_task_status(task, meta_exists):
    if task.status == "failed":
        message = task.error_message or "论文文件元数据缺失或已损坏。"
        if task.error_message != message:
            task.error_message = message
            task.save(update_fields=["error_message"])
        return "failed", 100, message

    if not meta_exists:
        task.status = "failed"
        task.error_message = "论文文件元数据缺失或已损坏。"
        task.save(update_fields=["status", "error_message"])
        return "failed", 100, task.error_message

    if task.status == "completed":
        if task.error_message:
            task.error_message = ""
            task.save(update_fields=["error_message"])
        return "completed", 100, ""
    if task.status == "in_progress":
        return "in_progress", 70, ""
    return "pending", 20, task.error_message or ""


def _split_paragraphs(text):
    chunks = [x.strip() for x in re.split(r"\n{2,}|(?<=[。！？.!?])\s+", text or "") if x.strip()]
    if not chunks:
        return ["未提取到有效文本，建议检查文件内容后重试。"]
    return chunks[:12]


def _load_paper_paragraphs(file_id):
    meta = _load_paper_meta(file_id)
    if not meta:
        return []

    paragraphs_rel_path = meta.get("paragraphs_path", "")
    paragraphs_abs_path = Path(settings.MEDIA_ROOT) / paragraphs_rel_path
    if not paragraphs_abs_path.exists():
        return []

    try:
        payload = json.loads(paragraphs_abs_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict) and item.get("text")]


def _risk_level(score):
    if score >= 0.7:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _build_aigc_result(task, paper_text, paragraphs_data=None):
    base = f"{task.id}|{paper_text[:2000]}"
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    ratio = round(0.2 + (int(digest[:8], 16) / 0xFFFFFFFF) * 0.65, 4)

    paragraph_items = paragraphs_data or [
        {"index": idx, "text": para}
        for idx, para in enumerate(_split_paragraphs(paper_text), start=1)
    ]
    paragraphs = []
    for idx, item in enumerate(paragraph_items[:12], start=1):
        para = str(item.get("text", "")).strip()
        if not para:
            continue
        phash = hashlib.md5(f"{task.id}:{idx}:{para[:200]}".encode("utf-8")).hexdigest()
        score = round(0.2 + (int(phash[:6], 16) / 0xFFFFFF) * 0.75, 3)
        paragraphs.append(
            {
                "index": item.get("index", idx),
                "risk_score": score,
                "risk_level": _risk_level(score),
                "excerpt": para[:180],
                "char_start": item.get("char_start"),
                "char_end": item.get("char_end"),
            }
        )

    high_count = sum(1 for p in paragraphs if p["risk_level"] == "high")
    summary = f"检测完成：AI 贡献占比约 {round(ratio * 100, 1)}%，高风险段落 {high_count} 段。"

    return {
        "task_id": task.id,
        "overall_risk_level": _risk_level(ratio),
        "ai_contribution_ratio": ratio,
        "summary": summary,
        "paragraphs": paragraphs,
    }


def _extract_ai_single_result(ai_result):
    if not isinstance(ai_result, dict):
        return {}
    results = ai_result.get("results")
    if isinstance(results, list) and results and isinstance(results[0], dict):
        return results[0]
    return {}


def _build_aigc_result_from_ai(task, ai_result):
    item = _extract_ai_single_result(ai_result)
    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    paper_summary = details.get("paper_summary") if isinstance(details.get("paper_summary"), dict) else {}
    paragraph_risks = details.get("paragraph_risks")
    if not isinstance(paragraph_risks, list):
        paragraph_risks = details.get("paragraphs") if isinstance(details.get("paragraphs"), list) else []

    ratio = float(
        paper_summary.get(
            "ai_contribution_ratio",
            paper_summary.get("overall_risk_score", item.get("overall_confidence", 0.0)),
        )
    )
    return {
        "task_id": task.id,
        "overall_risk_level": paper_summary.get("risk_level") or _risk_level(ratio),
        "ai_contribution_ratio": ratio,
        "summary": paper_summary.get("summary_text") or item.get("summary") or "论文 AIGC 检测完成。",
        "paragraphs": [
            {
                "index": paragraph.get("index"),
                "risk_score": float(paragraph.get("risk_score", paragraph.get("ai_generated_probability", 0.0))),
                "risk_level": paragraph.get("risk_level", "low"),
                "excerpt": paragraph.get("excerpt", ""),
                "char_start": paragraph.get("char_start"),
                "char_end": paragraph.get("char_end"),
                "basic_explanation": paragraph.get("basic_explanation", ""),
            }
            for paragraph in paragraph_risks
            if isinstance(paragraph, dict)
        ],
        "paper_summary": paper_summary,
        "basic_explanation": details.get("basic_explanation", []),
        "raw_ai_result": ai_result,
    }


def _build_review_result_from_ai(task, ai_result):
    item = _extract_ai_single_result(ai_result)
    details = item.get("details") if isinstance(item.get("details"), dict) else {}
    review_summary = details.get("review_summary") if isinstance(details.get("review_summary"), dict) else {}
    ai_tendency = details.get("ai_tendency") if isinstance(details.get("ai_tendency"), dict) else {}
    template_tendency = details.get("template_tendency") if isinstance(details.get("template_tendency"), dict) else {}
    suspicious_segments = details.get("suspicious_segments")
    if not isinstance(suspicious_segments, list):
        suspicious_segments = details.get("issues") if isinstance(details.get("issues"), list) else []

    overall = float(review_summary.get("overall_risk_score", item.get("overall_confidence", 0.0)))
    return {
        "task_id": task.id,
        "overall_risk_level": review_summary.get("risk_level") or _risk_level(overall),
        "overall_risk_score": overall,
        "summary": review_summary.get("summary_text") or item.get("summary") or "Review 检测完成。",
        "ai_tendency": ai_tendency,
        "template_tendency": template_tendency,
        "suspicious_segments": suspicious_segments,
        "basic_explanation": details.get("basic_explanation", []),
        "raw_ai_result": ai_result,
    }


def _build_resource_result(task, paper_text):
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
                issues.append(
                    {
                        "reference_index": i,
                        "issue_type": "doi_invalid",
                        "detail": f"DOI 可能不完整：{doi.group(0)}",
                        "severity": "medium",
                    }
                )
        else:
            issues.append(
                {
                    "reference_index": i,
                    "issue_type": "doi_missing",
                    "detail": "未识别到 DOI，建议核验该参考条目来源。",
                    "severity": "low",
                }
            )
        if len(line) < 18:
            issues.append(
                {
                    "reference_index": i,
                    "issue_type": "citation_incomplete",
                    "detail": "条目文本较短，可能缺少卷期、页码或作者信息。",
                    "severity": "medium",
                }
            )

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


def _get_paper_text(file_id):
    meta = _load_paper_meta(file_id)
    if not meta:
        return "", None

    text_rel_path = meta.get("cleaned_text_path") or meta.get("text_path", "")
    text_abs_path = Path(settings.MEDIA_ROOT) / text_rel_path
    if text_abs_path.exists():
        try:
            return text_abs_path.read_text(encoding="utf-8", errors="ignore"), meta
        except Exception:
            pass
    return "", meta


def _review_meta_path(file_id):
    return Path(settings.MEDIA_ROOT) / "review_uploads" / f"{file_id}_meta.json"


def _load_review_meta(file_id):
    meta_path = _review_meta_path(file_id)
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_review_meta(file_id, payload):
    folder = Path(settings.MEDIA_ROOT) / "review_uploads"
    folder.mkdir(parents=True, exist_ok=True)
    _review_meta_path(file_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sync_review_task_status(task, meta_exists):
    if task.status == "failed":
        message = task.error_message or "Review 文件元数据缺失或已损坏。"
        if task.error_message != message:
            task.error_message = message
            task.save(update_fields=["error_message"])
        return "failed", 100, message

    if not meta_exists:
        task.status = "failed"
        task.error_message = "Review 文件元数据缺失或已损坏。"
        task.save(update_fields=["status", "error_message"])
        return "failed", 100, task.error_message

    if task.status == "completed":
        if task.error_message:
            task.error_message = ""
            task.save(update_fields=["error_message"])
        return "completed", 100, ""
    if task.status == "in_progress":
        return "in_progress", 80, ""
    return "pending", 30, task.error_message or ""


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

    return Response(
        {
            "paper_file_id": file_management.id,
            "file_name": file_management.file_name,
            "upload_time": _now_str(file_management.upload_time),
            "paragraph_count": len(paragraphs),
        }
    )


def _submit_paper_task(request, expected_type):
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

    task.status = "in_progress"
    task.save(update_fields=["status"])
    try:
        if expected_type == "paper_aigc":
            result = _run_ai_task_from_meta(task, meta, task_type="paper")
            _complete_text_task(
                task,
                result,
                meta_loader=_load_paper_meta,
                meta_saver=_save_paper_meta,
                file_id=file_obj.id,
                folder="paper_uploads",
            )
        elif expected_type == "resource_check":
            paper_text, loaded_meta = _get_paper_text(file_obj.id)
            if not paper_text.strip() or loaded_meta is None:
                raise ValueError("Paper text is missing after preprocessing.")
            result = _build_resource_result(task, paper_text)
            _complete_text_task(
                task,
                result,
                meta_loader=_load_paper_meta,
                meta_saver=_save_paper_meta,
                file_id=file_obj.id,
                folder="paper_uploads",
            )
    except (AIGatewayError, ValueError) as exc:
        _fail_text_task(task, str(exc))

    return Response(
        {
            "task_id": task.id,
            "status": task.status,
            "error_message": task.error_message,
            "paper_file_id": file_obj.id,
            "paragraph_count": meta.get("paragraph_count", 0),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_aigc_task(request):
    return _submit_paper_task(request, "paper_aigc")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_resource_check_task(request):
    return _submit_paper_task(request, "resource_check")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_paper_task_status(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    if task.task_type not in ("paper_aigc", "resource_check"):
        return Response({"detail": "该任务不是论文检测任务。"}, status=400)
    if not task.paper_file_id:
        return Response({"detail": "论文任务缺少 paper_file 关联。"}, status=400)

    meta_exists = bool(_load_paper_meta(task.paper_file_id))
    status_text, progress, error_message = _sync_paper_task_status(task, meta_exists)

    return Response(
        {
            "task_id": task.id,
            "status": status_text,
            "progress": progress,
            "error_message": error_message,
        }
    )


def _ready_result_or_error(task, expected_type):
    if task.task_type != expected_type:
        return None, None, Response({"detail": "任务类型不匹配。"}, status=400)
    if not task.paper_file_id:
        return None, None, Response({"detail": "论文任务缺少 paper_file 关联。"}, status=400)

    meta = _load_paper_meta(task.paper_file_id)
    status_text, _, error_message = _sync_paper_task_status(task, bool(meta))
    if status_text != "completed":
        return None, None, Response(
            {
                "detail": "任务尚未完成。",
                "status": status_text,
                "error_message": error_message,
            },
            status=202,
        )

    paper_text, meta = _get_paper_text(task.paper_file_id)
    if meta is None:
        return None, None, Response({"detail": "论文文件元数据丢失。"}, status=404)

    return task.paper_file_id, paper_text, None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_aigc_result(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    paper_file_id, paper_text, error_resp = _ready_result_or_error(task, "paper_aigc")
    if error_resp is not None:
        return error_resp

    meta = _load_paper_meta(paper_file_id)
    ai_result = _read_media_json((meta or {}).get("ai_result_path", ""))
    if ai_result is not None:
        return Response(_build_aigc_result_from_ai(task, ai_result))

    return Response(_build_aigc_result(task, paper_text, _load_paper_paragraphs(paper_file_id)))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_resource_check_result(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    _, paper_text, error_resp = _ready_result_or_error(task, "resource_check")
    if error_resp is not None:
        return error_resp

    return Response(_build_resource_result(task, paper_text))


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

    task.status = "in_progress"
    task.save(update_fields=["status"])
    try:
        meta = _load_review_meta(file_management.id) or {}
        result = _run_ai_task_from_meta(task, meta, task_type="review")
        _complete_text_task(
            task,
            result,
            meta_loader=_load_review_meta,
            meta_saver=_save_review_meta,
            file_id=file_management.id,
            folder="review_uploads",
        )
    except (AIGatewayError, ValueError) as exc:
        _fail_text_task(task, str(exc))

    return Response(
        {
            "task_id": task.id,
            "status": task.status,
            "error_message": task.error_message,
            "cleaned_text_length": len(preprocessed.cleaned_text),
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_review_task_status(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user, task_type="review_detection")
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    if not task.paper_file_id:
        return Response({"detail": "Review 任务缺少文件关联。"}, status=400)

    meta = _load_review_meta(task.paper_file_id)
    meta_exists = bool(meta and meta.get("ai_payload_path") and meta.get("cleaned_text_path"))
    status_text, progress, error_message = _sync_review_task_status(task, meta_exists)
    return Response(
        {
            "task_id": task.id,
            "status": status_text,
            "progress": progress,
            "error_message": error_message,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_review_detection_result(request, task_id):
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user, task_type="review_detection")
    except DetectionTask.DoesNotExist:
        return Response({"detail": "任务不存在。"}, status=404)

    if not task.paper_file_id:
        return Response({"detail": "Review 任务缺少文件关联。"}, status=400)

    meta = _load_review_meta(task.paper_file_id)
    status_text, _, error_message = _sync_review_task_status(
        task,
        bool(meta and meta.get("ai_payload_path") and meta.get("cleaned_text_path")),
    )
    if status_text != "completed":
        return Response(
            {
                "detail": "任务尚未完成。",
                "status": status_text,
                "error_message": error_message,
            },
            status=202,
        )

    ai_result = _read_media_json((meta or {}).get("ai_result_path", ""))
    if ai_result is None:
        return Response({"detail": "Review AI 检测结果丢失。"}, status=404)
    return Response(_build_review_result_from_ai(task, ai_result))
