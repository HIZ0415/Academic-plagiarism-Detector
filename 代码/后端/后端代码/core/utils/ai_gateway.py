from __future__ import annotations

import base64
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from core.call_figure_detection import get_result as legacy_get_result
from core.call_figure_detection import reconnect as legacy_reconnect


class AIGatewayError(RuntimeError):
    """Raised when the backend cannot get a usable response from the AI service."""


_LOCAL_TEXT_DETECTION_SERVICE = None


def run_image_detection_batch(zip_path: str | Path, data_path: str | Path) -> Dict[str, Any] | Any:
    """
    Submit one image-detection batch to the AI side.

    When AI_SERVICE_URL is configured, the backend uses the HTTP JSON protocol.
    Otherwise it falls back to the historical SSH/SCP bridge in call_figure_detection.py.
    """
    service_url = getattr(settings, "AI_SERVICE_URL", "")
    if service_url:
        return _call_http_image_detection(service_url, Path(zip_path), Path(data_path))
    return legacy_get_result(zip_path, data_path)


def run_text_detection_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit a backend-normalized paper/review payload to the AI service.

    When AI_SERVICE_URL is configured, this uses the HTTP JSON protocol. In local
    project runs where only the backend process is started, it falls back to the
    in-repository text DetectionService so paper/review flows still complete.
    """
    service_url = getattr(settings, "AI_SERVICE_URL", "")
    if service_url:
        return _call_http_detection_payload(service_url, payload)
    return _call_local_text_detection_payload(payload)


def reconnect_ai_gateway() -> None:
    """Reconnect only for the legacy SSH bridge. HTTP mode opens one request per batch."""
    if getattr(settings, "AI_SERVICE_URL", ""):
        return
    legacy_reconnect()


def _call_http_image_detection(service_url: str, zip_path: Path, data_path: Path) -> Dict[str, Any]:
    endpoint = service_url.rstrip("/") + "/api/v1/image-detection/batches"
    timeout = int(getattr(settings, "AI_SERVICE_TIMEOUT", 1200))

    payload = {
        "schema_version": "backend-ai-request-v1",
        "task_type": "image",
        "batch_id": zip_path.parent.name,
        "parameters": _read_json_file(data_path),
        "image_names": _list_zip_image_names(zip_path),
        "images_zip_base64": base64.b64encode(zip_path.read_bytes()).decode("ascii"),
    }

    headers = {"Content-Type": "application/json"}
    api_token = getattr(settings, "AI_SERVICE_API_TOKEN", "")
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    req = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            raw_body = resp.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AIGatewayError(f"AI service HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise AIGatewayError(f"AI service unavailable: {exc.reason}") from exc

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise AIGatewayError("AI service returned non-JSON response") from exc


def _call_http_detection_payload(service_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = service_url.rstrip("/") + "/api/v1/detection/batches"
    timeout = int(getattr(settings, "AI_SERVICE_TIMEOUT", 1200))

    headers = {"Content-Type": "application/json"}
    api_token = getattr(settings, "AI_SERVICE_API_TOKEN", "")
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    req = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            raw_body = resp.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AIGatewayError(f"AI service HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise AIGatewayError(f"AI service unavailable: {exc.reason}") from exc

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise AIGatewayError("AI service returned non-JSON response") from exc


def _call_local_text_detection_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    service = _get_local_text_detection_service()
    try:
        return service.handle_request(payload)
    except Exception as exc:
        raise AIGatewayError(f"local AI text detection failed: {exc}") from exc


def _get_local_text_detection_service():
    global _LOCAL_TEXT_DETECTION_SERVICE
    if _LOCAL_TEXT_DETECTION_SERVICE is not None:
        return _LOCAL_TEXT_DETECTION_SERVICE

    service_root = _find_local_ai_service_root()
    service_root_str = str(service_root)
    if service_root_str not in sys.path:
        sys.path.insert(0, service_root_str)

    try:
        from detection_service import DetectionService  # type: ignore
    except Exception as exc:
        raise AIGatewayError(
            "AI_SERVICE_URL is not configured and local AI text service could not be imported"
        ) from exc

    try:
        _LOCAL_TEXT_DETECTION_SERVICE = DetectionService()
    except Exception as exc:
        raise AIGatewayError("failed to initialize local AI text service") from exc

    return _LOCAL_TEXT_DETECTION_SERVICE


def _find_local_ai_service_root() -> Path:
    current_file = Path(__file__).resolve()
    for parent in current_file.parents:
        candidate = parent / "AI服务" / "AI服务器代码"
        if (candidate / "detection_service").is_dir():
            return candidate
    raise AIGatewayError("AI_SERVICE_URL is not configured and local AI service directory was not found")


def _read_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _list_zip_image_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return [
            name
            for name in zf.namelist()
            if not name.endswith("/") and name.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
        ]
