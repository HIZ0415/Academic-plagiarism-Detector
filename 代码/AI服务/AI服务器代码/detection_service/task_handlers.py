from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .contracts import (
    DetectionContext,
    DetectionEvidence,
    DetectionResponse,
    ImageInput,
    StandardTextResult,
    TEXT_RESULT_SCHEMA_VERSION,
)
from .image_detector import ImageDetector
from .model_registry import DetectionModelRegistry
from .service_errors import TaskNotImplementedError


class TaskHandler:
    task_type: str

    def detect(self, request, context: DetectionContext, extracted_inputs: Any = None):
        raise NotImplementedError


class ImageTaskHandler(TaskHandler):
    task_type = "image"

    def __init__(
        self,
        detector: ImageDetector | None = None,
        model_registry: DetectionModelRegistry | None = None,
    ) -> None:
        self.detector = detector
        self.model_registry = model_registry

    def detect(self, request, context: DetectionContext, extracted_inputs: Any = None):
        if extracted_inputs is None:
            raise ValueError("image task requires extracted image inputs")
        detector = self.detector
        if detector is None:
            if self.model_registry is None:
                detector = ImageDetector()
            else:
                detector = self.model_registry.build_image_detector(context.model_profile)
        return detector.detect(extracted_inputs, context)

    @property
    def method_names(self) -> list[str]:
        if self.detector is not None:
            return self.detector.method_names
        if self.model_registry is not None:
            detector = self.model_registry.build_image_detector(self.model_registry.default_image_profile)
            return detector.method_names
        return ImageDetector().method_names


class PaperTaskHandler(TaskHandler):
    task_type = "paper"

    def detect(self, request, context: DetectionContext, extracted_inputs: Any = None):
        payload = extracted_inputs or {}
        text = str(payload.get("text") or "")
        paragraphs = payload.get("paragraphs") if isinstance(payload.get("paragraphs"), list) else []
        source_name = str(payload.get("source_name") or context.parameters.get("source_name") or "paper")
        paragraph_risks = []
        scores = []

        for fallback_index, paragraph in enumerate(paragraphs, start=1):
            if not isinstance(paragraph, dict):
                continue
            paragraph_text = str(paragraph.get("text") or "").strip()
            if not paragraph_text:
                continue
            paragraph_index = _safe_int(paragraph.get("index"), fallback_index)
            score = _paper_paragraph_risk_score(source_name, paragraph_index, paragraph_text)
            scores.append(score)
            paragraph_risks.append(
                {
                    "index": paragraph_index,
                    "paragraph_id": f"p{paragraph_index}",
                    "risk_score": score,
                    "ai_generated_probability": score,
                    "risk_level": _risk_level(score),
                    "excerpt": paragraph_text[:180],
                    "summary": _summarize_text(paragraph_text, max_chars=120),
                    "basic_explanation": _paper_paragraph_explanation(score, paragraph_text),
                    "char_start": paragraph.get("char_start"),
                    "char_end": paragraph.get("char_end"),
                    "word_count": paragraph.get("word_count"),
                }
            )

        if not scores and text:
            score = _stable_score(f"paper:{source_name}:{text[:2000]}", 0.18, 0.86)
            scores.append(score)

        overall = _aggregate_risk(scores)
        high_count = sum(1 for item in paragraph_risks if item["risk_level"] == "high")
        medium_count = sum(1 for item in paragraph_risks if item["risk_level"] == "medium")
        paper_summary = {
            "source_name": source_name,
            "text_length": len(text),
            "paragraph_count": len(paragraphs),
            "analyzed_paragraph_count": len(paragraph_risks),
            "overall_risk_score": overall,
            "ai_contribution_ratio": overall,
            "risk_level": _risk_level(overall),
            "high_risk_paragraph_count": high_count,
            "medium_risk_paragraph_count": medium_count,
            "summary_text": _build_paper_summary_text(
                text=text,
                overall=overall,
                high_count=high_count,
                medium_count=medium_count,
                analyzed_count=len(paragraph_risks),
            ),
        }
        basic_explanation = _build_paper_basic_explanation(
            overall=overall,
            high_count=high_count,
            medium_count=medium_count,
            analyzed_count=len(paragraph_risks),
        )
        summary = paper_summary["summary_text"]
        evidence = DetectionEvidence(
            evidence_id=f"{source_name}:paper_text",
            method="paper_text_baseline",
            category="text",
            evidence_type="score",
            suspicious=overall >= context.threshold,
            confidence=overall,
            summary=summary,
            artifacts={
                "paper_summary": paper_summary,
                "paragraph_risks": paragraph_risks,
                "basic_explanation": basic_explanation,
            },
            metadata={
                "preprocessing_schema_version": payload.get("schema_version"),
                "paragraph_count": len(paragraphs),
                "analyzed_paragraph_count": len(paragraph_risks),
            },
        )
        return DetectionResponse(
            schema_version=TEXT_RESULT_SCHEMA_VERSION,
            task_type="paper",
            model_version=context.model_version,
            batch_id=context.batch_id,
            results=[
                StandardTextResult(
                    task_type="paper",
                    source_name=source_name,
                    model_version=context.model_version,
                    overall_is_fake=overall >= context.threshold,
                    overall_confidence=overall,
                    summary=summary,
                    text_length=len(text),
                    evidences=[evidence],
                    details={
                        "paper_summary": paper_summary,
                        "paragraph_risks": paragraph_risks,
                        "basic_explanation": basic_explanation,
                        "paragraphs": paragraph_risks,
                        "paragraph_count": len(paragraphs),
                        "risk_level": _risk_level(overall),
                    },
                )
            ],
        )


