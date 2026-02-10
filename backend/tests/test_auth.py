"""Tests for authentication endpoints.

Covers the critical auth paths:
- Login success / failure (credential validation)
- /me with and without token (authz guard)
- /logout token blacklisting
- Health check (baseline sanity)
"""

import pytest
from httpx import AsyncClient

from webmacs_backend.models import User

# conftest provides: client, admin_user, auth_headers
# conftest constants re-exported here for readability
from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLogin:
    """POST /api/v1/auth/login"""

    async def test_login_success(self, client: AsyncClient, admin_user: User) -> None:
        """Valid credentials → 200 + JWT + user metadata."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "access_token" in body
        assert body["username"] == admin_user.username
        assert body["public_id"] == admin_user.public_id

    async def test_login_wrong_password(self, client: AsyncClient, admin_user: User) -> None:
        """Wrong password → 401."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": "wrong-password"},
        )
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"]

    async def test_login_nonexistent_email(self, client: AsyncClient) -> None:
        """Unknown email → 401 (no user information leak)."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@nowhere.io", "password": "irrelevant"},
        )
        assert resp.status_code == 401

    async def test_login_missing_fields(self, client: AsyncClient) -> None:
        """Missing required fields → 422 validation error."""
        resp = await client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestMe:
    """GET /api/v1/auth/me"""

    async def test_me_authenticated(
        self, client: AsyncClient, auth_headers: dict, admin_user: User
    ) -> None:
        """Authenticated user gets their own profile."""
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == admin_user.email
        assert body["username"] == admin_user.username
        assert body["admin"] is True

    async def test_me_unauthenticated(self, client: AsyncClient) -> None:
        """No token → 401."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)

    async def test_me_invalid_token(self, client: AsyncClient) -> None:
        """Garbage token → 401."""
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLogout:
    """POST /api/v1/auth/logout"""

    async def test_logout_success(self, client: AsyncClient, auth_headers: dict) -> None:
        """Authenticated user can log out."""
        resp = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    async def test_logout_unauthenticated(self, client: AsyncClient) -> None:
        """No token → 401."""
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Health check (baseline sanity)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestHealthCheck:
    async def test_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
