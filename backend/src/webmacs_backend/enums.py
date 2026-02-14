"""Shared enums — single source of truth for both ORM models and Pydantic schemas."""

from __future__ import annotations

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


class WebhookEventType(StrEnum):
    """Webhook subscribable event types."""

    sensor_threshold_exceeded = "sensor.threshold_exceeded"
    sensor_reading = "sensor.reading"
    experiment_started = "experiment.started"
    experiment_stopped = "experiment.stopped"
    system_health_changed = "system.health_changed"


class WebhookDeliveryStatus(StrEnum):
    """Status of a webhook delivery attempt."""

    pending = "pending"
    delivered = "delivered"
    failed = "failed"
    dead_letter = "dead_letter"


class RuleOperator(StrEnum):
    """Comparison operators for rule evaluation."""

    gt = "gt"
    lt = "lt"
    eq = "eq"
    gte = "gte"
    lte = "lte"
    between = "between"
    not_between = "not_between"


class RuleActionType(StrEnum):
    """Action to take when a rule triggers."""

    webhook = "webhook"
    log = "log"


class UpdateStatus(StrEnum):
    """Firmware update lifecycle status."""

    pending = "pending"
    downloading = "downloading"
    verifying = "verifying"
    applying = "applying"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"


class WidgetType(StrEnum):
    """Dashboard widget types."""

    line_chart = "line_chart"
    gauge = "gauge"
    stat_card = "stat_card"
    actuator_toggle = "actuator_toggle"


class PluginStatus(StrEnum):
    """Plugin instance lifecycle status."""

    inactive = "inactive"
    connected = "connected"
    error = "error"
    demo = "demo"


class ChannelDirection(StrEnum):
    """Channel data-flow direction."""

    input = "input"
    output = "output"
    bidirectional = "bidirectional"


class PluginSource(StrEnum):
    """How a plugin package was installed."""

    bundled = "bundled"
    uploaded = "uploaded"
