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
from webmacs_backend.main import create_app
from webmacs_backend.models import Event, EventType, User
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
        admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(admin_user: User) -> dict[str, str]:
    """Return Bearer auth headers (no HTTP call — uses create_access_token)."""
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_event(db_session: AsyncSession, admin_user: User) -> Event:
    """Insert a sensor event — useful for datapoint tests."""
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
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def second_event(db_session: AsyncSession, admin_user: User) -> Event:
    """A second event — needed to verify /latest returns one row per event."""
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
    await db_session.commit()
    await db_session.refresh(event)
    return event
