from __future__ import annotations

import base64
import json
import shutil
import tempfile
import threading
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict

from .contracts import BACKEND_REQUEST_SCHEMA_VERSION, DetectionContext, DetectionRequest, ImageInput
from .model_registry import DetectionModelRegistry
from .registry import build_task_handlers
from .service_errors import ValidationError


class DetectionService:
    def __init__(self, model_registry: DetectionModelRegistry | None = None) -> None:
        self._reload_lock = threading.RLock()
        self._model_registry = model_registry or DetectionModelRegistry.load()
        self._task_handlers = build_task_handlers(self._model_registry)
        self._implemented_tasks = {"image"}
        self._reserved_tasks = {"paper", "review"}
        self._reload_count = 0
        self._last_reload_at: str | None = None
        self._last_reload_error: str | None = None

    def health_payload(self) -> Dict[str, Any]:
        self._refresh_registry_if_needed()
        image_handler = self._task_handlers["image"]
        return {
            "status": "ok",
            "service_version": "ai-detection-service-2026-04",
            "supported_tasks": sorted(self._implemented_tasks),
            "reserved_tasks": sorted(self._reserved_tasks),
            "result_format": "standard-evidence-v1",
            **self._model_registry.metadata(),
            "image_profile_details": self._model_registry.describe_image_profiles(),
            "image_methods": image_handler.method_names,
            "registry_reload": self._reload_status_payload(),
        }

    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        self._refresh_registry_if_needed()
        request = self._parse_request(request_data)
        if request.task_type not in self._task_handlers:
            raise ValidationError(f"unsupported task_type: {request.task_type}")

        model_profile = self._resolve_model_profile(request)
        context = DetectionContext(
            task_type=request.task_type,
            parameters=request.parameters,
            model_version=self._resolve_model_version(request, model_profile),
            batch_id=request.batch_id,
            model_profile=model_profile,
        )

        extracted_inputs = None
        if request.task_type == "image":
            with tempfile.TemporaryDirectory(prefix="ai_image_batch_") as temp_dir:
                extracted_inputs = self._extract_images(request, Path(temp_dir))
                return self._task_handlers[request.task_type].detect(
                    request, context, extracted_inputs
                ).to_dict()

        return self._task_handlers[request.task_type].detect(request, context, extracted_inputs).to_dict()

    def management_payload(self, profile_name: str | None = None) -> Dict[str, Any]:
        self._refresh_registry_if_needed()
        payload = {
            "status": "ok",
            **self._model_registry.metadata(),
            "image_profile_details": self._model_registry.describe_image_profiles(),
            "registry_reload": self._reload_status_payload(),
        }
        if profile_name is not None:
            payload["selected_image_profile"] = self._model_registry.describe_image_profile(profile_name)
        return payload

    def build_request_from_files(
        self,
        zip_path: str | Path,
        data_path: str | Path,
        *,
        batch_id: str | None = None,
    ) -> Dict[str, Any]:
        zip_path = Path(zip_path)
        data_path = Path(data_path)
        with data_path.open("r", encoding="utf-8") as handle:
            parameters = json.load(handle)
        with zipfile.ZipFile(zip_path) as zip_file:
            image_names = [
                name
                for name in zip_file.namelist()
                if not name.endswith("/") and Path(name).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
            ]
        return {
            "schema_version": BACKEND_REQUEST_SCHEMA_VERSION,
            "task_type": parameters.get("task_type", "image"),
            "batch_id": batch_id or zip_path.parent.name,
            "parameters": parameters,
            "image_names": image_names,
            "images_zip_base64": base64.b64encode(zip_path.read_bytes()).decode("ascii"),
        }

    def _parse_request(self, request_data: Dict[str, Any]) -> DetectionRequest:
        schema_version = request_data.get("schema_version")
        if schema_version != BACKEND_REQUEST_SCHEMA_VERSION:
            raise ValidationError("unsupported schema_version")

        task_type = request_data.get("task_type")
        if not isinstance(task_type, str) or not task_type:
            raise ValidationError("task_type is required")

        parameters = request_data.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise ValidationError("parameters must be an object")

        image_names = request_data.get("image_names") or []
        if not isinstance(image_names, list):
            raise ValidationError("image_names must be a list")

        images_zip_base64 = request_data.get("images_zip_base64")
        if images_zip_base64 is not None and not isinstance(images_zip_base64, str):
            raise ValidationError("images_zip_base64 must be a string")

        payload_base64 = request_data.get("payload_base64")
        if payload_base64 is not None and not isinstance(payload_base64, str):
            raise ValidationError("payload_base64 must be a string")

        if task_type == "image" and not images_zip_base64:
            raise ValidationError("images_zip_base64 is required")

        return DetectionRequest(
            schema_version=schema_version,
            task_type=task_type,
            batch_id=request_data.get("batch_id"),
            parameters=parameters,
            image_names=image_names,
            images_zip_base64=images_zip_base64,
            payload_base64=payload_base64,
        )

    def _resolve_model_profile(self, request: DetectionRequest) -> str | None:
        if request.task_type != "image":
            return None
        requested_profile = request.parameters.get("model_profile")
        if requested_profile is None:
            return self._model_registry.default_image_profile
        if not isinstance(requested_profile, str):
            raise ValidationError("parameters.model_profile must be a string")
        return self._model_registry.resolve_image_profile(requested_profile).name

    def _resolve_model_version(self, request: DetectionRequest, model_profile: str | None) -> str:
        requested_version = request.parameters.get("model_version")
        if requested_version:
            return str(requested_version)
        if request.task_type == "image":
            profile = self._model_registry.resolve_image_profile(model_profile)
            return profile.model_version
        return f"{request.task_type}-detector-service-2026-04"

    def _refresh_registry_if_needed(self) -> bool:
        with self._reload_lock:
            try:
                current_mtime_ns = self._model_registry.config_path.stat().st_mtime_ns
            except OSError as exc:
                self._last_reload_error = f"failed to stat model registry: {exc}"
                return False

            if current_mtime_ns == self._model_registry.config_mtime_ns:
                return False

            try:
                reloaded_registry = DetectionModelRegistry.load(self._model_registry.config_path)
            except ValidationError as exc:
                self._last_reload_error = str(exc)
                return False

            self._model_registry = reloaded_registry
            self._task_handlers = build_task_handlers(self._model_registry)
            self._reload_count += 1
            self._last_reload_at = datetime.now(timezone.utc).isoformat()
            self._last_reload_error = None
            return True

    def _reload_status_payload(self) -> Dict[str, Any]:
        return {
            "reload_count": self._reload_count,
            "last_reload_at": self._last_reload_at,
            "last_reload_error": self._last_reload_error,
        }

    def _extract_images(self, request: DetectionRequest, temp_dir: Path) -> list[ImageInput]:
        try:
            zip_bytes = base64.b64decode(request.images_zip_base64)
        except ValueError as exc:
            raise ValidationError("images_zip_base64 is not valid base64") from exc

        try:
            zip_file = zipfile.ZipFile(BytesIO(zip_bytes))
        except zipfile.BadZipFile as exc:
            raise ValidationError("images_zip_base64 is not a valid zip file") from exc

        available_entries: dict[str, str] = {}
        with zip_file:
            for name in zip_file.namelist():
                if name.endswith("/"):
                    continue
                suffix = Path(name).suffix.lower()
                if suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
                    continue
                available_entries[Path(name).name] = name

            ordered_names = request.image_names or sorted(available_entries.keys())
            if len(ordered_names) != len(available_entries):
                raise ValidationError("image_names count does not match zip image count")

            images: list[ImageInput] = []
            for index, image_name in enumerate(ordered_names):
                safe_name = Path(image_name).name
                if safe_name not in available_entries:
                    raise ValidationError(f"image '{safe_name}' not found in zip payload")
                source_name = available_entries[safe_name]
                target_path = temp_dir / f"{index:04d}_{safe_name}"
                with zip_file.open(source_name) as source_handle, target_path.open("wb") as target_handle:
                    shutil.copyfileobj(source_handle, target_handle)
                image_id = self._parse_image_id(safe_name)
                images.append(ImageInput(image_name=safe_name, image_path=target_path, image_id=image_id))
            return images

    @staticmethod
    def _parse_image_id(image_name: str) -> int | None:
        stem = Path(image_name).stem
        return int(stem) if stem.isdigit() else None
