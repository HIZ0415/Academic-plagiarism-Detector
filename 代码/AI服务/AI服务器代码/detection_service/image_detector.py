from __future__ import annotations

from .contracts import DetectionContext, DetectionResponse, ImageInput, StandardImageResult
from .image_methods import (
    DEFAULT_LLM_TEXT,
    CopyMoveMethod,
    ELAMethod,
    ExifMethod,
    LLMMethod,
    URNMethod,
)


LEGACY_SUB_METHODS = ("splicing", "blurring", "bruteforce", "contrast", "inpainting")


class ImageDetector:
    def __init__(self) -> None:
        self.methods = [
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

    @property
    def method_names(self) -> list[str]:
        return [method.method_name for method in self.methods]

    def detect(
        self,
        images: list[ImageInput],
        context: DetectionContext,
    ) -> DetectionResponse:
        evidence_by_image = {image.image_name: [] for image in images}
        for method in self.methods:
            method_evidences = method.run_batch(images, context)
            if len(method_evidences) != len(images):
                raise ValueError(
                    f"method {method.method_name} returned {len(method_evidences)} results; "
                    f"expected {len(images)}"
                )
            for image, evidence in zip(images, method_evidences):
                evidence_by_image[image.image_name].append(evidence)

        results = [
            self._build_result(image, evidence_by_image[image.image_name], context)
            for image in images
        ]
        return DetectionResponse(
            schema_version="image-detection-v1",
            task_type="image",
            model_version=context.model_version,
            batch_id=context.batch_id,
            results=results,
        )

    def _build_result(
        self,
        image: ImageInput,
        evidences,
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

        sub_method_results = []
        max_probability = 0.0
        overall_is_fake = any(exif_flags.values())
        for method_name in LEGACY_SUB_METHODS:
            evidence = evidence_map[method_name]
            probability = float(evidence.confidence)
            max_probability = max(max_probability, probability)
            if evidence.suspicious:
                overall_is_fake = True
            sub_method_results.append(
                {
                    "method": method_name,
                    "probability": probability,
                    "mask": evidence.artifacts.get("mask", []),
                }
            )

        overall_confidence = 1.0 if any(exif_flags.values()) else max_probability

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
