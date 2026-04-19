from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


IMAGE_RESULT_SCHEMA_VERSION = "image-detection-v1"

DEFAULT_SUB_METHODS = (
    "splicing",
    "blurring",
    "bruteforce",
    "contrast",
    "inpainting",
)


class AIResultFormatError(ValueError):
    """Raised when the AI service result cannot be converted to the internal schema."""


def is_ai_batch_complete(raw_results: Any, expected_count: int) -> bool:
    """Return whether raw AI output contains exactly the expected number of image results."""
    if raw_results is None:
        return False

    try:
        if isinstance(raw_results, dict):
            return len(raw_results.get("results", [])) == expected_count
        return len(raw_results[1][1]) == expected_count
    except (IndexError, KeyError, TypeError):
        return False


def normalize_ai_batch_results(raw_results: Any, expected_count: int | None = None) -> List[Dict[str, Any]]:
    """
    Convert AI service output to the stable internal image result schema.

    Supported inputs:
    - New dict schema: {"schema_version": "image-detection-v1", "results": [...]}
    - Legacy tuple/list schema currently emitted by trigger.py/PipelineSingleImage.
    """
    if isinstance(raw_results, dict):
        normalized = [_normalize_new_schema_result(item) for item in raw_results.get("results", [])]
    else:
        result_count = _legacy_result_count(raw_results)
        normalized = [_normalize_legacy_single_result(raw_results, idx) for idx in range(result_count)]

    if expected_count is not None and len(normalized) != expected_count:
        raise AIResultFormatError(
            f"AI result count mismatch: expected {expected_count}, got {len(normalized)}"
        )
    return normalized


def _normalize_new_schema_result(item: Dict[str, Any]) -> Dict[str, Any]:
    sub_method_results = []
    for sub in item.get("sub_method_results", []):
        method = sub.get("method")
        if not method:
            raise AIResultFormatError("sub_method_results item missing method")
        sub_method_results.append(
            {
                "method": method,
                "prob": float(sub.get("prob", sub.get("probability", 0.0))),
                "mask": _to_serializable_array(sub.get("mask", [])),
            }
        )

    exif_flags = item.get("exif_flags") or {}
    return {
        "schema_version": item.get("schema_version", IMAGE_RESULT_SCHEMA_VERSION),
        "task_type": item.get("task_type", "image"),
        "model_version": item.get("model_version"),
        "image_id": item.get("image_id"),
        "image_name": item.get("image_name"),
        "llm_text": item.get("llm_text") or "无",
        "llm_img": _to_serializable_array(item.get("llm_img")),
        "ela": _to_serializable_array(item.get("ela", item.get("ela_image", []))),
        "overall_is_fake": bool(item.get("overall_is_fake", False)),
        "overall_confidence": float(item.get("overall_confidence", 0.0)),
        "exif_flags": {
            "photoshop": bool(exif_flags.get("photoshop", False)),
            "time_modified": bool(exif_flags.get("time_modified", False)),
        },
        "sub_method_results": sub_method_results,
    }


def _legacy_result_count(raw_results: Any) -> int:
    try:
        return len(raw_results[1][1])
    except (IndexError, TypeError) as exc:
        raise AIResultFormatError("legacy AI result missing ELA batch output") from exc


def _normalize_legacy_single_result(raw_results: Any, idx: int) -> Dict[str, Any]:
    try:
        llm_entry = raw_results[0][1][idx]
        llm_payload = llm_entry[1]
        llm_text = llm_payload[0] if llm_payload is not None else "无"
        llm_img = llm_payload[1] if llm_payload is not None else None

        ela_np = raw_results[1][1][idx][1]
        exif_raw = raw_results[2][1][idx][1][1]
        sub_raw = _extract_legacy_sub_methods(raw_results, idx)
    except (IndexError, TypeError) as exc:
        raise AIResultFormatError(f"legacy AI result missing fields for index {idx}") from exc

    exif_flags = {"photoshop": False, "time_modified": False}
    if exif_raw:
        exif_flags["photoshop"] = "使用了Photoshop进行修改" in exif_raw
        exif_flags["time_modified"] = "修改了拍摄或制作时间" in exif_raw

    threshold = 0.5
    sub_method_results = []
    probabilities = []
    for method_key, (mask_np, prob) in sub_raw:
        prob_float = float(prob)
        probabilities.append(prob_float)
        sub_method_results.append(
            {
                "method": method_key,
                "prob": prob_float,
                "mask": np.squeeze(mask_np).tolist(),
            }
        )

    return {
        "schema_version": IMAGE_RESULT_SCHEMA_VERSION,
        "task_type": "image",
        "model_version": None,
        "image_id": None,
        "image_name": None,
        "llm_text": llm_text,
        "llm_img": _to_serializable_array(llm_img),
        "ela": _to_serializable_array(ela_np),
        "overall_is_fake": any(prob > threshold for prob in probabilities) or exif_raw is not None,
        "overall_confidence": 1.0 if exif_raw is not None else max(probabilities, default=0.0),
        "exif_flags": exif_flags,
        "sub_method_results": sub_method_results,
    }


def _extract_legacy_sub_methods(raw_results: Any, idx: int) -> List[tuple[str, Any]]:
    urn_offset = 4
    if len(raw_results[0][1]) == 1:
        return [
            (method, raw_results[urn_offset + offset][1][0][2 * idx: 2 * idx + 2])
            for offset, method in enumerate(DEFAULT_SUB_METHODS)
        ]
    return [
        (method, raw_results[urn_offset + offset][1][2 * idx: 2 * idx + 2])
        for offset, method in enumerate(DEFAULT_SUB_METHODS)
    ]


def _to_serializable_array(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return np.asarray(value).tolist()
