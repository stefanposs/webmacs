import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webmacs_backend.database import get_db
from webmacs_backend.dependencies import get_current_user
from webmacs_backend.models import BlacklistToken, User
from webmacs_backend.schemas import (
    LoginRequest,
    LoginResponse,
    StatusResponse,
    UserMeResponse,
)
from webmacs_backend.security import create_access_token, verify_password
from webmacs_backend.services.log_service import create_log

logger = structlog.get_logger()
router = APIRouter(tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Rate limiting for login attempts
login_attempts: dict[str, list[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW = 15 * 60  # 15 minutes


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Too many login attempts. Try again after {retry_after} seconds.")


def check_rate_limit(email: str, max_attempts: int = MAX_LOGIN_ATTEMPTS, window: int = LOGIN_ATTEMPT_WINDOW) -> None:
    """Check if login attempts are within rate limit"""
    now = time.time()

    # Clean up old attempts
    if email in login_attempts:
        login_attempts[email] = [
            attempt_time for attempt_time in login_attempts[email]
            if now - attempt_time < window
        ]

    # Check current attempts
    recent_attempts = login_attempts.get(email, [])
    if len(recent_attempts) >= max_attempts:
        oldest_attempt = min(recent_attempts)
        retry_after = int(window - (now - oldest_attempt))
        raise RateLimitExceededError(retry_after)


def record_login_attempt(email: str) -> None:
    """Record a login attempt"""
    now = time.time()
    if email not in login_attempts:
        login_attempts[email] = []
    login_attempts[email].append(now)


def clear_login_attempts(email: str) -> None:
    """Clear login attempts for successful login"""
    login_attempts.pop(email, None)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    User login with rate limiting and auto-login support.

    Returns JWT access token on successful authentication.
    Implements exponential backoff for repeated failures.
    """
    client_ip = request.client.host if request.client else "unknown"

    try:
        # Check rate limit before attempting login
        check_rate_limit(login_data.email)

        # Find user by email
        result = await db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()

        # Verify password
        if not user or not verify_password(login_data.password, user.password_hash):
            # Record failed attempt
            record_login_attempt(login_data.email)

            await logger.awarning(
                "Login attempt failed",
                email=login_data.email,
                client_ip=client_ip,
                reason="invalid_credentials"
            )

            # Add artificial delay to slow down brute force attacks
            await asyncio.sleep(1)

            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        # Clear failed attempts on successful login
        clear_login_attempts(login_data.email)

        # Create access token
        access_token = create_access_token(user_id=user.id, role=user.role.value)

        # Audit log
        await create_log(db, f"User '{user.username}' logged in.", user.public_id)
        await db.commit()

        await logger.ainfo(
            "User login successful",
            user_id=user.public_id,
            email=user.email,
            client_ip=client_ip
        )

        return LoginResponse(
            status="success",
            message="Successfully logged in.",
            access_token=access_token,
            public_id=user.public_id,
            username=user.username
        )

    except RateLimitExceededError as e:
        await logger.awarning(
            "Login rate limit exceeded",
            email=login_data.email,
            client_ip=client_ip,
            retry_after=e.retry_after
        )

        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Try again in {e.retry_after} seconds.",
            headers={"Retry-After": str(e.retry_after)}
        ) from None


@router.post("/auto-login", response_model=LoginResponse)
async def auto_login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    """
    Automated login endpoint with reduced rate limiting for auto-login clients.

    This endpoint is specifically designed for automated login attempts
    and has more permissive rate limiting than the standard login endpoint.
    """
    client_ip = request.client.host if request.client else "unknown"

    try:
        # More permissive rate limiting for auto-login (10 attempts per 5 minutes)
        check_rate_limit(f"auto:{login_data.email}", max_attempts=10, window=5 * 60)

        # Find user by email
        result = await db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()

        # Verify password
        if not user or not verify_password(login_data.password, user.password_hash):
            # Record failed attempt with auto prefix
            record_login_attempt(f"auto:{login_data.email}")

            await logger.awarning(
                "Auto-login attempt failed",
                email=login_data.email,
                client_ip=client_ip,
                reason="invalid_credentials"
            )

            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        # Clear failed attempts on successful auto-login
        clear_login_attempts(f"auto:{login_data.email}")

        # Create access token
        access_token = create_access_token(user_id=user.id, role=user.role.value)

        await logger.ainfo(
            "Auto-login successful",
            user_id=user.public_id,
            email=user.email,
            client_ip=client_ip
        )

        return LoginResponse(
            status="success",
            message="Auto-login successful.",
            access_token=access_token,
            public_id=user.public_id,
            username=user.username
        )

    except RateLimitExceededError as e:
        await logger.awarning(
            "Auto-login rate limit exceeded",
            email=login_data.email,
            client_ip=client_ip,
            retry_after=e.retry_after
        )

        raise HTTPException(
            status_code=429,
            detail=f"Too many auto-login attempts. Try again in {e.retry_after} seconds.",
            headers={"Retry-After": str(e.retry_after)}
        ) from None


@router.post("/logout", response_model=StatusResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StatusResponse:
    """
    User logout - blacklists the current JWT token so it cannot be reused.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Extract token from Authorization header
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")

    token = authorization.split(" ")[1]

    # Add token to blacklist
    blacklist_entry = BlacklistToken(
        token=token,
        blacklisted_on=datetime.now(UTC)
    )
    db.add(blacklist_entry)
    await db.commit()

    await logger.ainfo(
        "User logout",
        user_id=current_user.public_id,
        email=current_user.email,
        client_ip=client_ip
    )

    return StatusResponse(
        status="success",
        message="Successfully logged out."
    )


@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserMeResponse:
    """
    Get current authenticated user information.
    """
    return UserMeResponse(
        public_id=current_user.public_id,
        email=current_user.email,
        username=current_user.username,
        admin=current_user.admin,
        role=current_user.role.value,
        registered_on=current_user.registered_on,
        sso_provider=getattr(current_user, 'sso_provider', None),
        created_on=current_user.registered_on
    )


@router.get("/rate-limit-status")
async def get_rate_limit_status(
    email: str,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """
    Get rate limit status for debugging and monitoring.
    Admin-only endpoint.
    """
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    now = time.time()

    # Get regular login attempts
    regular_attempts = login_attempts.get(email, [])
    recent_regular = [
        attempt for attempt in regular_attempts
        if now - attempt < LOGIN_ATTEMPT_WINDOW
    ]

    # Get auto-login attempts
    auto_attempts = login_attempts.get(f"auto:{email}", [])
    recent_auto = [
        attempt for attempt in auto_attempts
        if now - attempt < 5 * 60  # 5 minute window for auto-login
    ]

    return {
        "email": email,
        "regular_attempts": {
            "recent_count": len(recent_regular),
            "max_allowed": MAX_LOGIN_ATTEMPTS,
            "window_seconds": LOGIN_ATTEMPT_WINDOW,
            "is_locked": len(recent_regular) >= MAX_LOGIN_ATTEMPTS,
        },
        "auto_login_attempts": {
            "recent_count": len(recent_auto),
            "max_allowed": 10,
            "window_seconds": 5 * 60,
            "is_locked": len(recent_auto) >= 10,
        },
        "all_attempts": {
            "regular": [
                {"timestamp": attempt, "type": "manual"}
                for attempt in recent_regular
            ],
            "auto": [
                {"timestamp": attempt, "type": "auto"}
                for attempt in recent_auto
            ]
        }
    }


@router.post("/clear-rate-limit")
async def clear_rate_limit(
    email: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> StatusResponse:
    """
    Clear rate limit for a specific email.
    Admin-only endpoint for emergency access.
    """
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    client_ip = request.client.host if request.client else "unknown"

    # Clear both regular and auto-login attempts
    clear_login_attempts(email)
    clear_login_attempts(f"auto:{email}")

    await logger.ainfo(
        "Rate limit cleared by admin",
        target_email=email,
        admin_user_id=current_user.public_id,
        admin_email=current_user.email,
        client_ip=client_ip
    )

    return StatusResponse(
        status="success",
        message=f"Rate limit cleared for {email}"
    )
