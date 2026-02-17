"""OIDC / SSO authentication endpoints.

Implements the Authorization Code flow with a generic OIDC provider.
The backend acts as an OAuth2 client — the frontend never sees the
``client_secret`` or raw ID token.

Flow:
    1. ``GET  /sso/config``    → returns public SSO metadata (enabled? provider name)
    2. ``GET  /sso/authorize`` → redirects to the OIDC provider
    3. ``GET  /sso/callback``  → exchanges code, finds/creates local user,
       issues a single-use auth code and redirects to the frontend
    4. ``POST /sso/exchange``  → frontend exchanges the one-time code for a JWT

Security features:
    - Signed state JWT for CSRF protection
    - One-time authorization code exchange (JWT never appears in URLs)
    - ``email_verified`` claim enforcement
    - Admin account auto-linking is refused (requires manual linking)
    - Username sanitization via regex allowlist
    - PKCE (S256) for defense-in-depth
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import re
import secrets
import time
from typing import TYPE_CHECKING

import httpx
import structlog
from authlib.integrations.httpx_client import AsyncOAuth2Client  # type: ignore[import-untyped]
from authlib.jose import jwt as authlib_jwt  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from webmacs_backend.config import settings
from webmacs_backend.database import get_db
from webmacs_backend.enums import UserRole
from webmacs_backend.models import User
from webmacs_backend.schemas import SsoConfigResponse
from webmacs_backend.security import create_access_token, hash_password
from webmacs_backend.services.log_service import create_log

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter()

# ─── OIDC discovery cache (TTL-based) ───────────────────────────────────────

_oidc_config_cache: dict[str, object] | None = None
_oidc_config_cached_at: float = 0
_OIDC_CACHE_TTL: float = 3600  # 1 hour


async def _get_oidc_config() -> dict[str, object]:
    """Fetch and cache the OIDC provider's ``.well-known/openid-configuration``.

    The cache expires after ``_OIDC_CACHE_TTL`` seconds so endpoint/key
    rotations at the IdP are picked up without a restart.
    """
    global _oidc_config_cache, _oidc_config_cached_at  # noqa: PLW0603
    now = time.monotonic()
    if _oidc_config_cache is not None and (now - _oidc_config_cached_at) < _OIDC_CACHE_TTL:
        return _oidc_config_cache

    discovery_url = settings.oidc_issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(discovery_url, timeout=10)
        resp.raise_for_status()
        _oidc_config_cache = resp.json()  # type: ignore[assignment]
    _oidc_config_cached_at = now
    logger.info("oidc_discovery_loaded", issuer=settings.oidc_issuer_url)
    return _oidc_config_cache  # type: ignore[return-value]


def _require_oidc_enabled() -> None:
    """Raise 404 when OIDC is not configured."""
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO is not enabled.")
    if not settings.oidc_issuer_url or not settings.oidc_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SSO is enabled but OIDC_ISSUER_URL or OIDC_CLIENT_ID is missing.",
        )


# ─── State JWT helpers (stateless CSRF protection) ─────────────────────────

_STATE_ALGORITHM = "HS256"
_STATE_TTL_SECONDS = 600  # 10 minutes


def _create_state_token(code_verifier: str) -> str:
    """Create a signed, time-limited state token (prevents CSRF).

    Embeds the PKCE ``code_verifier`` so it survives the redirect round-trip
    without server-side session storage.
    """
    now = datetime.datetime.now(datetime.UTC)
    payload = {
        "iss": "webmacs-sso",
        "nonce": secrets.token_urlsafe(16),
        "cv": code_verifier,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(seconds=_STATE_TTL_SECONDS)).timestamp()),
    }
    header = {"alg": _STATE_ALGORITHM}
    token: bytes = authlib_jwt.encode(header, payload, settings.secret_key)
    return token.decode("utf-8")


def _verify_state_token(state: str) -> dict[str, object] | None:
    """Verify a state token and return claims, or None on failure."""
    try:
        claims = authlib_jwt.decode(state, settings.secret_key)
        claims.validate()
        return dict(claims)
    except Exception:
        return None


# ─── One-time auth code store (in-memory, short-lived) ─────────────────────

_AUTH_CODE_TTL_SECONDS = 60  # 1 minute
_auth_codes: dict[str, tuple[int, str, float]] = {}  # code -> (user_id, role, expires_at)


def _create_auth_code(user_id: int, role: str) -> str:
    """Create a short-lived, single-use authorization code."""
    code = secrets.token_urlsafe(48)
    _auth_codes[code] = (user_id, role, time.monotonic() + _AUTH_CODE_TTL_SECONDS)
    # Cleanup expired codes (lazy)
    _cleanup_auth_codes()
    return code


def _consume_auth_code(code: str) -> tuple[int, str] | None:
    """Consume (delete) an auth code and return (user_id, role) or None."""
    entry = _auth_codes.pop(code, None)
    if entry is None:
        return None
    user_id, role, expires_at = entry
    if time.monotonic() > expires_at:
        return None
    return user_id, role


def _cleanup_auth_codes() -> None:
    """Remove expired auth codes."""
    now = time.monotonic()
    expired = [k for k, (_, _, exp) in _auth_codes.items() if now > exp]
    for k in expired:
        _auth_codes.pop(k, None)


# ─── PKCE helpers ───────────────────────────────────────────────────────────


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# ─── Build OAuth2 client ────────────────────────────────────────────────────


def _build_oauth_client(oidc_cfg: dict[str, object]) -> AsyncOAuth2Client:
    """Create a configured ``AsyncOAuth2Client``."""
    return AsyncOAuth2Client(
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret or None,
        scope=settings.oidc_scopes,
        token_endpoint=str(oidc_cfg["token_endpoint"]),
        redirect_uri=_get_redirect_uri(),
    )


def _get_redirect_uri() -> str:
    """Return the configured redirect URI for the OIDC callback."""
    if settings.oidc_redirect_uri:
        return settings.oidc_redirect_uri
    # Fallback: derive from backend host/port
    scheme = "https" if settings.env == "production" else "http"
    host = settings.backend_host if settings.backend_host != "0.0.0.0" else "localhost"
    return f"{scheme}://{host}:{settings.backend_port}/api/v1/auth/sso/callback"


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.get("/config", response_model=SsoConfigResponse)
async def sso_config() -> SsoConfigResponse:
    """Return public SSO configuration (no secrets exposed)."""
    if not settings.oidc_enabled:
        return SsoConfigResponse(enabled=False, provider_name="", authorize_url="")

    return SsoConfigResponse(
        enabled=True,
        provider_name=settings.oidc_provider_name,
        authorize_url="/api/v1/auth/sso/authorize",
    )


@router.get("/authorize")
async def sso_authorize() -> RedirectResponse:
    """Start the OIDC Authorization Code flow with PKCE.

    Redirects the browser to the identity provider's authorize endpoint.
    """
    _require_oidc_enabled()

    oidc_cfg = await _get_oidc_config()
    authorize_endpoint = str(oidc_cfg["authorization_endpoint"])

    # Generate PKCE pair and embed verifier in state token
    code_verifier, code_challenge = _generate_pkce()
    state = _create_state_token(code_verifier)

    client = _build_oauth_client(oidc_cfg)
    authorization_url, _ = client.create_authorization_url(
        authorize_endpoint,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    logger.debug("sso_authorize_redirect", provider=settings.oidc_provider_name)
    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def sso_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle the OIDC callback after the user authenticated at the IdP.

    Exchanges the authorization code for tokens, extracts user information,
    creates or links the local user, and redirects to the frontend with a
    single-use authorization code (NOT the JWT directly).
    """
    _require_oidc_enabled()

    # ── Validate state ──────────────────────────────────────────────────
    state_claims = _verify_state_token(state)
    if state_claims is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired SSO state.")

    code_verifier = str(state_claims.get("cv", ""))

    # ── Exchange code for tokens (with PKCE) ────────────────────────────
    oidc_cfg = await _get_oidc_config()
    client = _build_oauth_client(oidc_cfg)

    try:
        token_response = await client.fetch_token(
            str(oidc_cfg["token_endpoint"]),
            code=code,
            grant_type="authorization_code",
            code_verifier=code_verifier,
        )
    except Exception as exc:
        logger.error("sso_token_exchange_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with identity provider.",
        ) from exc

    # ── Extract user info ───────────────────────────────────────────────
    userinfo = await _fetch_userinfo(oidc_cfg, token_response)

    email: str | None = str(userinfo["email"]) if "email" in userinfo else None
    sub: str | None = str(userinfo["sub"]) if "sub" in userinfo else None
    preferred_username: str | None = str(userinfo.get("preferred_username") or userinfo.get("name") or "") or None
    email_verified: bool = bool(userinfo.get("email_verified", False))

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identity provider did not return an email address. "
            "Ensure the 'email' scope is requested and the user has a verified email.",
        )
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identity provider did not return a subject identifier.",
        )

    # ── Find or create local user ───────────────────────────────────────
    user = await _find_or_create_sso_user(
        db,
        email=email,
        sso_subject_id=sub,
        sso_provider=settings.oidc_provider_name,
        preferred_username=preferred_username,
        email_verified=email_verified,
    )

    # ── Issue one-time auth code & redirect ─────────────────────────────
    auth_code = _create_auth_code(user.id, user.role.value)
    await create_log(db, f"User '{user.username}' logged in via SSO ({settings.oidc_provider_name}).", user.public_id)
    await db.commit()

    frontend_url = _get_frontend_url()
    redirect_target = f"{frontend_url}/sso-callback?code={auth_code}"
    logger.info("sso_login_success", user=user.username, provider=settings.oidc_provider_name)
    return RedirectResponse(url=redirect_target)


