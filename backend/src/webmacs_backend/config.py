"""Application configuration using pydantic-settings."""

from __future__ import annotations

import structlog
from pydantic_settings import BaseSettings

logger = structlog.get_logger()

_MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://webmacs:webmacs@localhost:5432/webmacs"

    # Security
    secret_key: str = ""  # MUST be set in production
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    debug: bool = False

    env: str = "development"  # "development" or "production"

    # Storage backend (postgresql|timescale)
    storage_backend: str = "postgresql"

    # Sentry
    sentry_dsn: str = ""

    # WebSocket
    ws_heartbeat_interval: int = 30

    # Timezone
    timezone: str = "Europe/Berlin"

    # Initial admin user (seeded on first start)
    initial_admin_email: str = "admin@webmacs.io"
    initial_admin_username: str = "admin"
    initial_admin_password: str = "admin123"

    # Rate limiting
    rate_limit_per_minute: int = 300

    # GitHub releases (for OTA update checks)
    github_repo: str = "stefanposs/webmacs"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


settings = Settings()


class WeakSecretKeyError(Exception):
    """Raised when SECRET_KEY is missing or too short in production."""


def validate_secret_key() -> None:
    """Validate that SECRET_KEY is acceptable for the current environment.

    - Production (``ENV=production``): raises :class:`WeakSecretKeyError` if
      SECRET_KEY is empty or shorter than 32 characters.
    - Development: logs a WARNING for weak keys but does not raise.
    """
    is_production = settings.env.lower() == "production"

    key = settings.secret_key.strip()

    if not key:
        if is_production:
            raise WeakSecretKeyError(
                "SECRET_KEY must be set in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )
        logger.warning("secret_key_missing", hint="SECRET_KEY is empty — acceptable for development only")
        return

    if len(key) < _MIN_SECRET_KEY_LENGTH:
        if is_production:
            raise WeakSecretKeyError(
                f"SECRET_KEY must be at least {_MIN_SECRET_KEY_LENGTH} characters in production (currently {len(key)})."
            )
        logger.warning(
            "secret_key_weak",
            length=len(key),
            min_required=_MIN_SECRET_KEY_LENGTH,
            hint="Weak SECRET_KEY — acceptable for development only",
        )
