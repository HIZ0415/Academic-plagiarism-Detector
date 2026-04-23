from __future__ import annotations

import base64
import json
import shutil
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict

from .contracts import BACKEND_REQUEST_SCHEMA_VERSION, DetectionContext, DetectionRequest, ImageInput
from .image_detector import ImageDetector


class ValidationError(ValueError):
    pass


class TaskNotImplementedError(NotImplementedError):
    pass


class DetectionService:
    def __init__(self) -> None:
        self._image_detector = ImageDetector()
        self._implemented_tasks = {"image"}
        self._reserved_tasks = {"paper", "review"}

    def health_payload(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "service_version": "ai-detection-service-2026-04",
            "supported_tasks": sorted(self._implemented_tasks),
            "reserved_tasks": sorted(self._reserved_tasks),
            "result_format": "standard-evidence-v1",
            "image_methods": self._image_detector.method_names,
        }

    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        request = self._parse_request(request_data)
        if request.task_type == "image":
            return self._handle_image_request(request).to_dict()
        if request.task_type in self._reserved_tasks:
            raise TaskNotImplementedError(
                f"task_type '{request.task_type}' is reserved but not implemented yet"
            )
        raise ValidationError(f"unsupported task_type: {request.task_type}")

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
        if not isinstance(images_zip_base64, str) or not images_zip_base64:
            raise ValidationError("images_zip_base64 is required")

        return DetectionRequest(
            schema_version=schema_version,
            task_type=task_type,
            batch_id=request_data.get("batch_id"),
            parameters=parameters,
            image_names=image_names,
            images_zip_base64=images_zip_base64,
        )

    def _handle_image_request(self, request: DetectionRequest):
        model_version = str(
            request.parameters.get("model_version") or "image-detector-service-2026-04"
        )
        context = DetectionContext(
            task_type="image",
            parameters=request.parameters,
            model_version=model_version,
            batch_id=request.batch_id,
        )
        with tempfile.TemporaryDirectory(prefix="ai_image_batch_") as temp_dir:
            images = self._extract_images(request, Path(temp_dir))
            return self._image_detector.detect(images, context)

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