class SsoExchangeRequest(BaseModel):
    """Request body for the one-time code exchange."""

    code: str


class SsoExchangeResponse(BaseModel):
    """Response from the one-time code exchange."""

    access_token: str


@router.post("/exchange", response_model=SsoExchangeResponse)
async def sso_exchange(request: SsoExchangeRequest) -> SsoExchangeResponse:
    """Exchange a single-use SSO auth code for a WebMACS JWT.

    The one-time code was issued during ``/callback`` and is valid for
    60 seconds. This keeps the JWT out of URLs, browser history, and
    server access logs.
    """
    result = _consume_auth_code(request.code)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired SSO authorization code.",
        )

    user_id, role = result
    access_token = create_access_token(user_id, role=role)
    return SsoExchangeResponse(access_token=access_token)


# ─── Helpers ────────────────────────────────────────────────────────────────


async def _fetch_userinfo(oidc_cfg: dict[str, object], token_response: dict[str, object]) -> dict[str, object]:
    """Fetch user info from the OIDC userinfo endpoint."""
    userinfo_endpoint = str(oidc_cfg.get("userinfo_endpoint", ""))
    if not userinfo_endpoint:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Identity provider does not expose a userinfo endpoint.",
        )

    access_token = token_response.get("access_token", "")
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error("sso_userinfo_failed", status=resp.status_code, body=resp.text[:500])
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch user information from identity provider.",
            )
        return resp.json()  # type: ignore[no-any-return]


