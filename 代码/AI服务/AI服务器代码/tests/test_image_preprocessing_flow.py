from __future__ import annotations

import io
import os
import shutil
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image


AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "代码" / "后端" / "后端代码"

if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from detection_service import DetectionService
from detection_service.contracts import DetectionResponse, StandardImageResult
from core.utils.image_preprocessing import (
    DetectionBatchImage,
    build_detection_batch_artifacts,
    detect_upload_kind,
)


class ImagePreprocessingFlowTest(unittest.TestCase):
    def test_detect_upload_kind_distinguishes_binary_image_and_zip(self):
        png_bytes = self._build_image_bytes("PNG", color=(12, 34, 56))
        zip_bytes = self._build_zip_fixture({"00000001.png": png_bytes})

        self.assertEqual(detect_upload_kind("figure.bin", "application/octet-stream", png_bytes), "image")
        self.assertEqual(detect_upload_kind("archive.bin", "application/octet-stream", zip_bytes), "zip")

    def test_backend_batch_packaging_matches_ai_side_extraction(self):
        service = DetectionService()
        temp_root = AI_ROOT / ".tmp-tests" / "image-flow"
        if temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=True)
        temp_root.mkdir(parents=True, exist_ok=True)

        image_three = temp_root / "figure_3.jpg"
        image_twelve = temp_root / "figure_12.png"
        image_three.write_bytes(self._build_image_bytes("JPEG", color=(220, 30, 10)))
        image_twelve.write_bytes(self._build_image_bytes("PNG", color=(15, 120, 200)))

        batch_dir = temp_root / "task_1_batch_0"
        zip_path, data_path = build_detection_batch_artifacts(
            batch_dir,
            [
                DetectionBatchImage(image_id=12, image_path=image_twelve),
                DetectionBatchImage(image_id=3, image_path=image_three),
            ],
            cmd_block_size=48,
            urn_k=0.2,
            if_use_llm=False,
        )

        request = service.build_request_from_files(zip_path, data_path, batch_id="batch_fixture")
        fake_response = DetectionResponse(
            schema_version="image-detection-v1",
            task_type="image",
            model_version="image-fixture-2026-04",
            batch_id="batch_fixture",
            results=[
                StandardImageResult(
                    image_name="00000003.jpg",
                    image_id=3,
                    model_version="image-fixture-2026-04",
                    overall_is_fake=False,
                    overall_confidence=0.0,
                    llm_text="",
                    llm_img=None,
                    ela=[],
                    exif_flags={"photoshop": False, "time_modified": False},
                    sub_method_results=[],
                    evidences=[],
                ),
                StandardImageResult(
                    image_name="00000012.png",
                    image_id=12,
                    model_version="image-fixture-2026-04",
                    overall_is_fake=False,
                    overall_confidence=0.0,
                    llm_text="",
                    llm_img=None,
                    ela=[],
                    exif_flags={"photoshop": False, "time_modified": False},
                    sub_method_results=[],
                    evidences=[],
                ),
            ],
        )

        captured = {}

        def fake_detect(_request, _context, extracted_inputs):
            captured["names"] = [item.image_name for item in extracted_inputs]
            captured["ids"] = [item.image_id for item in extracted_inputs]
            captured["exists"] = [item.image_path.exists() for item in extracted_inputs]
            return fake_response

        previous_temp_root = os.environ.get("AI_SERVICE_TEMP_ROOT")
        os.environ["AI_SERVICE_TEMP_ROOT"] = str(temp_root / "service-temp")
        try:
            with patch.object(service._task_handlers["image"], "detect", side_effect=fake_detect):
                response = service.handle_request(request)
        finally:
            if previous_temp_root is None:
                os.environ.pop("AI_SERVICE_TEMP_ROOT", None)
            else:
                os.environ["AI_SERVICE_TEMP_ROOT"] = previous_temp_root

        self.assertEqual(captured["names"], ["00000003.jpg", "00000012.png"])
        self.assertEqual(captured["ids"], [3, 12])
        self.assertEqual(captured["exists"], [True, True])
        self.assertEqual(response["batch_id"], "batch_fixture")
        self.assertEqual([item["image_id"] for item in response["results"]], [3, 12])

    @staticmethod
    def _build_image_bytes(fmt: str, *, color: tuple[int, int, int]) -> bytes:
        buffer = io.BytesIO()
        Image.new("RGB", (16, 16), color=color).save(buffer, format=fmt)
        return buffer.getvalue()

    @staticmethod
    def _build_zip_fixture(entries: dict[str, bytes]) -> bytes:
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for name, content in entries.items():
                zip_file.writestr(name, content)
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
