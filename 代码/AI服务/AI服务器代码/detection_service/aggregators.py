from __future__ import annotations

from dataclasses import dataclass

from .contracts import DetectionContext, DetectionEvidence, ImageInput, StandardImageResult
from .image_methods import DEFAULT_LLM_TEXT


LEGACY_SUB_METHODS = ("splicing", "blurring", "bruteforce", "contrast", "inpainting")
NON_SUB_METHODS = {"llm", "ela", "exif"}


@dataclass(slots=True)
class ImageResultAggregator:
    def aggregate(
        self,
        image: ImageInput,
        evidences: list[DetectionEvidence],
        context: DetectionContext,
    ) -> StandardImageResult:
        evidence_map = {evidence.method: evidence for evidence in evidences}

        llm_evidence = evidence_map.get("llm")
        ela_evidence = evidence_map.get("ela")
        exif_evidence = evidence_map.get("exif")

        llm_text = DEFAULT_LLM_TEXT
        llm_img = None
        if llm_evidence is not None:
            llm_text = llm_evidence.artifacts.get("text", DEFAULT_LLM_TEXT) or DEFAULT_LLM_TEXT
            llm_img = llm_evidence.artifacts.get("mask")

        ela_mask = []
        if ela_evidence is not None:
            ela_mask = ela_evidence.artifacts.get("mask", [])

        exif_flags = {"photoshop": False, "time_modified": False}
        if exif_evidence is not None:
            exif_flags = exif_evidence.metadata.get("flags", exif_flags)

        detector_evidences = [evidence for evidence in evidences if evidence.method not in NON_SUB_METHODS]
        sub_method_results = []
        for method_name in LEGACY_SUB_METHODS:
            evidence = evidence_map.get(method_name)
            if evidence is None:
                sub_method_results.append({"method": method_name, "probability": 0.0, "mask": []})
                continue
            sub_method_results.append(
                {
                    "method": method_name,
                    "probability": float(evidence.confidence),
                    "mask": evidence.artifacts.get("mask", []),
                }
            )

        extra_method_names = sorted(
            evidence.method
            for evidence in detector_evidences
            if evidence.method not in LEGACY_SUB_METHODS
        )
        for method_name in extra_method_names:
            evidence = evidence_map[method_name]
            sub_method_results.append(
                {
                    "method": method_name,
                    "probability": float(evidence.confidence),
                    "mask": evidence.artifacts.get("mask", []),
                }
            )

        overall_is_fake = any(exif_flags.values()) or any(evidence.suspicious for evidence in detector_evidences)
        overall_confidence = 1.0 if any(exif_flags.values()) else max(
            (float(evidence.confidence) for evidence in detector_evidences),
            default=0.0,
        )

        return StandardImageResult(
            image_name=image.image_name,
            image_id=image.image_id,
            model_version=context.model_version,
            overall_is_fake=overall_is_fake,
            overall_confidence=overall_confidence,
            llm_text=llm_text,
            llm_img=llm_img,
            ela=ela_mask,
            exif_flags=exif_flags,
            sub_method_results=sub_method_results,
            evidences=evidences,
        )
