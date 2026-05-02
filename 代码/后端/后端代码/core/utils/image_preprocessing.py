from __future__ import annotations

import io
import json
import os
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
PDF_SUFFIXES = {".pdf"}
ZIP_SUFFIXES = {".zip"}

IMAGE_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/bmp",
    "image/gif",
}
PDF_CONTENT_TYPES = {"application/pdf"}
ZIP_CONTENT_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
}


@dataclass(frozen=True, slots=True)
class ExtractedImagePayload:
    image_bytes: bytes
    source_name: str
    extracted_from_pdf: bool
    page_number: int | None = None


@dataclass(frozen=True, slots=True)
class DetectionBatchImage:
    image_id: int
    image_path: Path


def detect_upload_kind(file_name: str, content_type: str, raw_bytes: bytes) -> str:
    suffix = Path(file_name or "").suffix.lower()
    normalized_content_type = (content_type or "").split(";", 1)[0].strip().lower()

    if suffix in PDF_SUFFIXES or normalized_content_type in PDF_CONTENT_TYPES or raw_bytes.startswith(b"%PDF"):
        return "pdf"
    if suffix in ZIP_SUFFIXES or normalized_content_type in ZIP_CONTENT_TYPES or _is_zip_bytes(raw_bytes):
        return "zip"
    if suffix in IMAGE_SUFFIXES or normalized_content_type in IMAGE_CONTENT_TYPES or _is_image_bytes(raw_bytes):
        return "image"
    raise ValueError("unsupported upload type")


def save_original_upload(file_name: str, raw_bytes: bytes, folder: str) -> str:
    from django.core.files.base import ContentFile
    from django.core.files.storage import FileSystemStorage

    fs = FileSystemStorage()
    unique_name = f"{uuid.uuid4().hex}_{Path(file_name).name}"
    return fs.save(f"{folder}/{unique_name}", ContentFile(raw_bytes))


def preprocess_uploaded_image_resource(file_management, file_name: str, content_type: str, raw_bytes: bytes) -> int:
    from core.models import ImageUpload

    kind = detect_upload_kind(file_name, content_type, raw_bytes)
    created = 0

    if kind == "pdf":
        for payload in extract_images_from_pdf_bytes(raw_bytes, source_name=file_name):
            _create_image_upload(file_management, payload)
            created += 1
        return created

    if kind == "zip":
        for payload in extract_images_from_zip_bytes(raw_bytes):
            _create_image_upload(file_management, payload)
            created += 1
        return created

    image_name = f"{file_management.id}_{Path(file_name).name}"
    payload = ExtractedImagePayload(
        image_bytes=_normalize_image_bytes(raw_bytes, image_name),
        source_name=image_name,
        extracted_from_pdf=False,
    )
    _create_image_upload(file_management, payload)
    return 1


def extract_images_from_pdf_bytes(raw_bytes: bytes, *, source_name: str) -> list[ExtractedImagePayload]:
    import fitz

    try:
        pdf_document = fitz.open(stream=raw_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"failed to open PDF '{source_name}'") from exc

    extracted: list[ExtractedImagePayload] = []
    with pdf_document:
        for page_index in range(pdf_document.page_count):
            page = pdf_document.load_page(page_index)
            try:
                image_list = page.get_images(full=True)
                for image_index, image_meta in enumerate(image_list, start=1):
                    base_image = pdf_document.extract_image(image_meta[0])
                    image_bytes = base_image.get("image", b"")
                    image_ext = base_image.get("ext") or "png"
                    image_name = (
                        f"{Path(source_name).stem}_page{page_index + 1}_image{image_index}.{image_ext}"
                    )
                    extracted.append(
                        ExtractedImagePayload(
                            image_bytes=_normalize_image_bytes(image_bytes, image_name),
                            source_name=image_name,
                            extracted_from_pdf=True,
                            page_number=page_index + 1,
                        )
                    )
            finally:
                del page
    return extracted


def extract_images_from_zip_bytes(raw_bytes: bytes) -> list[ExtractedImagePayload]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError("uploaded file is not a valid ZIP archive") from exc

    extracted: list[ExtractedImagePayload] = []
    with archive:
        for member_name in archive.namelist():
            info = archive.getinfo(member_name)
            if info.is_dir():
                continue

            suffix = Path(member_name).suffix.lower()
            file_bytes = archive.read(member_name)

            if suffix in IMAGE_SUFFIXES:
                extracted.append(
                    ExtractedImagePayload(
                        image_bytes=_normalize_image_bytes(file_bytes, member_name),
                        source_name=Path(member_name).name,
                        extracted_from_pdf=False,
                    )
                )
                continue

            if suffix in PDF_SUFFIXES:
                extracted.extend(extract_images_from_pdf_bytes(file_bytes, source_name=member_name))

    return extracted


def build_detection_batch_artifacts(
    batch_dir: str | Path,
    images: Iterable[DetectionBatchImage],
    *,
    cmd_block_size: int,
    urn_k: float,
    if_use_llm: bool,
) -> tuple[Path, Path]:
    batch_dir = Path(batch_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)

    zip_path = batch_dir / "img.zip"
    data_path = batch_dir / "data.json"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for image in sorted(images, key=lambda item: item.image_id):
            source_path = Path(image.image_path)
            arcname = f"{int(image.image_id):08d}{source_path.suffix.lower()}"
            zf.write(source_path, arcname=arcname)

    data_path.write_text(
        json.dumps(
            {
                "cmd_block_size": int(cmd_block_size),
                "urn_k": float(urn_k),
                "if_use_llm": bool(if_use_llm),
            },
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return zip_path, data_path


def _create_image_upload(file_management, payload: ExtractedImagePayload) -> None:
    from core.models import ImageUpload

    relative_image_path = _save_image_bytes(payload.image_bytes, payload.source_name)
    ImageUpload.objects.create(
        file_management=file_management,
        image=relative_image_path,
        extracted_from_pdf=payload.extracted_from_pdf,
        page_number=payload.page_number,
        isDetect=False,
        isReview=False,
        isFake=False,
    )


def _save_image_bytes(image_bytes: bytes, image_name: str) -> str:
    from django.conf import settings

    unique_image_name = f"{uuid.uuid4().hex}_{Path(image_name).name}"
    relative_path = os.path.join("extracted_images", unique_image_name).replace("\\", "/")
    full_path = Path(settings.MEDIA_ROOT) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(io.BytesIO(image_bytes)) as image:
        image.save(full_path)

    return relative_path


def _normalize_image_bytes(image_bytes: bytes, image_name: str) -> bytes:
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            normalized = image.convert("RGB") if image.mode not in ("RGB", "L") else image.copy()
            output = io.BytesIO()
            suffix = Path(image_name).suffix.lower()
            target_format = "PNG"
            if suffix in {".jpg", ".jpeg"}:
                target_format = "JPEG"
            elif suffix == ".bmp":
                target_format = "BMP"
            elif suffix == ".gif":
                target_format = "GIF"
            normalized.save(output, format=target_format)
            return output.getvalue()
    except UnidentifiedImageError as exc:
        raise ValueError(f"failed to decode image '{image_name}'") from exc


def _is_zip_bytes(raw_bytes: bytes) -> bool:
    return raw_bytes.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))


def _is_image_bytes(raw_bytes: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(raw_bytes)) as image:
            image.verify()
        return True
    except Exception:
        return False
