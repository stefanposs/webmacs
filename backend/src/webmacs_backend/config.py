"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


settings = Settings()
