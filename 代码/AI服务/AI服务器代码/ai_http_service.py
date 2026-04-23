from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from detection_service import DetectionService, TaskNotImplementedError, ValidationError


IMAGE_BATCH_PATH = "/api/v1/image-detection/batches"
HEALTH_PATH = "/health"
SERVICE = DetectionService()


class AIHTTPHandler(BaseHTTPRequestHandler):
    server_version = "AcademicAIGateway/2.0"

    def do_GET(self) -> None:
        if self.path == HEALTH_PATH:
            self._send_json(HTTPStatus.OK, SERVICE.health_payload())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != IMAGE_BATCH_PATH:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        try:
            self._check_auth()
            request_data = self._read_json_body()
            response_data = handle_image_detection_batch(request_data)
        except ValidationError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except TaskNotImplementedError as exc:
            self._send_json(HTTPStatus.NOT_IMPLEMENTED, {"error": str(exc)})
            return
        except PermissionError as exc:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            return
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, response_data)

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def _check_auth(self) -> None:
        expected_token = os.getenv("AI_SERVICE_API_TOKEN", "")
        if not expected_token:
            return
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {expected_token}":
            raise PermissionError("invalid AI service token")

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValidationError("empty request body")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError("request body must be JSON") from exc

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def handle_image_detection_batch(request_data: Dict[str, Any]) -> Dict[str, Any]:
    return SERVICE.handle_request(request_data)


def main() -> None:
    parser = argparse.ArgumentParser(description="HTTP detection service for backend/AI integration.")
    parser.add_argument("--host", default=os.getenv("AI_SERVICE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AI_SERVICE_PORT", "8010")))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AIHTTPHandler)
    print(f"AI HTTP service listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