async def _find_or_create_sso_user(
    db: AsyncSession,
    *,
    email: str,
    sso_subject_id: str,
    sso_provider: str,
    preferred_username: str | None,
    email_verified: bool,
) -> User:
    """Find an existing user by SSO subject or email, or create a new one."""
    # 1. Try by SSO subject ID (most specific — returning user)
    result = await db.execute(
        select(User).where(User.sso_provider == sso_provider, User.sso_subject_id == sso_subject_id)
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    # 2. Try by email (link existing local account)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        # Security: require email_verified from IdP before linking
        if not email_verified:
            logger.warning("sso_link_refused_unverified", email=email, provider=sso_provider)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot link SSO account: the identity provider has not verified this email address.",
            )
        # Security: refuse auto-linking for admin accounts
        if user.role == UserRole.admin:
            logger.warning("sso_admin_link_refused", email=email, provider=sso_provider)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot automatically link an admin account to SSO. "
                "An administrator must manually link this account.",
            )
        # Link the local account to the SSO provider
        user.sso_provider = sso_provider
        user.sso_subject_id = sso_subject_id
        logger.info("sso_account_linked", email=email, provider=sso_provider)
        return user

    # 3. Auto-create
    if not settings.oidc_auto_create_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No local account found and automatic user creation is disabled. "
            "Ask an administrator to create your account first.",
        )

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create account: the identity provider has not verified this email address.",
        )

    default_role = UserRole(settings.oidc_default_role)
    username = _sanitize_username(preferred_username, email)

    # Ensure username uniqueness
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        username = f"{username}_{secrets.token_hex(3)}"

    new_user = User(
        email=email,
        username=username,
        password_hash=hash_password(secrets.token_urlsafe(32)),  # random pw for SSO-only
        role=default_role,
        sso_provider=sso_provider,
        sso_subject_id=sso_subject_id,
    )
    db.add(new_user)
    await db.flush()  # get the ID
    logger.info("sso_user_created", email=email, username=username, provider=sso_provider, role=default_role.value)
    return new_user


# ─── Username sanitization ──────────────────────────────────────────────────

_USERNAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _sanitize_username(preferred_username: str | None, email: str) -> str:
    """Derive a safe username from the OIDC preferred_username or email.

    Only alphanumeric characters, dots, hyphens, and underscores are kept.
    """
    raw = ""
    if preferred_username:
        raw = preferred_username.strip()
    if not raw:
        raw = email.split("@", maxsplit=1)[0].strip()
    sanitized = _USERNAME_RE.sub("", raw)[:50]
    return sanitized or f"sso_user_{secrets.token_hex(3)}"


def _get_frontend_url() -> str:
    """Return the frontend URL for post-SSO redirect.

    Uses the dedicated ``OIDC_FRONTEND_URL`` setting, falling back to the
    first CORS origin.  Never derived from user input.
    """
    if settings.oidc_frontend_url:
        return settings.oidc_frontend_url.rstrip("/")
    if settings.cors_origins:
        return settings.cors_origins[0].rstrip("/")
    return "http://localhost:5173"
