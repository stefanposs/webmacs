"""Test configuration and fixtures for WebMACS Backend.

Strategy
--------
- SQLite in-memory via aiosqlite  → fast, isolated, no Docker needed
- Fresh DB per test function       → create_all / drop_all around each test
- Real password hashing            → webmacs_backend.security (NOT passlib)
- auth_headers via create_access_token → no HTTP round-trip for every test
"""


from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from webmacs_backend.database import Base, get_db
from webmacs_backend.enums import (
    ChannelDirection,
    EventType,
    PluginStatus,
    RuleActionType,
    RuleOperator,
    UpdateStatus,
    UserRole,
)
from webmacs_backend.main import create_app
from webmacs_backend.models import ChannelMapping, Event, FirmwareUpdate, PluginInstance, Rule, User, Webhook
from webmacs_backend.security import create_access_token, hash_password

# ---------------------------------------------------------------------------
# In-memory SQLite for tests (requires `aiosqlite` in dev deps)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# ---------------------------------------------------------------------------
# Constants reused across test modules
# ---------------------------------------------------------------------------
ADMIN_EMAIL = "admin@test.io"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "adminpass123"


# ---------------------------------------------------------------------------
# Database engine + session (function-scoped → full isolation per test)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession]:
    """Provide a database session that is discarded after each test."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# FastAPI ASGI test client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """ASGI test client with DB dependency overridden to use test session."""
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed data helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Insert an admin user and return the ORM instance."""
    user = User(
        public_id="admin-public-id",
        email=ADMIN_EMAIL,
        username=ADMIN_USERNAME,
        password_hash=hash_password(ADMIN_PASSWORD),
        role=UserRole.admin,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(admin_user: User) -> dict[str, str]:
    """Return Bearer auth headers (no HTTP call — uses create_access_token)."""
    token = create_access_token(admin_user.id, role=admin_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def active_plugin(db_session: AsyncSession, admin_user: User) -> PluginInstance:
    """An enabled plugin instance — events linked via ChannelMapping can accept datapoints."""
    plugin = PluginInstance(
        public_id="plugin-active-001",
        plugin_id="simulated",
        instance_name="Active Test Plugin",
        demo_mode=False,
        enabled=True,
        status=PluginStatus.connected,
        user_public_id=admin_user.public_id,
    )
    db_session.add(plugin)
    await db_session.commit()
    await db_session.refresh(plugin)
    return plugin


@pytest_asyncio.fixture
async def sample_event(db_session: AsyncSession, admin_user: User, active_plugin: PluginInstance) -> Event:
    """Insert a sensor event linked to an active plugin via ChannelMapping."""
    event = Event(
        public_id="evt-temp-001",
        name="Temperature Sensor 1",
        min_value=0.0,
        max_value=200.0,
        unit="°C",
        type=EventType.sensor,
        user_public_id=admin_user.public_id,
    )
    db_session.add(event)
    await db_session.flush()

    mapping = ChannelMapping(
        plugin_instance_id=active_plugin.id,
        channel_id="ch-temp-1",
        channel_name="Temperature",
        direction=ChannelDirection.input,
        unit="°C",
        event_public_id=event.public_id,
    )
    db_session.add(mapping)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def sample_webhook(db_session: AsyncSession, admin_user: User) -> Webhook:
    """Insert a sample webhook subscription."""
    import json

    wh = Webhook(
        public_id="wh-test-001",
        url="https://example.com/hook",
        secret="test-secret-123",  # noqa: S106
        events=json.dumps(["sensor.threshold_exceeded"]),
        enabled=True,
        user_public_id=admin_user.public_id,
    )
    db_session.add(wh)
    await db_session.commit()
    await db_session.refresh(wh)
    return wh


@pytest_asyncio.fixture
async def second_event(db_session: AsyncSession, admin_user: User, active_plugin: PluginInstance) -> Event:
    """A second event linked to active plugin — needed to verify /latest returns one row per event."""
    event = Event(
        public_id="evt-press-001",
        name="Pressure Sensor 1",
        min_value=0.0,
        max_value=10.0,
        unit="bar",
        type=EventType.sensor,
        user_public_id=admin_user.public_id,
    )
    db_session.add(event)
    await db_session.flush()

    mapping = ChannelMapping(
        plugin_instance_id=active_plugin.id,
        channel_id="ch-press-1",
        channel_name="Pressure",
        direction=ChannelDirection.input,
        unit="bar",
        event_public_id=event.public_id,
    )
    db_session.add(mapping)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def sample_rule(db_session: AsyncSession, admin_user: User, sample_event: Event) -> Rule:
    """Insert a sample rule — fires when temperature > 100."""
    rule = Rule(
        public_id="rule-temp-001",
        name="High Temperature Alert",
        event_public_id=sample_event.public_id,
        operator=RuleOperator.gt,
        threshold=100.0,
        action_type=RuleActionType.webhook,
        webhook_event_type="sensor.threshold_exceeded",
        enabled=True,
        cooldown_seconds=60,
        user_public_id=admin_user.public_id,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


@pytest_asyncio.fixture
async def sample_firmware_update(db_session: AsyncSession, admin_user: User) -> FirmwareUpdate:
    """Insert a pending firmware update record."""
    fw = FirmwareUpdate(
        public_id="fw-update-001",
        version="2.1.0",
        changelog="Bug fixes and improvements",
        status=UpdateStatus.pending,
        user_public_id=admin_user.public_id,
    )
    db_session.add(fw)
    await db_session.commit()
    await db_session.refresh(fw)
    return fw


@pytest_asyncio.fixture
async def sample_plugin(db_session: AsyncSession, admin_user: User) -> PluginInstance:
    """Insert a plugin instance for plugin API tests."""
    plugin = PluginInstance(
        public_id="plugin-sim-001",
        plugin_id="simulated",
        instance_name="Test Simulated Sensors",
        demo_mode=True,
        enabled=True,
        status=PluginStatus.demo,
        user_public_id=admin_user.public_id,
    )
    db_session.add(plugin)
    await db_session.commit()
    await db_session.refresh(plugin)
    return plugin


# ---------------------------------------------------------------------------
# RBAC fixtures — operator and viewer users
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def operator_user(db_session: AsyncSession) -> User:
    """Insert an operator user and return the ORM instance."""
    user = User(
        public_id="operator-public-id",
        email="operator@test.io",
        username="operator",
        password_hash=hash_password("operatorpass123"),
        role=UserRole.operator,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def operator_headers(operator_user: User) -> dict[str, str]:
    """Bearer headers for operator user."""
    token = create_access_token(operator_user.id, role=operator_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Insert a viewer user and return the ORM instance."""
    user = User(
        public_id="viewer-public-id",
        email="viewer@test.io",
        username="viewer",
        password_hash=hash_password("viewerpass123"),
        role=UserRole.viewer,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_headers(viewer_user: User) -> dict[str, str]:
    """Bearer headers for viewer user."""
    token = create_access_token(viewer_user.id, role=viewer_user.role.value)
    return {"Authorization": f"Bearer {token}"}