class ReviewTaskHandler(TaskHandler):
    task_type = "review"

    def detect(self, request, context: DetectionContext, extracted_inputs: Any = None):
        payload = extracted_inputs or {}
        text = str(payload.get("text") or "")
        source_name = str(payload.get("source_name") or context.parameters.get("source_name") or "review")
        line_count = _safe_int(payload.get("line_count"), len([line for line in text.splitlines() if line.strip()]))
        ai_tendency = _review_ai_tendency_score(source_name, text) if text else 0.0
        template_tendency = _review_template_tendency_score(source_name, text) if text else 0.0
        overall = round(max(ai_tendency, template_tendency), 4)
        suspicious_segments = _build_review_suspicious_segments(
            text=text,
            ai_tendency=ai_tendency,
            template_tendency=template_tendency,
            threshold=context.threshold,
        )
        review_summary = {
            "source_name": source_name,
            "text_length": len(text),
            "line_count": line_count,
            "overall_risk_score": overall,
            "risk_level": _risk_level(overall),
            "ai_tendency": {
                "score": ai_tendency,
                "risk_level": _risk_level(ai_tendency),
                "suspicious": ai_tendency >= context.threshold,
            },
            "template_tendency": {
                "score": template_tendency,
                "risk_level": _risk_level(template_tendency),
                "suspicious": template_tendency >= context.threshold,
            },
            "summary_text": _build_review_summary_text(
                overall=overall,
                ai_tendency=ai_tendency,
                template_tendency=template_tendency,
                segment_count=len(suspicious_segments),
            ),
        }
        basic_explanation = _build_review_basic_explanation(
            ai_tendency=ai_tendency,
            template_tendency=template_tendency,
            segment_count=len(suspicious_segments),
        )
        summary = review_summary["summary_text"]
        evidence = DetectionEvidence(
            evidence_id=f"{source_name}:review_text",
            method="review_text_baseline",
            category="text",
            evidence_type="score",
            suspicious=overall >= context.threshold,
            confidence=overall,
            summary=summary,
            artifacts={
                "review_summary": review_summary,
                "suspicious_segments": suspicious_segments,
                "basic_explanation": basic_explanation,
            },
            metadata={
                "preprocessing_schema_version": payload.get("schema_version"),
                "line_count": line_count,
                "ai_tendency_score": ai_tendency,
                "template_tendency_score": template_tendency,
            },
        )
        return DetectionResponse(
            schema_version=TEXT_RESULT_SCHEMA_VERSION,
            task_type="review",
            model_version=context.model_version,
            batch_id=context.batch_id,
            results=[
                StandardTextResult(
                    task_type="review",
                    source_name=source_name,
                    model_version=context.model_version,
                    overall_is_fake=overall >= context.threshold,
                    overall_confidence=overall,
                    summary=summary,
                    text_length=len(text),
                    evidences=[evidence],
                    details={
                        "review_summary": review_summary,
                        "ai_tendency": review_summary["ai_tendency"],
                        "template_tendency": review_summary["template_tendency"],
                        "suspicious_segments": suspicious_segments,
                        "basic_explanation": basic_explanation,
                        "issues": suspicious_segments,
                        "line_count": line_count,
                        "risk_level": _risk_level(overall),
                    },
                )
            ],
        )


@dataclass(slots=True)
class UnimplementedTaskHandler(TaskHandler):
    task_type: str

    def detect(self, request, context: DetectionContext, extracted_inputs: Any = None):
        raise TaskNotImplementedError(
            f"task_type '{self.task_type}' is reserved but not implemented yet"
        )


def _stable_score(seed: str, lower: float, upper: float) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    ratio = int(digest[:8], 16) / 0xFFFFFFFF
    return round(lower + ratio * (upper - lower), 4)


