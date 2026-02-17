"""FastAPI dependencies for authentication, RBAC, and database access."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from webmacs_backend.database import get_db
from webmacs_backend.enums import UserRole
from webmacs_backend.models import ApiToken, BlacklistToken, User
from webmacs_backend.security import (
    API_TOKEN_PREFIX,
    InvalidTokenError,
    decode_access_token,
    hash_api_token,
)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Extract and validate JWT or API token, return the current user."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # ── API Token path (prefixed with wm_) ──────────────────────────────
    if token.startswith(API_TOKEN_PREFIX):
        token_hash = hash_api_token(token)
        result = await db.execute(select(ApiToken).where(ApiToken.token_hash == token_hash))
        api_token = result.scalar_one_or_none()
        if not api_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token.")

        # Check expiry
        if api_token.expires_at and api_token.expires_at < datetime.datetime.now(datetime.UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API token has expired.")

        # Update last_used_at (fire-and-forget, don't block)
        await db.execute(
            update(ApiToken).where(ApiToken.id == api_token.id).values(last_used_at=datetime.datetime.now(datetime.UTC))
        )

        user_result = await db.execute(select(User).where(User.id == api_token.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token owner not found.")
        return user

    # ── JWT path ────────────────────────────────────────────────────────
    # Check blacklist
    blacklist_result = await db.execute(select(BlacklistToken).where(BlacklistToken.token == token))
    if blacklist_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked.")

    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from None

    user_result = await db.execute(select(User).where(User.id == payload.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    return user


def _require_role(*allowed: UserRole):
    """Factory that returns a dependency requiring at least *min_role*."""

    async def _guard(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed and not any(current_user.role.has_at_least(r) for r in allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(r.value for r in allowed)}",
            )
        return current_user

    return _guard


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require admin role."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required.")
    return current_user


async def get_operator_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require at least operator role (operator or admin)."""
    if not current_user.role.has_at_least(UserRole.operator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator privileges required.")
    return current_user


async def get_viewer_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require at least viewer role (any authenticated user)."""
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
OperatorUser = Annotated[User, Depends(get_operator_user)]
ViewerUser = Annotated[User, Depends(get_viewer_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
