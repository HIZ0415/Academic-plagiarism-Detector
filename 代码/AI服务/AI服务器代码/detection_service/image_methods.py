from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

from .base import DetectionMethod
from .contracts import DetectionContext, DetectionEvidence, ImageInput


DEFAULT_LLM_TEXT = ""


def _normalize_probability(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return 0.0
        return float(np.asarray(value).reshape(-1)[0])
    if isinstance(value, (list, tuple)):
        if not value:
            return 0.0
        return _normalize_probability(value[0])
    return float(value)


def _ensure_mask(value: object) -> np.ndarray:
    if value is None:
        return np.zeros((2, 2), dtype=np.float32)
    mask = np.asarray(value, dtype=np.float32)
    if mask.ndim == 3:
        mask = np.squeeze(mask)
    if mask.ndim == 0:
        mask = np.zeros((2, 2), dtype=np.float32)
    return mask


def _mask_confidence(mask: np.ndarray) -> float:
    if mask.size == 0:
        return 0.0
    max_value = float(mask.max()) if mask.size else 0.0
    if max_value <= 0:
        return 0.0
    normalized = mask / max_value
    return float(np.clip(normalized.mean(), 0.0, 1.0))


def _cv2_read_image(image_path: Path) -> np.ndarray | None:
    buffer = np.fromfile(str(image_path), dtype=np.uint8)
    if buffer.size == 0:
        return None
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def _cv2_write_image(image_path: str | Path, image: np.ndarray, params: list[int] | None = None) -> bool:
    image_path = Path(image_path)
    extension = image_path.suffix.lower() or ".png"
    success, encoded = cv2.imencode(extension, image, params or [])
    if not success:
        return False
    image_path.write_bytes(encoded.tobytes())
    return True


def _build_evidence(
    image_name: str,
    method: str,
    category: str,
    evidence_type: str,
    suspicious: bool,
    confidence: float,
    summary: str,
    *,
    artifacts: dict | None = None,
    metadata: dict | None = None,
) -> DetectionEvidence:
    return DetectionEvidence(
        evidence_id=f"{image_name}:{method}",
        method=method,
        category=category,
        evidence_type=evidence_type,
        suspicious=bool(suspicious),
        confidence=float(np.clip(confidence, 0.0, 1.0)),
        summary=summary,
        artifacts=artifacts or {},
        metadata=metadata or {},
    )


def _build_failed_evidence(
    image_name: str,
    method: str,
    category: str,
    evidence_type: str,
    message: str,
    *,
    artifacts: dict | None = None,
    metadata: dict | None = None,
) -> DetectionEvidence:
    return _build_evidence(
        image_name,
        method,
        category,
        evidence_type,
        suspicious=False,
        confidence=0.0,
        summary=message,
        artifacts=artifacts,
        metadata=metadata,
    )


class ELAMethod(DetectionMethod):
    method_name = "ela"
    category = "visual"
    evidence_type = "mask"

    def run_batch(
        self,
        images: Sequence[ImageInput],
        context: DetectionContext,
    ) -> list[DetectionEvidence]:
        def _process(image: ImageInput) -> DetectionEvidence:
            original = _cv2_read_image(image.image_path)
            if original is None:
                raise ValueError(f"failed to read image: {image.image_path}")
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_path = temp_file.name
            try:
                if not _cv2_write_image(temp_path, original, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                    raise ValueError(f"failed to write temp JPEG: {temp_path}")
                compressed = _cv2_read_image(Path(temp_path))
                if compressed is None:
                    raise ValueError(f"failed to read temp JPEG: {temp_path}")
                ela = cv2.absdiff(original, compressed) * 15
                mask = cv2.cvtColor(ela, cv2.COLOR_BGR2GRAY).astype(np.float32)
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            confidence = _mask_confidence(mask)
            return _build_evidence(
                image.image_name,
                self.method_name,
                self.category,
                self.evidence_type,
                suspicious=confidence >= context.threshold,
                confidence=confidence,
                summary="ELA heatmap generated for localization.",
                artifacts={"mask": mask},
            )

        with ThreadPoolExecutor() as executor:
            return list(executor.map(_process, images))


class ExifMethod(DetectionMethod):
    method_name = "exif"
    category = "metadata"
    evidence_type = "flags"

    def run_batch(
        self,
        images: Sequence[ImageInput],
        context: DetectionContext,
    ) -> list[DetectionEvidence]:
        def _process(image: ImageInput) -> DetectionEvidence:
            flags = {"photoshop": False, "time_modified": False}
            summary_parts: list[str] = []
            try:
                with Image.open(image.image_path) as img:
                    exif_data = img.getexif()
            except Exception:
                exif_data = None
            exif: dict[str, object] = {}
            if exif_data:
                for tag_id, value in exif_data.items():
                    exif[TAGS.get(tag_id, str(tag_id))] = value
                software = str(exif.get("Software", ""))
                if "Photoshop" in software:
                    flags["photoshop"] = True
                    summary_parts.append("Photoshop metadata detected.")
                original_time = exif.get("DateTimeOriginal")
                modified_time = exif.get("DateTime")
                if original_time and modified_time and original_time != modified_time:
                    flags["time_modified"] = True
                    summary_parts.append("Original and modified timestamps differ.")
            suspicious = any(flags.values())
            if not summary_parts:
                summary_parts.append("No suspicious EXIF metadata detected.")
            return _build_evidence(
                image.image_name,
                self.method_name,
                self.category,
                self.evidence_type,
                suspicious=suspicious,
                confidence=1.0 if suspicious else 0.0,
                summary=" ".join(summary_parts),
                metadata={"flags": flags, "raw_exif_keys": sorted(exif.keys())},
            )

        with ThreadPoolExecutor() as executor:
            return list(executor.map(_process, images))


class CopyMoveMethod(DetectionMethod):
    method_name = "cmd"
    category = "visual"
    evidence_type = "mask"

    def run_batch(
        self,
        images: Sequence[ImageInput],
        context: DetectionContext,
    ) -> list[DetectionEvidence]:
        try:
            from skimage.feature import match_template
        except ModuleNotFoundError:
            return [
                _build_failed_evidence(
                    image.image_name,
                    self.method_name,
                    self.category,
                    self.evidence_type,
                    "skimage is not installed; copy-move detector returned a placeholder result.",
                    artifacts={"mask": np.zeros((2, 2), dtype=np.float32)},
                )
                for image in images
            ]

        block_size = int(context.parameters.get("cmd_block_size", 64))
        step = max(1, block_size // 2)

        def _process(image: ImageInput) -> DetectionEvidence:
            img = _cv2_read_image(image.image_path)
            if img is None:
                raise ValueError(f"failed to read image: {image.image_path}")
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            matches: list[tuple[int, int, int, int]] = []
            for y in range(0, max(1, height - block_size), step):
                for x in range(0, max(1, width - block_size), step):
                    block = gray[y : y + block_size, x : x + block_size]
                    if block.shape != (block_size, block_size):
                        continue
                    result = match_template(gray, block)
                    loc = np.where(result >= 0.9)
                    for pt in zip(*loc[::-1]):
                        if abs(pt[0] - x) > block_size or abs(pt[1] - y) > block_size:
                            matches.append((x, y, pt[0], pt[1]))
            mask = np.zeros_like(gray, dtype=np.float32)
            for x1, y1, x2, y2 in matches:
                mask[y1 : y1 + block_size, x1 : x1 + block_size] = 255.0
                mask[y2 : y2 + block_size, x2 : x2 + block_size] = 255.0
            confidence = min(1.0, len(matches) / 10.0)
            return _build_evidence(
                image.image_name,
                self.method_name,
                self.category,
                self.evidence_type,
                suspicious=confidence >= context.threshold,
                confidence=confidence,
                summary=f"Copy-move detector found {len(matches)} suspicious block matches.",
                artifacts={"mask": mask},
                metadata={"match_count": len(matches), "cmd_block_size": block_size},
            )

        with ThreadPoolExecutor() as executor:
            return list(executor.map(_process, images))


class URNMethod(DetectionMethod):
    category = "segmentation"
    evidence_type = "mask"

    def __init__(self, method_name: str, weight_path: str) -> None:
        self.method_name = method_name
        self.weight_path = weight_path
        self._model = None
        self._hyper_params = None

    def _ensure_model(self) -> tuple[object, object]:
        if self._model is None or self._hyper_params is None:
            urn_dir = Path(__file__).resolve().parent.parent / "method" / "urn"
            if str(urn_dir) not in sys.path:
                sys.path.insert(0, str(urn_dir))
            from infer import urn_initial_model

            self._model, self._hyper_params = urn_initial_model(self.weight_path)
        return self._model, self._hyper_params

    def run_batch(
        self,
        images: Sequence[ImageInput],
        context: DetectionContext,
    ) -> list[DetectionEvidence]:
        if not images:
            return []
        try:
            model, hyper_params = self._ensure_model()
            urn_dir = Path(__file__).resolve().parent.parent / "method" / "urn"
            if str(urn_dir) not in sys.path:
                sys.path.insert(0, str(urn_dir))
            from infer import urn_infer

            raw_results = urn_infer(
                [str(image.image_path) for image in images],
                model,
                hyper_params,
                float(context.parameters.get("urn_k", 0.3)),
            )
            parsed_results = self._normalize_results(raw_results, len(images))
        except Exception as exc:
            return [
                _build_failed_evidence(
                    image.image_name,
                    self.method_name,
                    self.category,
                    self.evidence_type,
                    f"{self.method_name} detector unavailable: {exc}",
                    artifacts={"mask": np.zeros((2, 2), dtype=np.float32)},
                    metadata={"weight_path": self.weight_path},
                )
                for image in images
            ]

        evidences: list[DetectionEvidence] = []
        for image, (mask_raw, probability_raw) in zip(images, parsed_results):
            mask = _ensure_mask(mask_raw)
            probability = _normalize_probability(probability_raw)
            evidences.append(
                _build_evidence(
                    image.image_name,
                    self.method_name,
                    self.category,
                    self.evidence_type,
                    suspicious=probability >= context.threshold,
                    confidence=probability,
                    summary=f"{self.method_name} detector probability: {probability:.3f}",
                    artifacts={"mask": mask},
                    metadata={"weight_path": self.weight_path},
                )
            )
        return evidences

    @staticmethod
    def _normalize_results(raw_results: object, expected_count: int) -> list[tuple[object, object]]:
        if isinstance(raw_results, list):
            if len(raw_results) == expected_count and all(
                isinstance(item, tuple) and len(item) == 2 for item in raw_results
            ):
                return [(item[0], item[1]) for item in raw_results]
            if len(raw_results) == expected_count * 2:
                pairs = []
                for index in range(expected_count):
                    pairs.append((raw_results[2 * index], raw_results[2 * index + 1]))
                return pairs
        raise ValueError("URN detector returned an unexpected result structure")


class LLMMethod(DetectionMethod):
    method_name = "llm"
    category = "language"
    evidence_type = "text"

    def run_batch(
        self,
        images: Sequence[ImageInput],
        context: DetectionContext,
    ) -> list[DetectionEvidence]:
        if not bool(context.parameters.get("if_use_llm", False)):
            return [
                _build_evidence(
                    image.image_name,
                    self.method_name,
                    self.category,
                    self.evidence_type,
                    suspicious=False,
                    confidence=0.0,
                    summary="LLM detector disabled by request parameters.",
                    artifacts={"text": DEFAULT_LLM_TEXT, "mask": None},
                )
                for image in images
            ]

        return [self._run_single(image) for image in images]

    def _run_single(self, image: ImageInput) -> DetectionEvidence:
        llm_dir = Path(__file__).resolve().parent.parent / "method" / "llm"
        weight_path = llm_dir / "weight" / "fakeshield-v1-22b"
        if not weight_path.exists():
            return _build_evidence(
                image.image_name,
                self.method_name,
                self.category,
                self.evidence_type,
                suspicious=False,
                confidence=0.0,
                summary="LLM detector weights not found; reserved interface returned a placeholder result.",
                artifacts={"text": DEFAULT_LLM_TEXT, "mask": None},
            )

        dte_output = llm_dir / "playground" / "DTE-FDM_output.jsonl"
        mflm_output = llm_dir / "playground" / "MFLM_output"
        if mflm_output.exists():
            shutil.rmtree(mflm_output)
        mflm_output.mkdir(parents=True, exist_ok=True)

        venv_python = os.getenv("LLM_VENV_PYTHON", "")
        venv_pip = os.getenv("LLM_VENV_PIP", "")
        if not venv_python or not venv_pip:
            return _build_evidence(
                image.image_name,
                self.method_name,
                self.category,
                self.evidence_type,
                suspicious=False,
                confidence=0.0,
                summary="LLM virtual environment is not configured; reserved interface returned a placeholder result.",
                artifacts={"text": DEFAULT_LLM_TEXT, "mask": None},
            )

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = env.get("CUDA_VISIBLE_DEVICES", "0")

        try:
            subprocess.check_call(
                [venv_pip, "install", "-q", "transformers==4.37.2"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.check_call(
                [
                    venv_python,
                    "-m",
                    "llava.serve.cli",
                    "--model-path",
                    str(weight_path / "DTE-FDM"),
                    "--DTG-path",
                    str(weight_path / "DTG.pth"),
                    "--image-path",
                    str(image.image_path),
                    "--output-path",
                    str(dte_output),
                ],
                cwd=str(llm_dir),
                env=env,
            )

            subprocess.check_call(
                [venv_pip, "install", "-q", "transformers==4.28.0"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.check_call(
                [
                    venv_python,
                    str(llm_dir / "MFLM" / "cli_demo.py"),
                    "--version",
                    str(weight_path / "MFLM"),
                    "--DTE-FDM-output",
                    str(dte_output),
                    "--MFLM-output",
                    str(mflm_output),
                ],
                cwd=str(llm_dir),
                env=env,
            )
        except Exception as exc:
            return _build_evidence(
                image.image_name,
                self.method_name,
                self.category,
                self.evidence_type,
                suspicious=False,
                confidence=0.0,
                summary=f"LLM detector execution failed: {exc}",
                artifacts={"text": DEFAULT_LLM_TEXT, "mask": None},
            )

        text_output = DEFAULT_LLM_TEXT
        if dte_output.exists():
            with dte_output.open("r", encoding="utf-8") as handle:
                for line in handle:
                    text_output = json.loads(line).get("outputs", DEFAULT_LLM_TEXT)

        mask = None
        for pattern in ("*.jpg", "*.jpeg", "*.png"):
            for image_path in glob.glob(str(mflm_output / pattern)):
                with Image.open(image_path) as generated_image:
                    mask = np.asarray(generated_image)
                    break
            if mask is not None:
                break

        return _build_evidence(
            image.image_name,
            self.method_name,
            self.category,
            self.evidence_type,
            suspicious=False,
            confidence=0.0,
            summary="LLM detector completed.",
            artifacts={"text": text_output or DEFAULT_LLM_TEXT, "mask": mask},
        )


def build_image_methods():
    return [
        LLMMethod(),
        ELAMethod(),
        ExifMethod(),
        CopyMoveMethod(),
        URNMethod("splicing", "weight/Coarse_v2.pkl"),
        URNMethod("blurring", "weight/blurring.pkl"),
        URNMethod("bruteforce", "weight/brute_force.pkl"),
        URNMethod("contrast", "weight/contrast.pkl"),
        URNMethod("inpainting", "weight/inpainting.pkl"),
    ]
