"""Pure ASGI middlewares for payload size limits and media type validation."""

import json
from typing import Dict, List, Tuple
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from mke_product.transport.models import TransportErrorCode, TransportErrorResponse

MAX_BODY_BYTES = 65536  # Exactly 64 KiB


def extract_media_type(raw_header: str) -> str:
    """Extract normalized media type from Content-Type header (portion before ';', stripped and lowercased)."""
    return raw_header.split(";")[0].strip().lower()


async def _send_json_response(
    send: Send,
    status_code: int,
    payload: TransportErrorResponse,
) -> None:
    """Send a structured JSON response via raw ASGI send callable."""
    body_bytes = json.dumps(payload.model_dump(mode="json")).encode("utf-8")
    headers: List[Tuple[bytes, bytes]] = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body_bytes)).encode("latin1")),
    ]
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": headers,
    })
    await send({
        "type": "http.response.body",
        "body": body_bytes,
        "more_body": False,
    })


class StreamPayloadLimitMiddleware:
    """Pure ASGI middleware that enforces the 64 KiB payload limit via bounded pre-read and replay."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers_dict: Dict[bytes, bytes] = dict(scope.get("headers", []))
        content_length_raw = headers_dict.get(b"content-length")

        # 1. Early inspection of Content-Length header
        if content_length_raw is not None:
            try:
                raw_str = content_length_raw.decode("latin1").strip()
                if not raw_str.isdigit():
                    raise ValueError("Malformed or negative Content-Length")
                declared_len = int(raw_str)
                if declared_len > MAX_BODY_BYTES:
                    error_resp = TransportErrorResponse(
                        transport_error_code=TransportErrorCode.PAYLOAD_TOO_LARGE,
                        message_vi="Kích thước yêu cầu vượt quá giới hạn 64 KiB.",
                        message_en="Request payload exceeds 64 KiB limit.",
                        details={"limit_bytes": MAX_BODY_BYTES, "declared_bytes": declared_len},
                    )
                    await _send_json_response(send, 413, error_resp)
                    return
            except (ValueError, UnicodeDecodeError):
                # Malformed or negative Content-Length header rejected immediately with HTTP 400
                error_resp = TransportErrorResponse(
                    transport_error_code=TransportErrorCode.MALFORMED_JSON,
                    message_vi="Tiêu đề Content-Length không hợp lệ.",
                    message_en="Invalid Content-Length header.",
                    details={"error": "INVALID_CONTENT_LENGTH"},
                )
                await _send_json_response(send, 400, error_resp)
                return

        # 2. Bounded stream pre-read (accumulates at most MAX_BODY_BYTES + 1 bytes)
        body_chunks: List[bytes] = []
        cumulative_bytes = 0

        while True:
            message = await receive()
            msg_type = message.get("type")

            if msg_type == "http.request":
                chunk = message.get("body", b"")
                if chunk:
                    # Bounded memory: cap in-memory accumulation to MAX_BODY_BYTES + 1
                    remaining_cap = (MAX_BODY_BYTES + 1) - cumulative_bytes
                    if remaining_cap > 0:
                        body_chunks.append(chunk[:remaining_cap])
                    cumulative_bytes += len(chunk)

                if cumulative_bytes > MAX_BODY_BYTES:
                    error_resp = TransportErrorResponse(
                        transport_error_code=TransportErrorCode.PAYLOAD_TOO_LARGE,
                        message_vi="Kích thước yêu cầu vượt quá giới hạn 64 KiB.",
                        message_en="Request payload exceeds 64 KiB limit.",
                        details={"limit_bytes": MAX_BODY_BYTES, "streamed_bytes_exceeded": cumulative_bytes},
                    )
                    await _send_json_response(send, 413, error_resp)
                    return

                if not message.get("more_body", False):
                    break
            elif msg_type == "http.disconnect":
                return
            else:
                break

        complete_body = b"".join(body_chunks)

        # 3. Replay bounded request body to downstream application
        replayed = False

        async def replayed_receive() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {
                    "type": "http.request",
                    "body": complete_body,
                    "more_body": False,
                }
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replayed_receive, send)


class MediaTypeEnforcementMiddleware:
    """Pure ASGI middleware enforcing Content-Type: application/json on API POST requests."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"].startswith("/api/"):
            headers_dict: Dict[bytes, bytes] = dict(scope.get("headers", []))
            raw_content_type = headers_dict.get(b"content-type", b"").decode("latin1")
            media_type = extract_media_type(raw_content_type)

            # Accept strictly "application/json" (with optional parameters like charset)
            if media_type != "application/json":
                error_resp = TransportErrorResponse(
                    transport_error_code=TransportErrorCode.UNSUPPORTED_MEDIA_TYPE,
                    message_vi="Tiêu đề Content-Type phải là 'application/json'.",
                    message_en="Content-Type header must be 'application/json'.",
                    details={"received_content_type": raw_content_type},
                )
                await _send_json_response(send, 415, error_resp)
                return

        await self.app(scope, receive, send)
