"""规则层事实性鉴伪子结论（FR-LWJC-0004/0005），供论文 AIGC 结果并入 API。"""
from __future__ import annotations

import re
from typing import Any


def build_factual_conclusions(
    paragraphs: list[dict[str, Any]],
    paper_text: str = "",
) -> list[dict[str, Any]]:
    """基于启发式规则生成可展示子结论；非大模型推理。"""
    conclusions: list[dict[str, Any]] = []
    text = paper_text or " ".join(
        str(p.get("excerpt") or p.get("text") or "") for p in paragraphs
    )

    doi_missing = not re.search(r"\b10\.\d{4,9}/\S+\b", text, re.I)
    if doi_missing and len(text) > 200:
        conclusions.append({
            "id": "fact-doi",
            "title": "参考文献 DOI 可解析性",
            "severity": "medium",
            "reasons": [
                "正文或参考文献区未检出标准 DOI 格式，著录项可能不完整。",
                "建议核对每条参考文献是否提供可解析 DOI 或权威 URL。",
            ],
        })

    year_refs = re.findall(r"\b(19|20)\d{2}\b", text)
    if len(year_refs) >= 3:
        try:
            years = [int(y) for y in year_refs]
            if max(years) - min(years) > 40:
                conclusions.append({
                    "id": "fact-year-span",
                    "title": "引用年代跨度异常",
                    "severity": "low",
                    "reasons": [
                        f"检出引用年份跨度较大（{min(years)}–{max(years)}），请确认是否与学科惯例一致。",
                    ],
                })
        except ValueError:
            pass

    high_paras = [p for p in paragraphs if p.get("risk_level") == "high"]
    if high_paras:
        idxs = ", ".join(f"P{p.get('index', '?')}" for p in high_paras[:5])
        conclusions.append({
            "id": "fact-aigc-high",
            "title": "高风险段落与事实陈述交叉核验",
            "severity": "high",
            "reasons": [
                f"段落 {idxs} 的 AIGC 风险较高，其中数据、结论性表述建议对照原始文献核实。",
                "生成式文本易出现引用张冠李戴或数据无法溯源，需人工复核。",
            ],
        })

    if re.search(r"\b(et al\.|等)\b", text, re.I) and len(text) < 800:
        conclusions.append({
            "id": "fact-thin-refs",
            "title": "引用密度偏低",
            "severity": "low",
            "reasons": [
                "全文较短但存在典型引用表述，建议检查参考文献列表是否完整。",
            ],
        })

    if not conclusions:
        conclusions.append({
            "id": "fact-ok",
            "title": "未发现显著事实性风险条目",
            "severity": "low",
            "reasons": [
                "规则层未命中明显 DOI/年代/高风险段落组合；仍建议结合人工审核与外部数据库核验。",
            ],
        })

    return conclusions[:8]
