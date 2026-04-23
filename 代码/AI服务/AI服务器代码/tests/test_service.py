from __future__ import annotations

import base64
import io
import sys
import zipfile
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from detection_service import DetectionService
from detection_service.contracts import DetectionResponse, StandardImageResult


class DetectionServiceTest(unittest.TestCase):
    def test_health_payload_exposes_methods_and_reserved_tasks(self):
        service = DetectionService()
        payload = service.health_payload()
        self.assertIn("image", payload["supported_tasks"])
        self.assertIn("paper", payload["reserved_tasks"])
        self.assertIn("splicing", payload["image_methods"])

    def test_paper_task_route_is_reserved(self):
        service = DetectionService()
        with self.assertRaises(NotImplementedError):
            service.handle_request(
                {
                    "schema_version": "backend-ai-request-v1",
                    "task_type": "paper",
                    "batch_id": "paper_fixture",
                    "parameters": {"model_version": "paper-fixture-2026-04"},
                    "payload_base64": base64.b64encode(b"paper content").decode("ascii"),
                }
            )

    def test_image_request_is_forwarded_to_task_handler(self):
        service = DetectionService()
        request = {
            "schema_version": "backend-ai-request-v1",
            "task_type": "image",
            "batch_id": "image_fixture",
            "parameters": {"model_version": "image-fixture-2026-04"},
            "image_names": ["00000001.jpg"],
            "images_zip_base64": self._build_zip_base64({"00000001.jpg": b"fake"}),
        }

        fake_response = DetectionResponse(
            schema_version="image-detection-v1",
            task_type="image",
            model_version="image-fixture-2026-04",
            batch_id="image_fixture",
            results=[
                StandardImageResult(
                    image_name="00000001.jpg",
                    image_id=1,
                    model_version="image-fixture-2026-04",
                    overall_is_fake=False,
                    overall_confidence=0.0,
                    llm_text="",
                    llm_img=None,
                    ela=[],
                    exif_flags={"photoshop": False, "time_modified": False},
                    sub_method_results=[],
                    evidences=[],
                )
            ],
        )

        with patch.object(service._task_handlers["image"], "detect", return_value=fake_response) as mock_detect:
            response = service.handle_request(request)

        self.assertEqual(response["task_type"], "image")
        self.assertEqual(response["results"][0]["image_id"], 1)
        mock_detect.assert_called_once()

    @staticmethod
    def _build_zip_base64(entries: dict[str, bytes]) -> str:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for name, content in entries.items():
                zip_file.writestr(name, content)
        return base64.b64encode(buffer.getvalue()).decode("ascii")


if __name__ == "__main__":
    unittest.main()
