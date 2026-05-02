from __future__ import annotations

import sys
import time
from http import HTTPStatus
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ai_http_service
from detection_service import TaskNotImplementedError, ValidationError


class AIHTTPServiceTest(unittest.TestCase):
    def test_map_exception_to_status(self):
        self.assertEqual(ai_http_service.map_exception_to_status(ValidationError("bad")), HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            ai_http_service.map_exception_to_status(TaskNotImplementedError("todo")),
            HTTPStatus.NOT_IMPLEMENTED,
        )
        self.assertEqual(ai_http_service.map_exception_to_status(PermissionError("no")), HTTPStatus.UNAUTHORIZED)
        self.assertEqual(ai_http_service.map_exception_to_status(TimeoutError("slow")), HTTPStatus.GATEWAY_TIMEOUT)
        self.assertEqual(ai_http_service.map_exception_to_status(RuntimeError("boom")), HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_map_exception_to_error_code(self):
        self.assertEqual(ai_http_service.map_exception_to_error_code(ValidationError("bad")), "validation_error")
        self.assertEqual(
            ai_http_service.map_exception_to_error_code(TaskNotImplementedError("todo")),
            "task_not_implemented",
        )
        self.assertEqual(ai_http_service.map_exception_to_error_code(PermissionError("no")), "unauthorized")
        self.assertEqual(ai_http_service.map_exception_to_error_code(TimeoutError("slow")), "timeout")
        self.assertEqual(ai_http_service.map_exception_to_error_code(RuntimeError("boom")), "internal_error")

    def test_build_error_response_keeps_legacy_error_field(self):
        payload = ai_http_service.build_error_response(
            status=HTTPStatus.BAD_REQUEST,
            message="bad request",
            error_code="validation_error",
            error_type="ValidationError",
            request_data={"task_type": "image", "batch_id": "task_1_batch_0"},
            details={"field": "schema_version"},
        )
        self.assertEqual(payload["schema_version"], "ai-service-error-v1")
        self.assertEqual(payload["error_code"], "validation_error")
        self.assertEqual(payload["error_type"], "ValidationError")
        self.assertEqual(payload["message"], "bad request")
        self.assertEqual(payload["error"], "bad request")
        self.assertEqual(payload["status"], 400)
        self.assertFalse(payload["retriable"])
        self.assertEqual(payload["task_type"], "image")
        self.assertEqual(payload["batch_id"], "task_1_batch_0")
        self.assertEqual(payload["details"], {"field": "schema_version"})

    def test_build_error_response_from_exception_marks_timeout_retriable(self):
        status, payload = ai_http_service.build_error_response_from_exception(
            TimeoutError("slow"),
            request_data={"task_type": "image", "batch_id": "batch_1"},
        )
        self.assertEqual(status, HTTPStatus.GATEWAY_TIMEOUT)
        self.assertEqual(payload["error_code"], "timeout")
        self.assertTrue(payload["retriable"])
        self.assertEqual(payload["batch_id"], "batch_1")

    def test_dispatch_detection_request_uses_service(self):
        expected = {"task_type": "image", "results": []}
        with patch.object(ai_http_service.SERVICE, "handle_request", return_value=expected) as mock_handle:
            response = ai_http_service.dispatch_detection_request({"task_type": "image"}, timeout_seconds=None)
        self.assertEqual(response, expected)
        mock_handle.assert_called_once()

    def test_dispatch_detection_request_times_out(self):
        def slow_handle(_request):
            time.sleep(0.05)
            return {"task_type": "image", "results": []}

        with patch.object(ai_http_service.SERVICE, "handle_request", side_effect=slow_handle):
            with self.assertRaises(TimeoutError):
                ai_http_service.dispatch_detection_request({"task_type": "image"}, timeout_seconds=0.01)

    def test_handle_management_registry_request_uses_service(self):
        expected = {"status": "ok", "default_image_profile": "default"}
        with patch.object(ai_http_service.SERVICE, "management_payload", return_value=expected) as mock_handle:
            response = ai_http_service.handle_management_registry_request("fast")
        self.assertEqual(response, expected)
        mock_handle.assert_called_once_with("fast")


if __name__ == "__main__":
    unittest.main()
