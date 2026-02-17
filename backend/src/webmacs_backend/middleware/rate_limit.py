"""In-memory rate-limiting ASGI middleware.

Design:
- Tracks request timestamps per client IP in a plain dict (no Redis needed).
- Reads ``settings.rate_limit_per_minute`` for the limit (default 100).
- Respects ``X-Forwarded-For`` / ``X-Real-IP`` headers behind a reverse proxy.
- Skips WebSocket upgrade requests (``/ws`` paths) and the ``/health`` endpoint.
- Periodically prunes stale entries to keep memory bounded.
- Returns 429 Too Many Requests with a JSON body when the limit is exceeded.

Note: In-memory state is per-worker. Single-worker deployment is assumed.
For multi-worker setups, use Redis-backed rate limiting.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

import structlog

from webmacs_backend.config import settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

logger = structlog.get_logger()

# ─── Configuration ───────────────────────────────────────────────────────────

_WINDOW_SECONDS: float = 60.0
_CLEANUP_INTERVAL: float = 60.0  # prune stale IPs every 60 s

# ─── Paths exempt from rate limiting ─────────────────────────────────────────

_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/ws",
    "/health",
    "/api/v1/ota",
)

# POST-only rate-limit exemptions (e.g. controller pushing sensor data)
_EXEMPT_POST_PREFIXES: tuple[str, ...] = ("/api/v1/datapoints",)

# GET-only rate-limit exemptions (e.g. live dashboard polling)
_EXEMPT_GET_PREFIXES: tuple[str, ...] = ("/api/v1/datapoints",)

# ─── Internal / trusted networks (Docker bridge, loopback) ──────────────────

_TRUSTED_PREFIXES: tuple[str, ...] = (
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "10.",
    "192.168.",
    "127.",
)


class RateLimitMiddleware:
    """ASGI middleware that enforces per-IP request rate limits."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup: float = time.monotonic()

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _client_ip(scope: Scope) -> str:
        """Extract the real client IP, respecting reverse-proxy headers.

        Priority: X-Forwarded-For (first hop) → X-Real-IP → ASGI client.
        """
        headers = dict(scope.get("headers", []))
        # X-Forwarded-For: client, proxy1, proxy2 — take the leftmost
        xff: str = headers.get(b"x-forwarded-for", b"").decode()
        if xff:
            return xff.split(",", maxsplit=1)[0].strip()
        # Fallback: X-Real-IP (set by nginx)
        xri: str = headers.get(b"x-real-ip", b"").decode()
        if xri:
            return xri.strip()
        # Last resort: direct TCP peer
        client = scope.get("client")
        if client:
            return str(client[0])
        return "unknown"

    def _cleanup(self, now: float) -> None:
        """Remove timestamps older than the window for every tracked IP."""
        cutoff = now - _WINDOW_SECONDS
        stale_ips: list[str] = []
        for ip, timestamps in self._requests.items():
            self._requests[ip] = [t for t in timestamps if t > cutoff]
            if not self._requests[ip]:
                stale_ips.append(ip)
        for ip in stale_ips:
            del self._requests[ip]
        self._last_cleanup = now

    def _is_rate_limited(self, ip: str, now: float) -> bool:
        """Return True if *ip* has exceeded the per-minute limit."""
        cutoff = now - _WINDOW_SECONDS
        # Filter out old timestamps
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]
        if len(self._requests[ip]) >= settings.rate_limit_per_minute:
            return True
        self._requests[ip].append(now)
        return False

    # ── ASGI entrypoint ──────────────────────────────────────────────────

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # Let WebSocket and lifespan through unmodified
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        method: str = scope.get("method", "GET")
        if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return
        if method == "POST" and any(path.startswith(prefix) for prefix in _EXEMPT_POST_PREFIXES):
            await self.app(scope, receive, send)
            return
        if method == "GET" and any(path.startswith(prefix) for prefix in _EXEMPT_GET_PREFIXES):
            await self.app(scope, receive, send)
            return

        now = time.monotonic()

        # Periodic cleanup
        if now - self._last_cleanup > _CLEANUP_INTERVAL:
            self._cleanup(now)

        ip = self._client_ip(scope)

        # Skip rate limiting for internal Docker / loopback traffic
        if any(ip.startswith(prefix) for prefix in _TRUSTED_PREFIXES):
            await self.app(scope, receive, send)
            return

        if self._is_rate_limited(ip, now):
            logger.warning("rate_limit_exceeded", client_ip=ip)
            await self._send_429(send)
            return

        await self.app(scope, receive, send)

    # ── 429 response ─────────────────────────────────────────────────────

    @staticmethod
    async def _send_429(send: Send) -> None:
        """Send a 429 Too Many Requests JSON response."""
        body = b'{"detail":"Too many requests. Please try again later."}'
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", b"60"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
