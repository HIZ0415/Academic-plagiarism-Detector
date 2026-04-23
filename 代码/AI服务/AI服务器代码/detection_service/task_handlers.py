from __future__ import annotations

from dataclasses import dataclass

from .contracts import DetectionContext, DetectionResponse, ImageInput
from .image_detector import ImageDetector
from .service_errors import TaskNotImplementedError


class TaskHandler:
    task_type: str

    def detect(self, request, context: DetectionContext, extracted_inputs: list[ImageInput] | None = None):
        raise NotImplementedError


class ImageTaskHandler(TaskHandler):
    task_type = "image"

    def __init__(self, detector: ImageDetector | None = None) -> None:
        self.detector = detector or ImageDetector()

    def detect(self, request, context: DetectionContext, extracted_inputs: list[ImageInput] | None = None):
        if extracted_inputs is None:
            raise ValueError("image task requires extracted image inputs")
        return self.detector.detect(extracted_inputs, context)

    @property
    def method_names(self) -> list[str]:
        return self.detector.method_names


@dataclass(slots=True)
class UnimplementedTaskHandler(TaskHandler):
    task_type: str

    def detect(self, request, context: DetectionContext, extracted_inputs: list[ImageInput] | None = None):
        raise TaskNotImplementedError(
            f"task_type '{self.task_type}' is reserved but not implemented yet"
        )
