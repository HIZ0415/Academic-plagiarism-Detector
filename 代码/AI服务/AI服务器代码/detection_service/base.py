from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from .contracts import DetectionContext, DetectionEvidence, ImageInput


class DetectionMethod(ABC):
    method_name: str
    category: str
    evidence_type: str

    @abstractmethod
    def run_batch(
        self,
        images: Sequence[ImageInput],
        context: DetectionContext,
    ) -> list[DetectionEvidence]:
        raise NotImplementedError
