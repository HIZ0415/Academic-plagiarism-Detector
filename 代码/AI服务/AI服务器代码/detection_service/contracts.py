from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np


BACKEND_REQUEST_SCHEMA_VERSION = "backend-ai-request-v1"
IMAGE_RESULT_SCHEMA_VERSION = "image-detection-v1"
STANDARD_EVIDENCE_SCHEMA_VERSION = "standard-evidence-v1"


def _serialize_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    return value


@dataclass(slots=True)
class DetectionEvidence:
    evidence_id: str
    method: str
    category: str
    evidence_type: str
    suspicious: bool
    confidence: float
    summary: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": STANDARD_EVIDENCE_SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "method": self.method,
            "category": self.category,
            "evidence_type": self.evidence_type,
            "suspicious": bool(self.suspicious),
            "confidence": float(self.confidence),
            "summary": self.summary,
            "artifacts": _serialize_value(self.artifacts),
            "metadata": _serialize_value(self.metadata),
        }


@dataclass(slots=True)
class ImageInput:
    image_name: str
    image_path: Path
    image_id: Optional[int] = None


@dataclass(slots=True)
class DetectionContext:
    task_type: str
    parameters: Dict[str, Any]
    model_version: str
    batch_id: Optional[str] = None
    model_profile: Optional[str] = None

    @property
    def threshold(self) -> float:
        return float(self.parameters.get("threshold", 0.5))


@dataclass(slots=True)
class DetectionRequest:
    schema_version: str
    task_type: str
    batch_id: Optional[str]
    parameters: Dict[str, Any]
    image_names: list[str] = field(default_factory=list)
    images_zip_base64: Optional[str] = None
    payload_base64: Optional[str] = None


@dataclass(slots=True)
class StandardImageResult:
    image_name: str
    image_id: Optional[int]
    model_version: str
    overall_is_fake: bool
    overall_confidence: float
    llm_text: str
    llm_img: Any
    ela: Any
    exif_flags: Dict[str, bool]
    sub_method_results: list[Dict[str, Any]]
    evidences: list[DetectionEvidence]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": IMAGE_RESULT_SCHEMA_VERSION,
            "task_type": "image",
            "model_version": self.model_version,
            "image_name": self.image_name,
            "image_id": self.image_id,
            "overall_is_fake": bool(self.overall_is_fake),
            "overall_confidence": float(self.overall_confidence),
            "llm_text": self.llm_text,
            "llm_img": _serialize_value(self.llm_img),
            "ela": _serialize_value(self.ela),
            "exif_flags": _serialize_value(self.exif_flags),
            "sub_method_results": _serialize_value(self.sub_method_results),
            "evidences": [evidence.to_dict() for evidence in self.evidences],
        }


@dataclass(slots=True)
class DetectionResponse:
    schema_version: str
    task_type: str
    model_version: str
    batch_id: Optional[str]
    results: list[StandardImageResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_type": self.task_type,
            "model_version": self.model_version,
            "batch_id": self.batch_id,
            "results": [result.to_dict() for result in self.results],
        }
