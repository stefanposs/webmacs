"""Security utilities — password hashing, token creation/decoding."""

import datetime
from dataclasses import dataclass

import bcrypt
from jose import JWTError, jwt  # type: ignore[import-untyped]

from webmacs_backend.config import settings


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid or expired."""


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Decoded token data."""

    user_id: int
    exp: datetime.datetime


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(user_id: int) -> str:
    """Create a JWT access token."""
    now = datetime.datetime.now(datetime.UTC)
    expire = now + datetime.timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "iat": now}
    encoded: str = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return encoded


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token. Raises InvalidTokenError on failure."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as e:
        raise InvalidTokenError("Invalid or expired token") from e

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise InvalidTokenError("Token missing 'sub' claim")

    return TokenPayload(user_id=int(user_id_str), exp=payload["exp"])
