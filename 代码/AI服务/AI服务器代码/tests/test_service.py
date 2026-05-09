from __future__ import annotations

import base64
import io
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from detection_service import DetectionModelRegistry, DetectionService, ValidationError
from detection_service.contracts import DetectionResponse, StandardImageResult


class DetectionServiceTest(unittest.TestCase):
    def test_health_payload_exposes_methods_and_reserved_tasks(self):
        service = DetectionService()
        payload = service.health_payload()
        self.assertIn("image", payload["supported_tasks"])
        self.assertIn("paper", payload["supported_tasks"])
        self.assertIn("review", payload["supported_tasks"])
        self.assertEqual(payload["reserved_tasks"], [])
        self.assertEqual(payload["default_image_profile"], "default")
        self.assertIn("fast", payload["available_image_profiles"])
        self.assertIn("splicing", payload["image_methods"])

    def test_paper_task_accepts_backend_preprocessed_payload(self):
        service = DetectionService()
        response = service.handle_request(
            {
                "schema_version": "backend-ai-request-v1",
                "task_type": "paper",
                "batch_id": "paper_fixture",
                "parameters": {"model_version": "paper-fixture-2026-04", "threshold": 0.5},
                "payload_base64": self._build_payload_base64(
                    {
                        "schema_version": "paper-preprocess-v1",
                        "source_name": "paper.pdf",
                        "text": "This is a normalized paper paragraph for AI detection.",
                        "paragraphs": [
                            {
                                "index": 1,
                                "text": "This is a normalized paper paragraph for AI detection.",
                                "char_start": 0,
                                "char_end": 54,
                                "word_count": 9,
                            }
                        ],
                    }
                ),
            }
        )

        self.assertEqual(response["schema_version"], "text-detection-v1")
        self.assertEqual(response["task_type"], "paper")
        self.assertEqual(response["results"][0]["source_name"], "paper.pdf")
        self.assertEqual(response["results"][0]["details"]["paragraph_count"], 1)
        self.assertIn("paper_summary", response["results"][0]["details"])
        self.assertIn("paragraph_risks", response["results"][0]["details"])
        self.assertIn("basic_explanation", response["results"][0]["details"])
        self.assertEqual(response["results"][0]["details"]["paper_summary"]["analyzed_paragraph_count"], 1)
        self.assertEqual(response["results"][0]["details"]["paragraph_risks"][0]["index"], 1)
        self.assertIn("risk_score", response["results"][0]["details"]["paragraph_risks"][0])
        self.assertIn("basic_explanation", response["results"][0]["details"]["paragraph_risks"][0])

    def test_review_task_accepts_backend_preprocessed_payload(self):
        service = DetectionService()
        response = service.handle_request(
            {
                "schema_version": "backend-ai-request-v1",
                "task_type": "review",
                "batch_id": "review_fixture",
                "parameters": {"model_version": "review-fixture-2026-04"},
                "payload_base64": self._build_payload_base64(
                    {
                        "schema_version": "review-preprocess-v1",
                        "source_name": "review.txt",
                        "text": "This review has already been cleaned by the backend.",
                        "text_length": 52,
                        "line_count": 1,
                    }
                ),
            }
        )

        self.assertEqual(response["schema_version"], "text-detection-v1")
        self.assertEqual(response["task_type"], "review")
        self.assertEqual(response["results"][0]["source_name"], "review.txt")
        self.assertEqual(response["results"][0]["details"]["line_count"], 1)
        self.assertIn("review_summary", response["results"][0]["details"])
        self.assertIn("ai_tendency", response["results"][0]["details"])
        self.assertIn("template_tendency", response["results"][0]["details"])
        self.assertIn("suspicious_segments", response["results"][0]["details"])
        self.assertIn("basic_explanation", response["results"][0]["details"])
        self.assertIn("score", response["results"][0]["details"]["ai_tendency"])
        self.assertIn("score", response["results"][0]["details"]["template_tendency"])

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

    def test_image_request_uses_profile_default_model_version(self):
        service = DetectionService()
        request = {
            "schema_version": "backend-ai-request-v1",
            "task_type": "image",
            "batch_id": "fast_profile_fixture",
            "parameters": {"model_profile": "fast"},
            "image_names": ["00000002.jpg"],
            "images_zip_base64": self._build_zip_base64({"00000002.jpg": b"fake"}),
        }

        fake_response = DetectionResponse(
            schema_version="image-detection-v1",
            task_type="image",
            model_version="image-detector-fast-2026-04",
            batch_id="fast_profile_fixture",
            results=[],
        )

        with patch.object(service._task_handlers["image"], "detect", return_value=fake_response) as mock_detect:
            service.handle_request(request)

        _, context, _ = mock_detect.call_args.args
        self.assertEqual(context.model_profile, "fast")
        self.assertEqual(context.model_version, "image-detector-fast-2026-04")

    def test_unknown_model_profile_is_rejected(self):
        service = DetectionService()
        request = {
            "schema_version": "backend-ai-request-v1",
            "task_type": "image",
            "batch_id": "bad_profile_fixture",
            "parameters": {"model_profile": "missing"},
            "image_names": ["00000003.jpg"],
            "images_zip_base64": self._build_zip_base64({"00000003.jpg": b"fake"}),
        }

        with self.assertRaises(ValidationError):
            service.handle_request(request)

    def test_management_payload_returns_selected_profile_details(self):
        service = DetectionService()
        payload = service.management_payload("fast")
        self.assertEqual(payload["selected_image_profile"]["name"], "fast")
        self.assertEqual(
            payload["selected_image_profile"]["model_version"],
            "image-detector-fast-2026-04",
        )
        self.assertEqual(
            payload["selected_image_profile"]["enabled_methods"],
            ["ela", "exif", "cmd", "splicing"],
        )

    def test_registry_is_hot_reloaded_when_config_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "model_registry.json"
            self._write_registry_config(
                config_path,
                {
                    "registry_version": "image-model-registry-v1",
                    "default_image_profile": "default",
                    "image_profiles": [
                        {
                            "name": "default",
                            "model_version": "v1",
                            "methods": [{"kind": "ela", "enabled": True}],
                        }
                    ],
                },
            )

            registry = DetectionModelRegistry.load(config_path)
            service = DetectionService(registry)
            initial = service.management_payload()
            self.assertEqual(initial["image_profile_details"]["default"]["model_version"], "v1")
            self.assertEqual(initial["registry_reload"]["reload_count"], 0)

            self._write_registry_config(
                config_path,
                {
                    "registry_version": "image-model-registry-v2",
                    "default_image_profile": "fast",
                    "image_profiles": [
                        {
                            "name": "default",
                            "model_version": "v2-default",
                            "methods": [{"kind": "ela", "enabled": True}],
                        },
                        {
                            "name": "fast",
                            "model_version": "v2-fast",
                            "methods": [{"kind": "exif", "enabled": True}],
                        },
                    ],
                },
                ensure_newer=True,
            )

            reloaded = service.management_payload("fast")
            self.assertEqual(reloaded["registry_version"], "image-model-registry-v2")
            self.assertEqual(reloaded["default_image_profile"], "fast")
            self.assertEqual(reloaded["selected_image_profile"]["model_version"], "v2-fast")
            self.assertEqual(reloaded["registry_reload"]["reload_count"], 1)
            self.assertIsNone(reloaded["registry_reload"]["last_reload_error"])

    def test_invalid_hot_reload_keeps_previous_registry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "model_registry.json"
            self._write_registry_config(
                config_path,
                {
                    "registry_version": "image-model-registry-v1",
                    "default_image_profile": "default",
                    "image_profiles": [
                        {
                            "name": "default",
                            "model_version": "stable",
                            "methods": [{"kind": "ela", "enabled": True}],
                        }
                    ],
                },
            )

            registry = DetectionModelRegistry.load(config_path)
            service = DetectionService(registry)
            current_ns = time.time_ns()
            config_path.write_text("{ bad json", encoding="utf-8")
            os.utime(config_path, ns=(current_ns + 5_000_000, current_ns + 5_000_000))

            payload = service.management_payload()
            self.assertEqual(payload["registry_version"], "image-model-registry-v1")
            self.assertEqual(payload["image_profile_details"]["default"]["model_version"], "stable")
            self.assertEqual(payload["registry_reload"]["reload_count"], 0)
            self.assertIn("not valid JSON", payload["registry_reload"]["last_reload_error"])

    @staticmethod
    def _build_zip_base64(entries: dict[str, bytes]) -> str:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for name, content in entries.items():
                zip_file.writestr(name, content)
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @staticmethod
    def _build_payload_base64(payload: dict) -> str:
        return base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")

    @staticmethod
    def _write_registry_config(path: Path, payload: dict, *, ensure_newer: bool = False) -> None:
        previous_mtime = path.stat().st_mtime_ns if ensure_newer and path.exists() else None
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if previous_mtime is not None:
            next_mtime = max(time.time_ns(), previous_mtime + 1_000_000)
            os.utime(path, ns=(next_mtime, next_mtime))


if __name__ == "__main__":
    unittest.main()
