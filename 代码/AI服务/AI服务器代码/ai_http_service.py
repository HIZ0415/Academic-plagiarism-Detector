from __future__ import annotations

import argparse
import base64
import json
import os
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from typing import Any, Dict, List


SERVICE_VERSION = "ai-http-stub-2026-04"
IMAGE_BATCH_PATH = "/api/v1/image-detection/batches"
HEALTH_PATH = "/health"


class AIRequestError(ValueError):
    pass


class AIHTTPHandler(BaseHTTPRequestHandler):
    server_version = "AcademicAIGateway/1.0"

    def do_GET(self) -> None:
        if self.path == HEALTH_PATH:
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service_version": SERVICE_VERSION,
                    "supported_tasks": ["image"],
                },
            )
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
        except AIRequestError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
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
            raise AIRequestError("empty request body")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise AIRequestError("request body must be JSON") from exc

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def handle_image_detection_batch(request_data: Dict[str, Any]) -> Dict[str, Any]:
    if request_data.get("schema_version") != "backend-ai-request-v1":
        raise AIRequestError("unsupported schema_version")
    if request_data.get("task_type") != "image":
        raise AIRequestError("unsupported task_type")

    zip_base64 = request_data.get("images_zip_base64")
    if not zip_base64:
        raise AIRequestError("images_zip_base64 is required")

    extracted_image_names = _extract_image_names(zip_base64)
    image_names = request_data.get("image_names") or extracted_image_names
    if len(image_names) != len(extracted_image_names):
        raise AIRequestError("image_names count does not match zip image count")
    parameters = request_data.get("parameters") or {}
    model_version = parameters.get("model_version") or SERVICE_VERSION

    return {
        "schema_version": "image-detection-v1",
        "task_type": "image",
        "model_version": model_version,
        "batch_id": request_data.get("batch_id"),
        "results": [_build_stub_image_result(name, model_version) for name in image_names],
    }


def _extract_image_names(zip_base64: str) -> List[str]:
    try:
        zip_bytes = base64.b64decode(zip_base64)
    except ValueError as exc:
        raise AIRequestError("images_zip_base64 is not valid base64") from exc

    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            return [
                name
                for name in zf.namelist()
                if not name.endswith("/") and name.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
            ]
    except zipfile.BadZipFile as exc:
        raise AIRequestError("images_zip_base64 is not a valid zip file") from exc


def _build_stub_image_result(image_name: str, model_version: str) -> Dict[str, Any]:
    return {
        "schema_version": "image-detection-v1",
        "task_type": "image",
        "model_version": model_version,
        "image_name": image_name,
        "overall_is_fake": False,
        "overall_confidence": 0.0,
        "llm_text": "无",
        "llm_img": None,
        "ela": [[0, 0], [0, 0]],
        "exif_flags": {
            "photoshop": False,
            "time_modified": False,
        },
        "sub_method_results": [
            {
                "method": method,
                "probability": 0.0,
                "mask": [[0.0, 0.0], [0.0, 0.0]],
            }
            for method in ("splicing", "blurring", "bruteforce", "contrast", "inpainting")
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="HTTP stub for backend/AI integration.")
    parser.add_argument("--host", default=os.getenv("AI_SERVICE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("AI_SERVICE_PORT", "8010")))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AIHTTPHandler)
    print(f"AI HTTP service listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
