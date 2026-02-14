"""SQLAlchemy ORM models."""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from webmacs_backend.database import Base
from webmacs_backend.enums import (
    ChannelDirection,
    EventType,
    LoggingType,
    PluginSource,
    PluginStatus,
    RuleActionType,
    RuleOperator,
    StatusType,
    UpdateStatus,
    WebhookDeliveryStatus,
    WidgetType,
)


class User(Base):
    """User model for authentication and ownership."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    events: Mapped[list[Event]] = relationship(back_populates="user", cascade="all, delete-orphan")
    experiments: Mapped[list[Experiment]] = relationship(back_populates="user", cascade="all, delete-orphan")
    log_entries: Mapped[list[LogEntry]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Event(Base):
    """Event model - represents a sensor or actuator channel."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    min_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"), index=True)

    # Relationships
    user: Mapped[User] = relationship(back_populates="events")
    datapoints: Mapped[list[Datapoint]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Experiment(Base):
    """Experiment model - a time-bounded measurement session."""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    started_on: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    stopped_on: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"), index=True)

    # Relationships
    user: Mapped[User] = relationship(back_populates="experiments")
    datapoints: Mapped[list[Datapoint]] = relationship(back_populates="experiment", cascade="all, delete-orphan")


class Datapoint(Base):
    """Datapoint model - a single sensor/actuator measurement."""

    __tablename__ = "datapoints"
    __table_args__ = (Index("ix_datapoints_event_ts", "event_public_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    event_public_id: Mapped[str] = mapped_column(String, ForeignKey("events.public_id"), index=True)
    experiment_public_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("experiments.public_id"),
        nullable=True,
        index=True,
    )

    # Relationships
    event: Mapped[Event] = relationship(back_populates="datapoints")
    experiment: Mapped[Experiment | None] = relationship(back_populates="datapoints")


class BlacklistToken(Base):
    """Blacklisted JWT tokens for logout."""

    __tablename__ = "blacklist_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    blacklisted_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LogEntry(Base):
    """Application log entry model."""

    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    logging_type: Mapped[LoggingType | None] = mapped_column(Enum(LoggingType), nullable=True)
    status_type: Mapped[StatusType] = mapped_column(Enum(StatusType), default=StatusType.unread)
    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"), index=True)

    # Relationships
    user: Mapped[User] = relationship(back_populates="log_entries")


class Webhook(Base):
    """Webhook subscription — delivers payloads to external URLs on events."""

    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    events: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array of WebhookEventType values
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"), index=True)

    # Relationships
    user: Mapped[User] = relationship()
    deliveries: Mapped[list[WebhookDelivery]] = relationship(back_populates="webhook", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    """Record of a single webhook delivery attempt (including dead letters)."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    webhook_id: Mapped[int] = mapped_column(Integer, ForeignKey("webhooks.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON payload
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        Enum(WebhookDeliveryStatus), default=WebhookDeliveryStatus.pending
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    delivered_on: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    webhook: Mapped[Webhook] = relationship(back_populates="deliveries")


class Rule(Base):
    """Rule model — evaluates incoming datapoints against a condition and triggers actions."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    event_public_id: Mapped[str] = mapped_column(String, ForeignKey("events.public_id"), nullable=False, index=True)
    operator: Mapped[RuleOperator] = mapped_column(Enum(RuleOperator), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_high: Mapped[float | None] = mapped_column(Float, nullable=True)  # upper bound for between/not_between
    action_type: Mapped[RuleActionType] = mapped_column(Enum(RuleActionType), nullable=False)
    webhook_event_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # WebhookEventType value
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)
    last_triggered_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"), index=True)

    # Relationships
    event: Mapped[Event] = relationship()
    user: Mapped[User] = relationship()


class FirmwareUpdate(Base):
    """Firmware update record — tracks OTA update lifecycle."""

    __tablename__ = "firmware_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[UpdateStatus] = mapped_column(Enum(UpdateStatus), default=UpdateStatus.pending, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_on: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_on: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"))

    # Relationships
    user: Mapped[User] = relationship()


class Dashboard(Base):
    """Custom dashboard — user-defined layout with widgets."""

    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False)
    created_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"), index=True)

    # Relationships
    user: Mapped[User] = relationship()
    widgets: Mapped[list[DashboardWidget]] = relationship(
        back_populates="dashboard", cascade="all, delete-orphan", order_by="DashboardWidget.id"
    )


class DashboardWidget(Base):
    """A single widget placed on a dashboard grid."""

    __tablename__ = "dashboard_widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    dashboard_id: Mapped[int] = mapped_column(Integer, ForeignKey("dashboards.id"), nullable=False, index=True)
    widget_type: Mapped[WidgetType] = mapped_column(Enum(WidgetType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_public_id: Mapped[str | None] = mapped_column(String, ForeignKey("events.public_id"), nullable=True)
    # Grid position (grid-layout-plus convention)
    x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    w: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    h: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # Widget-specific config stored as JSON text
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    dashboard: Mapped[Dashboard] = relationship(back_populates="widgets")
    event: Mapped[Event | None] = relationship()


class PluginInstance(Base):
    """Installed plugin instance — ties a plugin class to its configuration."""

    __tablename__ = "plugin_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    plugin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    instance_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[PluginStatus] = mapped_column(Enum(PluginStatus), default=PluginStatus.inactive)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"), index=True)

    # Relationships
    user: Mapped[User] = relationship()
    channel_mappings: Mapped[list[ChannelMapping]] = relationship(
        back_populates="plugin_instance", cascade="all, delete-orphan"
    )


class ChannelMapping(Base):
    """Maps a plugin channel to a WebMACS Event for data storage and display."""

    __tablename__ = "channel_mappings"
    __table_args__ = (Index("ix_channel_mappings_plugin_channel", "plugin_instance_id", "channel_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    plugin_instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plugin_instances.id"), nullable=False, index=True
    )
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[ChannelDirection] = mapped_column(Enum(ChannelDirection), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    event_public_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("events.public_id"), nullable=True, index=True
    )
    created_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    plugin_instance: Mapped[PluginInstance] = relationship(back_populates="channel_mappings")
    event: Mapped[Event | None] = relationship()


class PluginPackage(Base):
    """Tracks installed plugin packages — both bundled and uploaded."""

    __tablename__ = "plugin_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    package_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[PluginSource] = mapped_column(Enum(PluginSource), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plugin_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list of plugin IDs
    installed_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_public_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.public_id"), nullable=True, index=True)

    user: Mapped[User | None] = relationship()
