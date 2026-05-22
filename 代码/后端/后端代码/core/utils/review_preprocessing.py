from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any


BACKEND_AI_REQUEST_SCHEMA_VERSION = "backend-ai-request-v1"
PREPROCESSING_SCHEMA_VERSION = "review-preprocess-v1"
TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "latin-1")
# 与测试用例 §6.4-5 对齐：正常 Review 约数百～千余字；超长拒绝（避免 AI/存储压力）
MAX_REVIEW_TEXT_CHARS = 100_000


@dataclass(frozen=True, slots=True)
class ReviewPreprocessingResult:
    raw_text: str
    cleaned_text: str
    encoding: str
    ai_payload: dict[str, Any]


def _ensure_review_text_within_limit(text: str) -> None:
    if len(text) > MAX_REVIEW_TEXT_CHARS:
        raise ValueError(
            f"Review 文本超过最大长度 {MAX_REVIEW_TEXT_CHARS} 字符，请缩短后重试。"
        )


def preprocess_review_text(raw_text: str, *, source_name: str = "review_input.txt") -> ReviewPreprocessingResult:
    _ensure_review_text_within_limit(raw_text)
    cleaned_text = clean_review_text(raw_text)
    if not cleaned_text:
        raise ValueError("Review text is empty after preprocessing")

    return ReviewPreprocessingResult(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        encoding="unicode",
        ai_payload=build_review_ai_payload(source_name, cleaned_text),
    )


def preprocess_review_bytes(raw_bytes: bytes, *, source_name: str) -> ReviewPreprocessingResult:
    raw_text, encoding = decode_review_bytes(raw_bytes)
    _ensure_review_text_within_limit(raw_text)
    cleaned_text = clean_review_text(raw_text)
    if not cleaned_text:
        raise ValueError("Review text is empty after preprocessing")

    return ReviewPreprocessingResult(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        encoding=encoding,
        ai_payload=build_review_ai_payload(source_name, cleaned_text),
    )


def decode_review_bytes(raw_bytes: bytes) -> tuple[str, str]:
    for encoding in TEXT_ENCODINGS:
        try:
            return raw_bytes.decode(encoding).strip(), encoding
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="ignore").strip(), "utf-8-ignore"


def clean_review_text(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.lstrip("\ufeff")
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    blocks = [block.strip() for block in re.split(r"\n{2,}", normalized) if block.strip()]
    cleaned_blocks = []
    for block in blocks:
        block = re.sub(r"\n+", " ", block)
        block = re.sub(r"\s+", " ", block).strip()
        if block:
            cleaned_blocks.append(block)

    return "\n\n".join(cleaned_blocks)


def build_review_ai_payload(source_name: str, cleaned_text: str) -> dict[str, Any]:
    payload = {
        "schema_version": PREPROCESSING_SCHEMA_VERSION,
        "source_name": source_name,
        "text": cleaned_text,
        "text_length": len(cleaned_text),
        "line_count": len([line for line in cleaned_text.splitlines() if line.strip()]),
    }

    return {
        "schema_version": BACKEND_AI_REQUEST_SCHEMA_VERSION,
        "task_type": "review",
        "batch_id": None,
        "parameters": {
            "preprocessing_schema_version": PREPROCESSING_SCHEMA_VERSION,
            "source_name": source_name,
            "text_length": len(cleaned_text),
        },
        "payload_base64": base64.b64encode(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).decode("ascii"),
    }
