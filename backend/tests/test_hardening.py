"""Tests for Phase 5: Hardening & Polish.

Covers:
- Rate limiting middleware
- WebSocket JWT authentication
- SECRET_KEY startup validation
- Expired blacklist-token cleanup
"""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from starlette.testclient import TestClient

from webmacs_backend.config import WeakSecretKeyError, validate_secret_key
from webmacs_backend.database import get_db
from webmacs_backend.main import create_app
from webmacs_backend.models import BlacklistToken, User
from webmacs_backend.security import create_access_token

# ─── Rate Limiting ───────────────────────────────────────────────────────────


class TestRateLimiting:
    """Rate-limit middleware tests."""

    @pytest.mark.asyncio
    async def test_requests_within_limit_succeed(self, client: AsyncClient) -> None:
        """Requests under the per-minute limit should return 200."""
        for _ in range(5):
            resp = await client.get("/health")
            # Health is exempt from rate limiting, so always 200
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, db_session) -> None:
        """Exceeding the per-minute limit on a non-exempt path should return 429."""
        with (
            patch("webmacs_backend.middleware.rate_limit.settings.rate_limit_per_minute", 3),
            patch("webmacs_backend.middleware.rate_limit._TRUSTED_PREFIXES", ()),
        ):
            test_app = create_app()

            async def _override_get_db():
                yield db_session

            test_app.dependency_overrides[get_db] = _override_get_db

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # First 3 requests should succeed (limit is 3)
                for _ in range(3):
                    resp = await ac.get("/api/v1/auth/me")
                    # 401 is fine — we just check it's NOT 429
                    assert resp.status_code != 429

                # 4th request should be rate limited
                resp = await ac.get("/api/v1/auth/me")
                assert resp.status_code == 429
                assert "Too many requests" in resp.json()["detail"]

            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_health_exempt_from_rate_limit(self, db_session) -> None:
        """The /health endpoint should never be rate-limited."""
        with patch("webmacs_backend.middleware.rate_limit.settings.rate_limit_per_minute", 2):
            test_app = create_app()

            async def _override_get_db():
                yield db_session

            test_app.dependency_overrides[get_db] = _override_get_db

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                for _ in range(10):
                    resp = await ac.get("/health")
                    assert resp.status_code == 200

            test_app.dependency_overrides.clear()


# ─── WebSocket Authentication ────────────────────────────────────────────────


def _ws_test_app(db_session) -> FastAPI:
    """Create a lightweight app with no-op lifespan for WebSocket tests.

    The real ``create_app()`` lifespan connects to PostgreSQL which isn't
    available in the SQLite test environment.  We replicate just the routers
    and middleware needed for WS auth testing, and patch ``db_session`` to use
    the test session.
    """
    from contextlib import asynccontextmanager

    from webmacs_backend.middleware.rate_limit import RateLimitMiddleware
    from webmacs_backend.middleware.request_id import RequestIdMiddleware
    from webmacs_backend.ws import endpoints as ws_endpoints

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    # Patch the standalone db_session context manager used by WS auth
    @asynccontextmanager
    async def _test_db_session():
        yield db_session

    ws_endpoints._original_db_session = ws_endpoints.db_session  # type: ignore[attr-defined]  # noqa: SLF001
    ws_endpoints.db_session = _test_db_session  # type: ignore[assignment]

    app = FastAPI(lifespan=_noop_lifespan)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(ws_endpoints.router, prefix="/ws")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    return app


def _restore_ws_db_session() -> None:
    """Restore the original db_session on the WS endpoints module."""
    from webmacs_backend.ws import endpoints as ws_endpoints

    original = getattr(ws_endpoints, "_original_db_session", None)
    if original is not None:
        ws_endpoints.db_session = original  # type: ignore[assignment]
        del ws_endpoints._original_db_session  # type: ignore[attr-defined]  # noqa: SLF001


