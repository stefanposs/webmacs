"""Request-ID middleware — attaches a unique UUID to every request and binds it to structlog."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestIdMiddleware:
    """ASGI middleware that generates a UUID per HTTP request and binds it to structlog context."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())

        # Bind request_id into structlog context for every log line in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list[Any] = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            structlog.contextvars.clear_contextvars()
