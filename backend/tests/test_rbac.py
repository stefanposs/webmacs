"""Tests for RBAC (Role-Based Access Control) and API tokens.

Verifies:
  - Role hierarchy enforcement (admin > operator > viewer)
  - Viewer can read, but cannot write
  - Operator can read and write data, but cannot manage users/webhooks/plugins
  - Admin can do everything
  - API token authentication (create, use, revoke)
  - API token expiry
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pytest

from webmacs_backend.enums import UserRole
from webmacs_backend.models import ApiToken, User
from webmacs_backend.security import generate_api_token

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Role hierarchy tests
# ---------------------------------------------------------------------------


class TestRoleHierarchy:
    """Verify UserRole.has_at_least() works correctly."""

    def test_admin_has_at_least_all(self) -> None:
        assert UserRole.admin.has_at_least(UserRole.admin)
        assert UserRole.admin.has_at_least(UserRole.operator)
        assert UserRole.admin.has_at_least(UserRole.viewer)

    def test_operator_has_at_least(self) -> None:
        assert not UserRole.operator.has_at_least(UserRole.admin)
        assert UserRole.operator.has_at_least(UserRole.operator)
        assert UserRole.operator.has_at_least(UserRole.viewer)

    def test_viewer_has_at_least(self) -> None:
        assert not UserRole.viewer.has_at_least(UserRole.admin)
        assert not UserRole.viewer.has_at_least(UserRole.operator)
        assert UserRole.viewer.has_at_least(UserRole.viewer)


# ---------------------------------------------------------------------------
# Viewer cannot write, but can read
# ---------------------------------------------------------------------------


class TestViewerAccess:
    """Viewer can LIST/GET but not POST/PUT/DELETE on data endpoints."""

    async def test_viewer_can_list_events(
        self, client: AsyncClient, viewer_headers: dict[str, str], sample_event: object
    ) -> None:
        resp = await client.get("/api/v1/events", headers=viewer_headers)
        assert resp.status_code == 200

    async def test_viewer_cannot_create_event(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/events",
            headers=viewer_headers,
            json={"name": "New Event", "min_value": 0, "max_value": 100, "unit": "V", "type": "sensor"},
        )
        assert resp.status_code == 403

    async def test_viewer_can_list_experiments(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/experiments", headers=viewer_headers)
        assert resp.status_code == 200

    async def test_viewer_cannot_create_experiment(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/experiments", headers=viewer_headers, json={"name": "My Exp"}
        )
        assert resp.status_code == 403

    async def test_viewer_can_list_datapoints(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/datapoints", headers=viewer_headers)
        assert resp.status_code == 200

    async def test_viewer_cannot_create_datapoint(
        self, client: AsyncClient, viewer_headers: dict[str, str], sample_event: object
    ) -> None:
        resp = await client.post(
            "/api/v1/datapoints",
            headers=viewer_headers,
            json={"value": 42.0, "event_public_id": "evt-temp-001"},
        )
        assert resp.status_code == 403

    async def test_viewer_can_list_logs(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/logging", headers=viewer_headers)
        assert resp.status_code == 200

    async def test_viewer_cannot_create_log(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/logging",
            headers=viewer_headers,
            json={"content": "test", "logging_type": "info"},
        )
        assert resp.status_code == 403

    async def test_viewer_cannot_list_rules(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/rules", headers=viewer_headers)
        assert resp.status_code == 403

    async def test_viewer_cannot_manage_users(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/users", headers=viewer_headers)
        assert resp.status_code == 403

    async def test_viewer_cannot_manage_webhooks(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/webhooks", headers=viewer_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Operator can write data but not admin areas
# ---------------------------------------------------------------------------


class TestOperatorAccess:
    """Operator can CRUD data (events, experiments, rules) but not users/webhooks/ota."""

    async def test_operator_can_list_events(
        self, client: AsyncClient, operator_headers: dict[str, str], sample_event: object
    ) -> None:
        resp = await client.get("/api/v1/events", headers=operator_headers)
        assert resp.status_code == 200

    async def test_operator_can_create_event(
        self, client: AsyncClient, operator_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/events",
            headers=operator_headers,
            json={"name": "Operator Event", "min_value": 0, "max_value": 50, "unit": "A", "type": "sensor"},
        )
        assert resp.status_code == 201

    async def test_operator_can_list_rules(
        self, client: AsyncClient, operator_headers: dict[str, str], sample_rule: object
    ) -> None:
        resp = await client.get("/api/v1/rules", headers=operator_headers)
        assert resp.status_code == 200

    async def test_operator_cannot_manage_users(
        self, client: AsyncClient, operator_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/users", headers=operator_headers)
        assert resp.status_code == 403

    async def test_operator_cannot_manage_webhooks(
        self, client: AsyncClient, operator_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/webhooks", headers=operator_headers)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin can do everything
# ---------------------------------------------------------------------------


class TestAdminAccess:
    async def test_admin_can_list_users(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.get("/api/v1/users", headers=auth_headers)
        assert resp.status_code == 200

    async def test_admin_can_create_user_with_role(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "username": "newoperator",
                "email": "newop@test.io",
                "password": "secure12345",
                "role": "operator",
            },
        )
        assert resp.status_code == 201

    async def test_admin_can_list_webhooks(
        self, client: AsyncClient, auth_headers: dict[str, str], sample_webhook: object
    ) -> None:
        resp = await client.get("/api/v1/webhooks", headers=auth_headers)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# API Token tests
# ---------------------------------------------------------------------------


class TestApiTokens:
    """Test API token CRUD and authentication."""

    async def test_create_token(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/tokens", headers=auth_headers, json={"name": "Test Token"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Token"
        assert data["token"].startswith("wm_")
        assert "public_id" in data

    async def test_list_tokens(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Create a token first
        await client.post(
            "/api/v1/tokens", headers=auth_headers, json={"name": "List Test"}
        )
        resp = await client.get("/api/v1/tokens", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_delete_token(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        create_resp = await client.post(
            "/api/v1/tokens", headers=auth_headers, json={"name": "To Delete"}
        )
        token_id = create_resp.json()["public_id"]
        resp = await client.delete(f"/api/v1/tokens/{token_id}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_authenticate_with_api_token(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """Create a token, then use it to authenticate a request."""
        create_resp = await client.post(
            "/api/v1/tokens", headers=auth_headers, json={"name": "Auth Test"}
        )
        plain_token = create_resp.json()["token"]

        # Use the API token to list events
        token_headers = {"Authorization": f"Bearer {plain_token}"}
        resp = await client.get("/api/v1/events", headers=token_headers)
        assert resp.status_code == 200

    async def test_expired_api_token_rejected(
        self, client: AsyncClient, db_session: AsyncSession, admin_user: User
    ) -> None:
        """An expired API token should be rejected."""
        plain, token_hash = generate_api_token()
        api_token = ApiToken(
            public_id="expired-token-001",
            name="Expired Token",
            token_hash=token_hash,
            user_id=admin_user.id,
            expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
        )
        db_session.add(api_token)
        await db_session.commit()

        token_headers = {"Authorization": f"Bearer {plain}"}
        resp = await client.get("/api/v1/events", headers=token_headers)
        assert resp.status_code == 401

    async def test_invalid_api_token_rejected(self, client: AsyncClient) -> None:
        """A fabricated API token should be rejected."""
        token_headers = {"Authorization": "Bearer wm_fakeinvalidtoken12345"}
        resp = await client.get("/api/v1/events", headers=token_headers)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Login returns role in response
# ---------------------------------------------------------------------------


class TestLoginRole:
    async def test_login_returns_valid_token_with_role(
        self, client: AsyncClient, admin_user: User
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.io", "password": "adminpass123"},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # Use the token to check /auth/me — should include role
        me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["role"] == "admin"
