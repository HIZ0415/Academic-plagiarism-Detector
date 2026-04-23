from __future__ import annotations

from dataclasses import dataclass

from .contracts import DetectionContext, DetectionResponse, ImageInput
from .image_detector import ImageDetector
from .model_registry import DetectionModelRegistry
from .service_errors import TaskNotImplementedError


class TaskHandler:
    task_type: str

    def detect(self, request, context: DetectionContext, extracted_inputs: list[ImageInput] | None = None):
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

    def detect(self, request, context: DetectionContext, extracted_inputs: list[ImageInput] | None = None):
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


@dataclass(slots=True)
class UnimplementedTaskHandler(TaskHandler):
    task_type: str

    def detect(self, request, context: DetectionContext, extracted_inputs: list[ImageInput] | None = None):
        raise TaskNotImplementedError(
            f"task_type '{self.task_type}' is reserved but not implemented yet"
        )
