"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from webmacs_backend.dependencies import CurrentUser, DbSession
from webmacs_backend.models import BlacklistToken, User
from webmacs_backend.schemas import LoginRequest, LoginResponse, StatusResponse, UserResponse
from webmacs_backend.security import create_access_token, verify_password
from webmacs_backend.services.log_service import create_log

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

# Simple in-memory failed-login tracker (per email). This is intentionally
# lightweight — it provides basic throttling in single-process setups.
_FAILED_LOGINS: dict[str, tuple[int, float]] = {}
_MAX_FAILED = 5
_WINDOW_SEC = 300


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: DbSession, http_request: Request) -> LoginResponse:
    """Authenticate user and return JWT token."""
    # Basic rate limit: per-email failed attempts window
    now = __import__("time").time()
    failed_count, first_ts = _FAILED_LOGINS.get(body.email, (0, 0.0))
    if failed_count >= _MAX_FAILED and (now - first_ts) < _WINDOW_SEC:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed login attempts.")

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        # Increment failed counter (reset when window expired)
        if (now - first_ts) > _WINDOW_SEC:
            _FAILED_LOGINS[body.email] = (1, now)
        else:
            _FAILED_LOGINS[body.email] = (failed_count + 1, first_ts or now)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    # Successful login — clear failure counter and issue token
    if body.email in _FAILED_LOGINS:
        _FAILED_LOGINS.pop(body.email, None)

    token = create_access_token(user.id, role=user.role.value)
    await create_log(db, f"User '{user.username}' logged in.", user.public_id)
    return LoginResponse(access_token=token, public_id=user.public_id, username=user.username)


@router.post("/logout", response_model=StatusResponse)
async def logout(
    current_user: CurrentUser,
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> StatusResponse:
    """Blacklist the current token."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials.")
    # Persist the blacklist entry and record a log entry for auditing.
    blacklist_entry = BlacklistToken(token=credentials.credentials)
    db.add(blacklist_entry)
    await db.flush()
    await create_log(db, f"User '{current_user.username}' logged out.", current_user.public_id)
    return StatusResponse(status="success", message="Successfully logged out.")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)
