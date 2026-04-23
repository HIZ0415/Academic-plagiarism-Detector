from __future__ import annotations

from .image_detector import ImageDetector
from .image_methods import build_image_methods
from .task_handlers import ImageTaskHandler, UnimplementedTaskHandler


def build_task_handlers():
    image_detector = ImageDetector(methods=build_image_methods())
    return {
        "image": ImageTaskHandler(image_detector),
        "paper": UnimplementedTaskHandler("paper"),
        "review": UnimplementedTaskHandler("review"),
    }
