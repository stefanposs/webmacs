"""Shared enums — single source of truth for both ORM models and Pydantic schemas."""

from enum import StrEnum


class EventType(StrEnum):
    """Event type classification."""

    sensor = "sensor"
    actuator = "actuator"
    range = "range"
    cmd_button = "cmd_button"
    cmd_opened = "cmd_opened"
    cmd_closed = "cmd_closed"


class StatusType(StrEnum):
    """Log entry read status."""

    read = "read"
    unread = "unread"


class LoggingType(StrEnum):
    """Log severity level."""

    error = "error"
    warning = "warning"
    info = "info"