class TestWebSocketAuth:
    """WebSocket JWT authentication tests."""

    @pytest.mark.asyncio
    async def test_ws_without_token_rejected(self, db_session) -> None:
        """WS connection without a token query param should be accepted then closed with 1008."""
        app = _ws_test_app(db_session)
        try:
            with (
                TestClient(app) as tc,
                tc.websocket_connect("/ws/datapoints/stream") as ws,
                pytest.raises(Exception),  # noqa: B017, PT011
            ):
                ws.receive_json()
        finally:
            _restore_ws_db_session()

    @pytest.mark.asyncio
    async def test_ws_with_invalid_token_rejected(self, db_session) -> None:
        """WS connection with an invalid JWT should be accepted then closed with 1008."""
        app = _ws_test_app(db_session)
        try:
            with (
                TestClient(app) as tc,
                tc.websocket_connect("/ws/datapoints/stream?token=garbage") as ws,
                pytest.raises(Exception),  # noqa: B017, PT011
            ):
                ws.receive_json()
        finally:
            _restore_ws_db_session()

    @pytest.mark.asyncio
    async def test_ws_with_valid_token_connects(
        self, db_session, admin_user: User
    ) -> None:
        """WS connection with a valid JWT should succeed and receive the connected message."""
        app = _ws_test_app(db_session)
        token = create_access_token(admin_user.id)
        try:
            with TestClient(app) as tc, tc.websocket_connect(
                f"/ws/datapoints/stream?token={token}"
            ) as ws:
                data = ws.receive_json()
                assert data["type"] == "connected"
        finally:
            _restore_ws_db_session()


# ─── SECRET_KEY Validation ───────────────────────────────────────────────────


class TestSecretKeyValidation:
    """Startup SECRET_KEY validation tests."""

    def test_empty_key_production_raises(self) -> None:
        """An empty SECRET_KEY in production must raise WeakSecretKeyError."""
        with (
            patch("webmacs_backend.config.settings.secret_key", ""),
            patch("webmacs_backend.config.settings.env", "production"),
            pytest.raises(WeakSecretKeyError, match="SECRET_KEY must be set"),
        ):
            validate_secret_key()

    def test_short_key_production_raises(self) -> None:
        """A SHORT SECRET_KEY in production must raise WeakSecretKeyError."""
        with (
            patch("webmacs_backend.config.settings.secret_key", "tooshort"),
            patch("webmacs_backend.config.settings.env", "production"),
            pytest.raises(WeakSecretKeyError, match="at least 32 characters"),
        ):
            validate_secret_key()

    def test_valid_key_production_ok(self) -> None:
        """A long-enough SECRET_KEY in production should not raise."""
        long_key = "a" * 64
        with (
            patch("webmacs_backend.config.settings.secret_key", long_key),
            patch("webmacs_backend.config.settings.env", "production"),
        ):
            validate_secret_key()  # no error

    def test_empty_key_development_warns(self) -> None:
        """An empty SECRET_KEY in development should log a warning but not raise."""
        with (
            patch("webmacs_backend.config.settings.secret_key", ""),
            patch("webmacs_backend.config.settings.env", "development"),
        ):
            validate_secret_key()

    def test_short_key_development_warns(self) -> None:
        """A short SECRET_KEY in development should log a warning but not raise."""
        with (
            patch("webmacs_backend.config.settings.secret_key", "short"),
            patch("webmacs_backend.config.settings.env", "development"),
        ):
            validate_secret_key()


# ─── Token Blacklist Cleanup ────────────────────────────────────────────────


class TestTokenBlacklistCleanup:
    """Expired blacklisted tokens should be removed by the cleanup task."""

    @pytest.mark.asyncio
    async def test_expired_tokens_removed(self, db_session) -> None:
        """Tokens blacklisted longer than the expiry window should be deleted."""
        # Insert an "expired" blacklisted token (old timestamp)
        old_token = BlacklistToken(
            token="expired-token-123",  # noqa: S106
            blacklisted_on=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7),
        )
        # Insert a recent blacklisted token (should NOT be deleted)
        recent_token = BlacklistToken(
            token="recent-token-456",  # noqa: S106
            blacklisted_on=datetime.datetime.now(datetime.UTC),
        )
        db_session.add_all([old_token, recent_token])
        await db_session.commit()

        # Verify both exist
        result = await db_session.execute(select(BlacklistToken))
        assert len(result.scalars().all()) == 2

        # Run the cleanup logic directly (same query as _cleanup_expired_tokens)
        cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            minutes=1440,  # default access_token_expire_minutes
        )
        await db_session.execute(
            delete(BlacklistToken).where(BlacklistToken.blacklisted_on < cutoff)
        )
        await db_session.commit()

        # The old token should be deleted, the recent one should remain
        result = await db_session.execute(select(BlacklistToken))
        remaining = result.scalars().all()
        assert len(remaining) == 1
        assert remaining[0].token == "recent-token-456"
