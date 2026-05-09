from __future__ import annotations

import shutil
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = ROOT / ".tmp-tests" / "unit"


class LocalTemporaryDirectory:
    def __init__(self, prefix: str = "tmp") -> None:
        self.path = TEST_TEMP_ROOT / f"{prefix}_{uuid.uuid4().hex}"

    def __enter__(self) -> str:
        self.path.mkdir(parents=True, exist_ok=False)
        return str(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:
        shutil.rmtree(self.path, ignore_errors=True)
