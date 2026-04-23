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


if __name__ == "__main__":
    unittest.main()
