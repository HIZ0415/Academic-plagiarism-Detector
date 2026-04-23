from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from detection_service import DetectionService, TaskNotImplementedError, ValidationError


IMAGE_BATCH_PATH = "/api/v1/image-detection/batches"
HEALTH_PATH = "/health"
SERVICE = DetectionService()


def resolve_request_timeout_seconds() -> float | None:
    raw_value = os.getenv("AI_SERVICE_TIMEOUT_SECONDS", "120").strip()
    if not raw_value:
        return None
    timeout_seconds = float(raw_value)
    return timeout_seconds if timeout_seconds > 0 else None


def map_exception_to_status(exc: Exception) -> HTTPStatus:
    if isinstance(exc, ValidationError):
        return HTTPStatus.BAD_REQUEST
    if isinstance(exc, TaskNotImplementedError):
        return HTTPStatus.NOT_IMPLEMENTED
    if isinstance(exc, PermissionError):
        return HTTPStatus.UNAUTHORIZED
    if isinstance(exc, TimeoutError):
        return HTTPStatus.GATEWAY_TIMEOUT
    return HTTPStatus.INTERNAL_SERVER_ERROR


def dispatch_detection_request(
    request_data: Dict[str, Any],
    *,
    timeout_seconds: float | None = None,
) -> Dict[str, Any]:
    timeout_seconds = resolve_request_timeout_seconds() if timeout_seconds is None else timeout_seconds
    if timeout_seconds is None:
        return SERVICE.handle_request(request_data)

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(SERVICE.handle_request, request_data)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise TimeoutError(f"AI detection timed out after {timeout_seconds:.1f}s") from exc
    except Exception:
        executor.shutdown(wait=True, cancel_futures=False)
        raise
    else:
        executor.shutdown(wait=True, cancel_futures=False)


class AIHTTPHandler(BaseHTTPRequestHandler):
    server_version = "AcademicAIGateway/2.1"

    def do_GET(self) -> None:
        if self.path == HEALTH_PATH:
            self._send_json(HTTPStatus.OK, SERVICE.health_payload())
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != IMAGE_BATCH_PATH:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        request_started_at = time.perf_counter()
        request_data: Dict[str, Any] | None = None
        try:
            self._check_auth()
            request_data = self._read_json_body()
            self._log_request("accepted", request_data)
            response_data = dispatch_detection_request(request_data)
        except Exception as exc:
            status = map_exception_to_status(exc)
            self._log_request(
                "failed",
                request_data,
                status=status,
                elapsed_ms=(time.perf_counter() - request_started_at) * 1000.0,
                error=str(exc),
            )
            self._send_json(status, {"error": str(exc)})
            return

        elapsed_ms = (time.perf_counter() - request_started_at) * 1000.0
        self._log_request("completed", request_data, status=HTTPStatus.OK, elapsed_ms=elapsed_ms)
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

    def _log_request(
        self,
        event: str,
        request_data: Dict[str, Any] | None,
        *,
        status: HTTPStatus | None = None,
        elapsed_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        payload = {
            "event": event,
            "task_type": (request_data or {}).get("task_type"),
            "batch_id": (request_data or {}).get("batch_id"),
        }
        if status is not None:
            payload["status"] = int(status)
        if elapsed_ms is not None:
            payload["elapsed_ms"] = round(elapsed_ms, 2)
        if error:
            payload["error"] = error
        print(json.dumps(payload, ensure_ascii=False))


def handle_image_detection_batch(request_data: Dict[str, Any]) -> Dict[str, Any]:
    return dispatch_detection_request(request_data)


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