def _paper_paragraph_risk_score(source_name: str, paragraph_index: int, paragraph_text: str) -> float:
    lexical_score = 0.0
    normalized = " ".join(paragraph_text.lower().split())
    if len(normalized) > 900:
        lexical_score += 0.04
    if any(marker in normalized for marker in ("in conclusion", "overall,", "it is worth noting", "综上", "总之")):
        lexical_score += 0.035
    if normalized.count(";") + normalized.count("；") >= 3:
        lexical_score += 0.025
    baseline = _stable_score(f"paper:{source_name}:{paragraph_index}:{normalized[:500]}", 0.18, 0.82)
    return round(min(0.98, baseline + lexical_score), 4)


def _aggregate_risk(scores: list[float]) -> float:
    if not scores:
        return 0.0
    top_scores = sorted(scores, reverse=True)[: min(5, len(scores))]
    top_average = sum(top_scores) / len(top_scores)
    full_average = sum(scores) / len(scores)
    return round(max(top_scores[0], top_average * 0.75 + full_average * 0.25), 4)


def _risk_level(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _summarize_text(text: str, *, max_chars: int) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def _paper_paragraph_explanation(score: float, paragraph_text: str) -> str:
    risk = _risk_level(score)
    length = len(paragraph_text)
    if risk == "high":
        return (
            "该段落的基线风险较高，建议结合原文语境复核表达是否过于模板化、"
            "论证是否缺少具体实验或引用支撑。"
        )
    if risk == "medium":
        return (
            "该段落存在一定 AI 生成倾向，建议重点查看术语密度、句式重复和上下文衔接。"
        )
    if length < 80:
        return "该段落较短，当前基线仅给出低风险提示，仍建议结合上下文判断。"
    return "该段落当前未表现出明显高风险特征，保留为低风险参考结论。"


def _build_paper_summary_text(
    *,
    text: str,
    overall: float,
    high_count: int,
    medium_count: int,
    analyzed_count: int,
) -> str:
    leading = _summarize_text(text, max_chars=140)
    return (
        f"已分析 {analyzed_count} 个段落，整体风险为 {_risk_level(overall)} "
        f"({overall:.3f})，高风险段落 {high_count} 个，中风险段落 {medium_count} 个。"
        f"全文摘要：{leading}"
    )


def _build_paper_basic_explanation(
    *,
    overall: float,
    high_count: int,
    medium_count: int,
    analyzed_count: int,
) -> list[str]:
    if analyzed_count == 0:
        return ["后端已传入论文文本，但未提供可分析的有效段落。"]
    explanations = [
        "AI 侧已接收后端标准化后的论文全文文本和段落切分数据。",
        "当前结果由轻量基线规则生成，用于打通论文检测协议和结果展示结构。",
        "段落级风险分值范围为 0 到 1，数值越高表示越需要人工复核。",
    ]
    if high_count:
        explanations.append(f"存在 {high_count} 个高风险段落，应优先进入人工复核或报告重点展示。")
    elif medium_count:
        explanations.append(f"存在 {medium_count} 个中风险段落，建议在综合报告中保留提示。")
    else:
        explanations.append("未发现高风险段落，整体结论仍应作为辅助判断而非最终裁决。")
    explanations.append(f"全文聚合风险为 {overall:.3f}，由段落风险分布汇总得到。")
    return explanations


def _review_ai_tendency_score(source_name: str, text: str) -> float:
    normalized = " ".join(text.lower().split())
    score = _stable_score(f"review:ai:{source_name}:{normalized[:1600]}", 0.16, 0.76)
    if len(normalized) > 900:
        score += 0.035
    if any(marker in normalized for marker in ("overall", "in conclusion", "it is recommended", "总体而言", "综上")):
        score += 0.04
    if _sentence_length_variance(normalized) < 35.0 and len(normalized) > 220:
        score += 0.035
    return round(min(0.98, score), 4)


def _review_template_tendency_score(source_name: str, text: str) -> float:
    normalized = " ".join(text.lower().split())
    score = _stable_score(f"review:template:{source_name}:{normalized[:1600]}", 0.12, 0.72)
    template_markers = (
        "the paper is well written",
        "minor revision",
        "major revision",
        "the authors should",
        "i recommend",
        "语言流畅",
        "结构清晰",
        "建议录用",
        "需要修改",
    )
    marker_hits = sum(1 for marker in template_markers if marker in normalized)
    score += min(0.18, marker_hits * 0.045)
    repeated_ratio = _repeated_sentence_ratio(text)
    if repeated_ratio >= 0.25:
        score += min(0.16, repeated_ratio)
    return round(min(0.98, score), 4)


def _build_review_suspicious_segments(
    *,
    text: str,
    ai_tendency: float,
    template_tendency: float,
    threshold: float,
) -> list[dict[str, Any]]:
    sentences = _split_review_sentences(text)
    if not sentences:
        return []
    selected: list[dict[str, Any]] = []
    for index, sentence in enumerate(sentences[:12], start=1):
        sentence_score = _stable_score(f"review:segment:{index}:{sentence.lower()[:400]}", 0.1, 0.85)
        issue_type = "ai_tendency" if ai_tendency >= template_tendency else "template_tendency"
        if _looks_template_like(sentence):
            issue_type = "template_tendency"
            sentence_score = max(sentence_score, template_tendency)
        elif ai_tendency >= threshold:
            sentence_score = max(sentence_score, ai_tendency)

        if sentence_score < threshold and len(selected) >= 1:
            continue
        if sentence_score < 0.35:
            continue
        selected.append(
            {
                "segment_index": index,
                "issue_type": issue_type,
                "risk_score": round(min(0.98, sentence_score), 4),
                "risk_level": _risk_level(sentence_score),
                "excerpt": _summarize_text(sentence, max_chars=180),
                "basic_explanation": _review_segment_explanation(issue_type, sentence_score),
            }
        )
        if len(selected) >= 5:
            break
    return selected


def _split_review_sentences(text: str) -> list[str]:
    normalized = " ".join((text or "").split())
    if not normalized:
        return []
    separators = ".!?。！？；;"
    sentences: list[str] = []
    current = ""
    for char in normalized:
        current += char
        if char in separators:
            piece = current.strip()
            if piece:
                sentences.append(piece)
            current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences


def _repeated_sentence_ratio(text: str) -> float:
    sentences = [_summarize_text(sentence.lower(), max_chars=80) for sentence in _split_review_sentences(text)]
    if len(sentences) < 3:
        return 0.0
    unique_count = len(set(sentences))
    return round((len(sentences) - unique_count) / len(sentences), 4)


def _sentence_length_variance(text: str) -> float:
    sentences = _split_review_sentences(text)
    if len(sentences) < 2:
        return 999.0
    lengths = [len(sentence) for sentence in sentences]
    mean = sum(lengths) / len(lengths)
    return sum((length - mean) ** 2 for length in lengths) / len(lengths)


def _looks_template_like(sentence: str) -> bool:
    normalized = sentence.lower()
    return any(
        marker in normalized
        for marker in (
            "the paper is well written",
            "the authors should",
            "minor revision",
            "major revision",
            "i recommend",
            "结构清晰",
            "语言流畅",
            "建议录用",
            "需要修改",
        )
    )


def _review_segment_explanation(issue_type: str, score: float) -> str:
    if issue_type == "template_tendency":
        return "该片段包含常见评审模板表达或重复句式，建议结合具体审稿语境复核。"
    if score >= 0.7:
        return "该片段 AI 倾向较高，建议检查是否缺少针对论文具体内容的细节反馈。"
    return "该片段存在一定 AI 倾向，建议作为辅助风险提示查看。"


def _build_review_summary_text(
    *,
    overall: float,
    ai_tendency: float,
    template_tendency: float,
    segment_count: int,
) -> str:
    dominant = "AI 生成倾向" if ai_tendency >= template_tendency else "模板化倾向"
    return (
        f"Review 整体风险为 {_risk_level(overall)} ({overall:.3f})，"
        f"主要风险来源为{dominant}；AI 倾向 {ai_tendency:.3f}，"
        f"模板化倾向 {template_tendency:.3f}，可疑片段 {segment_count} 个。"
    )


def _build_review_basic_explanation(
    *,
    ai_tendency: float,
    template_tendency: float,
    segment_count: int,
) -> list[str]:
    explanations = [
        "AI 侧已接收后端标准化后的 Review 文本。",
        "当前结果由轻量基线规则生成，用于打通 Review 检测协议和结果展示结构。",
        "AI 倾向用于提示文本是否可能由生成式模型产出；模板化倾向用于提示是否存在固定句式或重复评审话术。",
    ]
    if ai_tendency >= template_tendency:
        explanations.append(f"本次主要风险为 AI 生成倾向，分值为 {ai_tendency:.3f}。")
    else:
        explanations.append(f"本次主要风险为模板化倾向，分值为 {template_tendency:.3f}。")
    if segment_count:
        explanations.append(f"已抽取 {segment_count} 个可疑片段供前端高亮或报告展示。")
    else:
        explanations.append("未抽取到明显可疑片段，整体结论仍应作为辅助判断。")
    return explanations
