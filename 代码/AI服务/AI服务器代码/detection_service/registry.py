from __future__ import annotations

from .model_registry import DetectionModelRegistry
from .task_handlers import ImageTaskHandler, UnimplementedTaskHandler


def build_task_handlers(model_registry: DetectionModelRegistry | None = None):
    model_registry = model_registry or DetectionModelRegistry.load()
    return {
        "image": ImageTaskHandler(model_registry=model_registry),
        "paper": UnimplementedTaskHandler("paper"),
        "review": UnimplementedTaskHandler("review"),
    }
