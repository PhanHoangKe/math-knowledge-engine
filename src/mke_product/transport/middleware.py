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
    """Pure ASGI middleware that strictly enforces the 64 KiB payload limit."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers_dict: Dict[bytes, bytes] = dict(scope.get("headers", []))
        content_length_raw = headers_dict.get(b"content-length")

        # 1. Early rejection when valid Content-Length header is present and > 65536
        if content_length_raw:
            try:
                declared_len = int(content_length_raw.decode("latin1").strip())
                if declared_len > MAX_BODY_BYTES:
                    error_resp = TransportErrorResponse(
                        transport_error_code=TransportErrorCode.PAYLOAD_TOO_LARGE,
                        message_vi="Kích thước yêu cầu vượt quá giới hạn 64 KiB.",
                        message_en="Request payload exceeds 64 KiB limit.",
                        details={"limit_bytes": MAX_BODY_BYTES, "declared_bytes": declared_len},
                    )
                    await _send_json_response(send, 413, error_resp)
                    return
            except ValueError:
                pass

        # 2. Wrap receive callable with byte accumulator for streaming/chunked requests
        cumulative_bytes = 0
        limit_exceeded = False
        response_sent = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_sent
            if limit_exceeded:
                if not response_sent:
                    response_sent = True
                    error_resp = TransportErrorResponse(
                        transport_error_code=TransportErrorCode.PAYLOAD_TOO_LARGE,
                        message_vi="Kích thước yêu cầu vượt quá giới hạn 64 KiB.",
                        message_en="Request payload exceeds 64 KiB limit.",
                        details={"limit_bytes": MAX_BODY_BYTES, "streamed_bytes_exceeded": cumulative_bytes},
                    )
                    await _send_json_response(send, 413, error_resp)
                return

            await send(message)

        async def limited_receive() -> Message:
            nonlocal cumulative_bytes, limit_exceeded
            if limit_exceeded:
                return {"type": "http.request", "body": b"", "more_body": False}

            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                cumulative_bytes += len(chunk)
                if cumulative_bytes > MAX_BODY_BYTES:
                    limit_exceeded = True
                    # Return empty to short-circuit further downstream buffering
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        try:
            await self.app(scope, limited_receive, send_wrapper)
        finally:
            if limit_exceeded and not response_sent:
                response_sent = True
                error_resp = TransportErrorResponse(
                    transport_error_code=TransportErrorCode.PAYLOAD_TOO_LARGE,
                    message_vi="Kích thước yêu cầu vượt quá giới hạn 64 KiB.",
                    message_en="Request payload exceeds 64 KiB limit.",
                    details={"limit_bytes": MAX_BODY_BYTES, "streamed_bytes_exceeded": cumulative_bytes},
                )
                await _send_json_response(send, 413, error_resp)


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
