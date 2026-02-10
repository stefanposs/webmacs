"""SQLAlchemy ORM models."""

import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from webmacs_backend.database import Base
from webmacs_backend.enums import EventType, LoggingType, StatusType


class User(Base):
    """User model for authentication and ownership."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    events: Mapped[list["Event"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    log_entries: Mapped[list["LogEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")


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
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="events")
    datapoints: Mapped[list["Datapoint"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Experiment(Base):
    """Experiment model - a time-bounded measurement session."""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    started_on: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), default=func.now())
    stopped_on: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="experiments")
    datapoints: Mapped[list["Datapoint"]] = relationship(back_populates="experiment", cascade="all, delete-orphan")


class Datapoint(Base):
    """Datapoint model - a single sensor/actuator measurement."""

    __tablename__ = "datapoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event_public_id: Mapped[str] = mapped_column(String, ForeignKey("events.public_id"))
    experiment_public_id: Mapped[str | None] = mapped_column(String, ForeignKey("experiments.public_id"), nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="datapoints")
    experiment: Mapped["Experiment | None"] = relationship(back_populates="datapoints")


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
    user_public_id: Mapped[str] = mapped_column(String, ForeignKey("users.public_id"))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="log_entries")
