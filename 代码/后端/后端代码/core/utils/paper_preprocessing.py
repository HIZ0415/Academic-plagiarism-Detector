from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any


BACKEND_AI_REQUEST_SCHEMA_VERSION = "backend-ai-request-v1"
PREPROCESSING_SCHEMA_VERSION = "paper-preprocess-v1"


@dataclass(frozen=True, slots=True)
class PaperParagraph:
    index: int
    text: str
    char_start: int
    char_end: int
    word_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "word_count": self.word_count,
        }


@dataclass(frozen=True, slots=True)
class PaperPreprocessingResult:
    raw_text: str
    cleaned_text: str
    paragraphs: list[PaperParagraph]
    ai_payload: dict[str, Any]


def preprocess_pdf_paper(raw_bytes: bytes, *, source_name: str) -> PaperPreprocessingResult:
    raw_text = extract_text_from_pdf_bytes(raw_bytes, source_name=source_name)
    cleaned_text = clean_paper_text(raw_text)
    paragraphs = split_paper_paragraphs(cleaned_text)

    if not paragraphs:
        raise ValueError("PDF text is empty after preprocessing")

    return PaperPreprocessingResult(
        raw_text=raw_text,
        cleaned_text=cleaned_text,
        paragraphs=paragraphs,
        ai_payload=build_paper_ai_payload(source_name, cleaned_text, paragraphs),
    )


def extract_text_from_pdf_bytes(raw_bytes: bytes, *, source_name: str) -> str:
    try:
        import fitz  # type: ignore

        document = fitz.open(stream=raw_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"failed to open PDF '{source_name}'") from exc

    chunks: list[str] = []
    with document:
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            try:
                chunks.append(page.get_text("text"))
            finally:
                del page

    text = "\n".join(chunks).strip()
    if not text:
        raise ValueError(f"failed to extract text from PDF '{source_name}'")
    return text


def clean_paper_text(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", normalized)
    normalized = re.sub(r"(?<=\w)-\n(?=\w)", "", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    blocks = [block.strip() for block in re.split(r"\n{2,}", normalized) if block.strip()]
    cleaned_blocks = []
    for block in blocks:
        block = re.sub(r"(?<![.!?;:\u3002\uff01\uff1f\uff1b\uff1a])\n(?!\s*[-*0-9])", " ", block)
        block = re.sub(r"\s+", " ", block).strip()
        if block:
            cleaned_blocks.append(block)

    return "\n\n".join(cleaned_blocks)


def split_paper_paragraphs(
    cleaned_text: str,
    *,
    min_chars: int = 40,
    max_chars: int = 1800,
) -> list[PaperParagraph]:
    blocks = [block.strip() for block in re.split(r"\n{2,}", cleaned_text or "") if block.strip()]
    normalized_blocks = _merge_short_blocks(blocks, min_chars=min_chars)

    paragraphs: list[PaperParagraph] = []
    search_from = 0
    for block in normalized_blocks:
        for piece in _split_long_block(block, max_chars=max_chars):
            start = cleaned_text.find(piece, search_from)
            if start < 0:
                start = search_from
            end = start + len(piece)
            search_from = end
            paragraphs.append(
                PaperParagraph(
                    index=len(paragraphs) + 1,
                    text=piece,
                    char_start=start,
                    char_end=end,
                    word_count=len(re.findall(r"\S+", piece)),
                )
            )

    return paragraphs


def build_paper_ai_payload(
    source_name: str,
    cleaned_text: str,
    paragraphs: list[PaperParagraph],
) -> dict[str, Any]:
    payload = {
        "schema_version": PREPROCESSING_SCHEMA_VERSION,
        "source_name": source_name,
        "text": cleaned_text,
        "paragraphs": [paragraph.as_dict() for paragraph in paragraphs],
    }

    return {
        "schema_version": BACKEND_AI_REQUEST_SCHEMA_VERSION,
        "task_type": "paper",
        "batch_id": None,
        "parameters": {
            "preprocessing_schema_version": PREPROCESSING_SCHEMA_VERSION,
            "source_name": source_name,
            "paragraph_count": len(paragraphs),
        },
        "payload_base64": base64.b64encode(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).decode("ascii"),
    }


def _merge_short_blocks(blocks: list[str], *, min_chars: int) -> list[str]:
    merged: list[str] = []
    pending = ""

    for block in blocks:
        if not pending:
            pending = block
        elif len(pending) < min_chars:
            pending = f"{pending} {block}"
        else:
            merged.append(pending)
            pending = block

    if pending:
        merged.append(pending)

    return merged


def _split_long_block(block: str, *, max_chars: int) -> list[str]:
    if len(block) <= max_chars:
        return [block]

    sentences = re.split(r"(?<=[.!?\u3002\uff01\uff1f])\s+", block)
    pieces: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if current and len(current) + len(sentence) + 1 > max_chars:
            pieces.append(current)
            current = sentence
        else:
            current = sentence if not current else f"{current} {sentence}"

    if current:
        pieces.append(current)

    if not pieces:
        return [block[i : i + max_chars] for i in range(0, len(block), max_chars)]

    return pieces
