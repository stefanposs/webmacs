"""Tests for OIDC / SSO authentication endpoints.

Covers:
- SSO config endpoint (enabled / disabled)
- SSO authorize redirect (PKCE, state token)
- SSO callback (code exchange, user create, link, admin-link refusal,
  email_verified enforcement, auto-create disabled, missing claims)
- One-time auth code exchange endpoint
- State token creation, verification, expiry, tampering
- Username sanitization
- OIDC discovery cache TTL
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webmacs_backend.config import settings
from webmacs_backend.enums import UserRole
from webmacs_backend.models import User
from webmacs_backend.security import hash_password

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_OIDC_CONFIG = {
    "issuer": "https://idp.example.com",
    "authorization_endpoint": "https://idp.example.com/authorize",
    "token_endpoint": "https://idp.example.com/token",
    "userinfo_endpoint": "https://idp.example.com/userinfo",
    "jwks_uri": "https://idp.example.com/.well-known/jwks.json",
}


def _enable_oidc() -> None:
    """Temporarily enable OIDC settings for testing."""
    settings.oidc_enabled = True
    settings.oidc_issuer_url = "https://idp.example.com"
    settings.oidc_client_id = "test-client"
    settings.oidc_client_secret = "test-secret"  # noqa: S105
    settings.oidc_provider_name = "TestIDP"
    settings.oidc_auto_create_users = True
    settings.oidc_default_role = "viewer"
    settings.oidc_frontend_url = "http://localhost:5173"


def _disable_oidc() -> None:
    """Restore OIDC settings to disabled."""
    settings.oidc_enabled = False
    settings.oidc_issuer_url = ""
    settings.oidc_client_id = ""
    settings.oidc_client_secret = ""
    settings.oidc_provider_name = "SSO"
    settings.oidc_auto_create_users = True
    settings.oidc_default_role = "viewer"
    settings.oidc_frontend_url = ""


@pytest.fixture(autouse=True)
def _reset_oidc_settings():
    """Reset OIDC settings and caches after each test."""
    yield
    _disable_oidc()
    import webmacs_backend.api.v1.sso as sso_module

    sso_module._oidc_config_cache = None
    sso_module._oidc_config_cached_at = 0
    sso_module._auth_codes.clear()


def _mock_callback_deps():
    """Return context managers for mocking OIDC config, OAuth client, and userinfo."""
    mock_cfg = patch("webmacs_backend.api.v1.sso._get_oidc_config", new_callable=AsyncMock)
    mock_client_cls = patch("webmacs_backend.api.v1.sso.AsyncOAuth2Client")
    mock_userinfo = patch("webmacs_backend.api.v1.sso._fetch_userinfo", new_callable=AsyncMock)
    return mock_cfg, mock_client_cls, mock_userinfo


async def _do_callback(
    client: AsyncClient,
    *,
    email: str = "sso-user@example.com",
    sub: str = "sso-user-123",
    preferred_username: str = "ssouser",
    email_verified: bool = True,
) -> object:
    """Helper: perform a full SSO callback with mocked IdP."""
    from webmacs_backend.api.v1.sso import _create_state_token

    valid_state = _create_state_token("fake-verifier")
    mock_cfg, mock_client_cls, mock_userinfo = _mock_callback_deps()

    with mock_cfg as m_cfg, mock_client_cls as m_cls, mock_userinfo as m_ui:
        m_cfg.return_value = _FAKE_OIDC_CONFIG
        mock_oauth = AsyncMock()
        mock_oauth.fetch_token = AsyncMock(return_value={"access_token": "fake-token"})
        m_cls.return_value = mock_oauth
        m_ui.return_value = {
            "sub": sub,
            "email": email,
            "preferred_username": preferred_username,
            "email_verified": email_verified,
        }
        return await client.get(
            f"/api/v1/auth/sso/callback?code=test-code&state={valid_state}",
            follow_redirects=False,
        )


# ---------------------------------------------------------------------------
# SSO Config endpoint
# ---------------------------------------------------------------------------


class TestSsoConfig:
    """Tests for GET /api/v1/auth/sso/config."""

    async def test_config_disabled(self, client: AsyncClient) -> None:
        _disable_oidc()
        resp = await client.get("/api/v1/auth/sso/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["provider_name"] == ""

    async def test_config_enabled(self, client: AsyncClient) -> None:
        _enable_oidc()
        resp = await client.get("/api/v1/auth/sso/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["provider_name"] == "TestIDP"
        assert data["authorize_url"] == "/api/v1/auth/sso/authorize"


# ---------------------------------------------------------------------------
# SSO Authorize endpoint
# ---------------------------------------------------------------------------


class TestSsoAuthorize:
    """Tests for GET /api/v1/auth/sso/authorize."""

    async def test_authorize_disabled_returns_404(self, client: AsyncClient) -> None:
        _disable_oidc()
        resp = await client.get("/api/v1/auth/sso/authorize", follow_redirects=False)
        assert resp.status_code == 404

    async def test_authorize_redirects_with_pkce(self, client: AsyncClient) -> None:
        _enable_oidc()
        with patch("webmacs_backend.api.v1.sso._get_oidc_config", new_callable=AsyncMock) as mock_cfg:
            mock_cfg.return_value = _FAKE_OIDC_CONFIG
            resp = await client.get("/api/v1/auth/sso/authorize", follow_redirects=False)

        assert resp.status_code == 307
        location = resp.headers["location"]
        assert location.startswith("https://idp.example.com/authorize")
        assert "client_id=test-client" in location
        assert "state=" in location
        assert "code_challenge=" in location
        assert "code_challenge_method=S256" in location


# ---------------------------------------------------------------------------
# SSO Callback endpoint
# ---------------------------------------------------------------------------


class TestSsoCallback:
    """Tests for GET /api/v1/auth/sso/callback."""

    async def test_callback_disabled_returns_404(self, client: AsyncClient) -> None:
        _disable_oidc()
        resp = await client.get("/api/v1/auth/sso/callback?code=abc&state=xyz", follow_redirects=False)
        assert resp.status_code == 404

    async def test_callback_invalid_state(self, client: AsyncClient) -> None:
        _enable_oidc()
        with patch("webmacs_backend.api.v1.sso._get_oidc_config", new_callable=AsyncMock) as mock_cfg:
            mock_cfg.return_value = _FAKE_OIDC_CONFIG
            resp = await client.get(
                "/api/v1/auth/sso/callback?code=abc&state=invalid-state",
                follow_redirects=False,
            )
        assert resp.status_code == 400
        assert "state" in resp.json()["detail"].lower()

    async def test_callback_creates_new_user(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """New SSO user is created and one-time code is returned."""
        _enable_oidc()
        resp = await _do_callback(client)
        assert resp.status_code == 307
        location = resp.headers["location"]
        assert "/sso-callback?code=" in location
        # JWT should NOT be in URL
        assert "token=" not in location

        result = await db_session.execute(select(User).where(User.email == "sso-user@example.com"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.username == "ssouser"
        assert user.sso_provider == "TestIDP"
        assert user.sso_subject_id == "sso-user-123"
        assert user.role == UserRole.viewer

    async def test_callback_links_existing_operator(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Existing non-admin user is linked to SSO."""
        _enable_oidc()
        existing = User(
            email="operator@example.com",
            username="operator_user",
            password_hash=hash_password("password123"),
            role=UserRole.operator,
        )
        db_session.add(existing)
        await db_session.commit()
        await db_session.refresh(existing)

        resp = await _do_callback(client, email="operator@example.com", sub="idp-op-1")
        assert resp.status_code == 307

        await db_session.refresh(existing)
        assert existing.sso_provider == "TestIDP"
        assert existing.sso_subject_id == "idp-op-1"
        assert existing.role == UserRole.operator

    async def test_callback_refuses_admin_auto_link(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Admin accounts cannot be auto-linked via SSO."""
        _enable_oidc()
        admin = User(
            email="admin@example.com",
            username="admin_user",
            password_hash=hash_password("password123"),
            role=UserRole.admin,
        )
        db_session.add(admin)
        await db_session.commit()

        resp = await _do_callback(client, email="admin@example.com", sub="idp-admin-1")
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"].lower()

    async def test_callback_refuses_unverified_email_link(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Unverified email cannot be used to link an existing account."""
        _enable_oidc()
        existing = User(
            email="unverified@example.com",
            username="unverified_user",
            password_hash=hash_password("password123"),
            role=UserRole.viewer,
        )
        db_session.add(existing)
        await db_session.commit()

        resp = await _do_callback(client, email="unverified@example.com", sub="idp-uv", email_verified=False)
        assert resp.status_code == 403
        assert "verified" in resp.json()["detail"].lower()

    async def test_callback_refuses_unverified_email_create(self, client: AsyncClient) -> None:
        """Unverified email cannot be used to create a new account."""
        _enable_oidc()
        resp = await _do_callback(client, email="brand-new@example.com", sub="idp-new", email_verified=False)
        assert resp.status_code == 403
        assert "verified" in resp.json()["detail"].lower()

    async def test_callback_recognizes_returning_sso_user(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """A returning SSO user is matched by sso_subject_id."""
        _enable_oidc()
        sso_user = User(
            email="returning@example.com",
            username="returning_sso",
            password_hash=hash_password("random-password-123"),
            role=UserRole.viewer,
            sso_provider="TestIDP",
            sso_subject_id="returning-sub-456",
        )
        db_session.add(sso_user)
        await db_session.commit()

        resp = await _do_callback(client, email="returning@example.com", sub="returning-sub-456")
        assert resp.status_code == 307
        assert "/sso-callback?code=" in resp.headers["location"]

    async def test_callback_auto_create_disabled(self, client: AsyncClient) -> None:
        """When auto-create is disabled, unknown users get 403."""
        _enable_oidc()
        settings.oidc_auto_create_users = False

        resp = await _do_callback(client, email="noaccount@example.com", sub="no-account-user")
        assert resp.status_code == 403
        assert "automatic user creation" in resp.json()["detail"].lower()

    async def test_callback_no_email_returns_400(self, client: AsyncClient) -> None:
        _enable_oidc()
        from webmacs_backend.api.v1.sso import _create_state_token

        valid_state = _create_state_token("fake-verifier")
        mock_cfg, mock_client_cls, mock_userinfo = _mock_callback_deps()

        with mock_cfg as m_cfg, mock_client_cls as m_cls, mock_userinfo as m_ui:
            m_cfg.return_value = _FAKE_OIDC_CONFIG
            mock_oauth = AsyncMock()
            mock_oauth.fetch_token = AsyncMock(return_value={"access_token": "fake-token"})
            m_cls.return_value = mock_oauth
            m_ui.return_value = {"sub": "no-email-user", "preferred_username": "noemail"}

            resp = await client.get(
                f"/api/v1/auth/sso/callback?code=test-code&state={valid_state}",
                follow_redirects=False,
            )
        assert resp.status_code == 400
        assert "email" in resp.json()["detail"].lower()

    async def test_callback_no_sub_returns_400(self, client: AsyncClient) -> None:
        """Missing 'sub' claim returns 400."""
        _enable_oidc()
        from webmacs_backend.api.v1.sso import _create_state_token

        valid_state = _create_state_token("fake-verifier")
        mock_cfg, mock_client_cls, mock_userinfo = _mock_callback_deps()

        with mock_cfg as m_cfg, mock_client_cls as m_cls, mock_userinfo as m_ui:
            m_cfg.return_value = _FAKE_OIDC_CONFIG
            mock_oauth = AsyncMock()
            mock_oauth.fetch_token = AsyncMock(return_value={"access_token": "fake-token"})
            m_cls.return_value = mock_oauth
            m_ui.return_value = {"email": "nosub@example.com", "email_verified": True}

            resp = await client.get(
                f"/api/v1/auth/sso/callback?code=test-code&state={valid_state}",
                follow_redirects=False,
            )
        assert resp.status_code == 400
        assert "subject" in resp.json()["detail"].lower()

    async def test_callback_token_exchange_failure_returns_502(self, client: AsyncClient) -> None:
        """When the IdP token exchange fails, return 502."""
        _enable_oidc()
        from webmacs_backend.api.v1.sso import _create_state_token

        valid_state = _create_state_token("fake-verifier")

        with (
            patch("webmacs_backend.api.v1.sso._get_oidc_config", new_callable=AsyncMock) as mock_cfg,
            patch("webmacs_backend.api.v1.sso.AsyncOAuth2Client") as mock_client_cls,
        ):
            mock_cfg.return_value = _FAKE_OIDC_CONFIG
            mock_oauth = AsyncMock()
            mock_oauth.fetch_token = AsyncMock(side_effect=Exception("IdP unreachable"))
            mock_client_cls.return_value = mock_oauth

            resp = await client.get(
                f"/api/v1/auth/sso/callback?code=test-code&state={valid_state}",
                follow_redirects=False,
            )
        assert resp.status_code == 502
        assert "exchange" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# One-time code exchange endpoint
# ---------------------------------------------------------------------------


class TestSsoExchange:
    """Tests for POST /api/v1/auth/sso/exchange."""

    async def test_exchange_valid_code(self, client: AsyncClient) -> None:
        """Valid one-time code returns a JWT."""
        from webmacs_backend.api.v1.sso import _create_auth_code

        code = _create_auth_code(user_id=42, role="operator")
        resp = await client.post("/api/v1/auth/sso/exchange", json={"code": code})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["access_token"]  # not empty

    async def test_exchange_invalid_code(self, client: AsyncClient) -> None:
        """Invalid code returns 400."""
        resp = await client.post("/api/v1/auth/sso/exchange", json={"code": "bogus"})
        assert resp.status_code == 400

    async def test_exchange_code_consumed_once(self, client: AsyncClient) -> None:
        """A code can only be used once (single-use)."""
        from webmacs_backend.api.v1.sso import _create_auth_code

        code = _create_auth_code(user_id=42, role="viewer")
        resp1 = await client.post("/api/v1/auth/sso/exchange", json={"code": code})
        assert resp1.status_code == 200

        resp2 = await client.post("/api/v1/auth/sso/exchange", json={"code": code})
        assert resp2.status_code == 400

    async def test_exchange_expired_code(self, client: AsyncClient) -> None:
        """Expired one-time code returns 400."""
        import webmacs_backend.api.v1.sso as sso_module
        from webmacs_backend.api.v1.sso import _create_auth_code

        code = _create_auth_code(user_id=42, role="viewer")
        # Force expiry by setting the timestamp to the past
        user_id, role, _ = sso_module._auth_codes[code]
        sso_module._auth_codes[code] = (user_id, role, 0.0)  # already expired

        resp = await client.post("/api/v1/auth/sso/exchange", json={"code": code})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# State token helpers
# ---------------------------------------------------------------------------


class TestStateToken:
    """Tests for the state JWT helper functions."""

    def test_create_and_verify(self) -> None:
        from webmacs_backend.api.v1.sso import _create_state_token, _verify_state_token

        token = _create_state_token("test-verifier")
        claims = _verify_state_token(token)
        assert claims is not None
        assert claims["cv"] == "test-verifier"
        assert claims["iss"] == "webmacs-sso"

    def test_invalid_token_fails(self) -> None:
        from webmacs_backend.api.v1.sso import _verify_state_token

        assert _verify_state_token("not-a-valid-jwt") is None

    def test_tampered_token_fails(self) -> None:
        from webmacs_backend.api.v1.sso import _create_state_token, _verify_state_token

        token = _create_state_token("verifier")
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        assert _verify_state_token(tampered) is None


# ---------------------------------------------------------------------------
# Username sanitization
# ---------------------------------------------------------------------------


class TestUsernameSanitization:
    """Tests for _sanitize_username."""

    def test_alphanumeric_preserved(self) -> None:
        from webmacs_backend.api.v1.sso import _sanitize_username

        assert _sanitize_username("john.doe", "x@x.com") == "john.doe"

    def test_special_chars_removed(self) -> None:
        from webmacs_backend.api.v1.sso import _sanitize_username

        assert _sanitize_username("j@hn / d<>e", "x@x.com") == "jhnde"

    def test_unicode_removed(self) -> None:
        from webmacs_backend.api.v1.sso import _sanitize_username

        assert _sanitize_username("ünïcödé", "x@x.com") == "ncd"

    def test_fallback_to_email(self) -> None:
        from webmacs_backend.api.v1.sso import _sanitize_username

        assert _sanitize_username(None, "alice@example.com") == "alice"

    def test_empty_generates_random(self) -> None:
        from webmacs_backend.api.v1.sso import _sanitize_username

        result = _sanitize_username("@@@", "@@@.com")
        assert result.startswith("sso_user_")

    def test_truncates_to_50(self) -> None:
        from webmacs_backend.api.v1.sso import _sanitize_username

        long_name = "a" * 100
        assert len(_sanitize_username(long_name, "x@x.com")) == 50


# ---------------------------------------------------------------------------
# Username collision
# ---------------------------------------------------------------------------


class TestUsernameCollision:
    """Test that duplicate usernames get a suffix."""

    async def test_username_dedup_suffix(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """If a username already exists, a hex suffix is appended."""
        _enable_oidc()
        existing = User(
            email="taken@example.com",
            username="ssouser",
            password_hash=hash_password("password123"),
            role=UserRole.viewer,
        )
        db_session.add(existing)
        await db_session.commit()

        resp = await _do_callback(
            client,
            email="new-ssouser@example.com",
            sub="new-sso-id",
            preferred_username="ssouser",
        )
        assert resp.status_code == 307

        result = await db_session.execute(select(User).where(User.email == "new-ssouser@example.com"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.username.startswith("ssouser_")
        assert len(user.username) > len("ssouser_")


# ---------------------------------------------------------------------------
# PKCE
# ---------------------------------------------------------------------------


class TestRequireOidcEnabled:
    """Tests for _require_oidc_enabled guard."""

    async def test_enabled_but_missing_issuer(self, client: AsyncClient) -> None:
        """SSO enabled but missing OIDC_ISSUER_URL returns 500."""
        settings.oidc_enabled = True
        settings.oidc_client_id = "some-client"
        settings.oidc_issuer_url = ""
        resp = await client.get("/api/v1/auth/sso/authorize", follow_redirects=False)
        assert resp.status_code == 500
        assert "OIDC_ISSUER_URL" in resp.json()["detail"]

    async def test_enabled_but_missing_client_id(self, client: AsyncClient) -> None:
        """SSO enabled but missing OIDC_CLIENT_ID returns 500."""
        settings.oidc_enabled = True
        settings.oidc_issuer_url = "https://idp.example.com"
        settings.oidc_client_id = ""
        resp = await client.get("/api/v1/auth/sso/authorize", follow_redirects=False)
        assert resp.status_code == 500
        assert "OIDC_CLIENT_ID" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Frontend URL derivation
# ---------------------------------------------------------------------------


class TestFrontendUrl:
    """Tests for _get_frontend_url."""

    def test_explicit_config(self) -> None:
        from webmacs_backend.api.v1.sso import _get_frontend_url

        settings.oidc_frontend_url = "https://webmacs.example.com/"
        assert _get_frontend_url() == "https://webmacs.example.com"

    def test_cors_origin_fallback(self) -> None:
        from webmacs_backend.api.v1.sso import _get_frontend_url

        settings.oidc_frontend_url = ""
        original = settings.cors_origins
        settings.cors_origins = ["http://localhost:5173"]
        try:
            assert _get_frontend_url() == "http://localhost:5173"
        finally:
            settings.cors_origins = original

    def test_default_fallback(self) -> None:
        from webmacs_backend.api.v1.sso import _get_frontend_url

        settings.oidc_frontend_url = ""
        original = settings.cors_origins
        settings.cors_origins = []
        try:
            assert _get_frontend_url() == "http://localhost:5173"
        finally:
            settings.cors_origins = original


# ---------------------------------------------------------------------------
# OIDC Discovery cache TTL
# ---------------------------------------------------------------------------


class TestOidcDiscoveryCache:
    """Tests for OIDC discovery cache expiry."""

    async def test_cache_refreshes_after_ttl(self) -> None:
        """Discovery config is re-fetched after TTL expires."""
        import webmacs_backend.api.v1.sso as sso_module

        call_count = 0
        original_get = httpx.AsyncClient.get

        async def _fake_get(self: object, url: str, **kwargs: object) -> object:  # type: ignore[override]
            nonlocal call_count
            call_count += 1

            class FakeResp:
                status_code = 200

                def raise_for_status(self) -> None:
                    pass

                def json(self) -> dict[str, object]:
                    return _FAKE_OIDC_CONFIG

            return FakeResp()

        settings.oidc_issuer_url = "https://idp.example.com"
        sso_module._oidc_config_cache = None
        sso_module._oidc_config_cached_at = 0

        with patch.object(httpx.AsyncClient, "get", _fake_get):
            await sso_module._get_oidc_config()
            assert call_count == 1

            # Second call within TTL — should use cache
            await sso_module._get_oidc_config()
            assert call_count == 1

            # Simulate TTL expiry
            sso_module._oidc_config_cached_at = time.monotonic() - sso_module._OIDC_CACHE_TTL - 1
            await sso_module._get_oidc_config()
            assert call_count == 2


# ---------------------------------------------------------------------------
# Userinfo fetch failures
# ---------------------------------------------------------------------------


class TestFetchUserinfo:
    """Tests for _fetch_userinfo edge cases."""

    async def test_userinfo_missing_endpoint_returns_502(self, client: AsyncClient) -> None:
        """Missing userinfo_endpoint in OIDC config returns 502."""
        _enable_oidc()
        from webmacs_backend.api.v1.sso import _create_state_token

        valid_state = _create_state_token("fake-verifier")

        oidc_no_userinfo = {k: v for k, v in _FAKE_OIDC_CONFIG.items() if k != "userinfo_endpoint"}

        with (
            patch("webmacs_backend.api.v1.sso._get_oidc_config", new_callable=AsyncMock) as mock_cfg,
            patch("webmacs_backend.api.v1.sso.AsyncOAuth2Client") as mock_client_cls,
        ):
            mock_cfg.return_value = oidc_no_userinfo
            mock_oauth = AsyncMock()
            mock_oauth.fetch_token = AsyncMock(return_value={"access_token": "fake-token"})
            mock_client_cls.return_value = mock_oauth

            resp = await client.get(
                f"/api/v1/auth/sso/callback?code=test-code&state={valid_state}",
                follow_redirects=False,
            )
        assert resp.status_code == 502
        assert "userinfo" in resp.json()["detail"].lower()

    async def test_userinfo_non_200_returns_502(self, client: AsyncClient) -> None:
        """Non-200 response from userinfo endpoint returns 502."""
        _enable_oidc()
        from webmacs_backend.api.v1.sso import _fetch_userinfo

        class FakeResp:
            status_code = 403
            text = "Forbidden"

        with patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=FakeResp())):
            with pytest.raises(HTTPException) as exc_info:
                await _fetch_userinfo(_FAKE_OIDC_CONFIG, {"access_token": "bad-token"})
            assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# PKCE
# ---------------------------------------------------------------------------


class TestPkce:
    """Tests for PKCE helper."""

    def test_generate_pkce(self) -> None:
        from webmacs_backend.api.v1.sso import _generate_pkce

        verifier, challenge = _generate_pkce()
        assert len(verifier) > 40
        assert len(challenge) > 20
        # Verify challenge is S256 of verifier
        import base64
        import hashlib

        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        assert challenge == expected
