"""Controller configuration using pydantic-settings."""

from __future__ import annotations

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class ControllerSettings(BaseSettings):
    """Controller configuration loaded from environment or .env file."""

    # Environment
    env: str = Field(default="development", alias="WEBMACS_ENV")

    # Backend connection
    server_url: str = Field(default="http://localhost", alias="WEBMACS_SERVER_URL")
    server_port: int = Field(default=8000, alias="WEBMACS_SERVER_PORT")

    # Authentication
    admin_email: str = Field(default="", alias="WEBMACS_ADMIN_EMAIL")
    admin_password: str = Field(default="", alias="WEBMACS_ADMIN_PASSWORD")

    # Timing
    poll_interval: float = Field(default=0.1, alias="WEBMACS_POLL_INTERVAL")
    request_timeout: float = Field(default=30.0, alias="WEBMACS_REQUEST_TIMEOUT")
    event_round_digit: int = 2

    # Telemetry transport (http | websocket)
    telemetry_mode: str = Field(default="http", alias="WEBMACS_TELEMETRY_MODE")

    # Rule engine
    rule_event_id: str = Field(default="", alias="WEBMACS_RULE_EVENT_ID")

    # RevPi mapping (JSON string from env, parsed to dict)
    revpi_mapping: dict[str, Any] = Field(default_factory=dict, alias="WEBMACS_REVPI_MAPPING")

    # Sentry
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    # API paths
    api_prefix: str = "/api/v1"
    path_login: str = "/auth/login"
    path_events: str = "/events"
    path_datapoints_latest: str = "/datapoints/latest"
    path_datapoints_batch: str = "/datapoints/batch"

    @property
    def base_url(self) -> str:
        return f"{self.server_url}:{self.server_port}{self.api_prefix}"

    @property
    def ws_url(self) -> str:
        """WebSocket URL for telemetry endpoint."""
        scheme = "wss" if self.server_url.startswith("https") else "ws"
        host = self.server_url.replace("http://", "").replace("https://", "")
        return f"{scheme}://{host}:{self.server_port}/ws/controller/telemetry"

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "populate_by_name": True}


settings = ControllerSettings()
