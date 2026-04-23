from __future__ import annotations

from .aggregators import ImageResultAggregator
from .contracts import DetectionContext, DetectionResponse, ImageInput
from .image_methods import build_image_methods


class ImageDetector:
    def __init__(self, methods=None, aggregator: ImageResultAggregator | None = None) -> None:
        self.methods = methods or build_image_methods()
        self.aggregator = aggregator or ImageResultAggregator()

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
            self.aggregator.aggregate(image, evidence_by_image[image.image_name], context)
            for image in images
        ]
        return DetectionResponse(
            schema_version="image-detection-v1",
            task_type="image",
            model_version=context.model_version,
            batch_id=context.batch_id,
            results=results,
        )
