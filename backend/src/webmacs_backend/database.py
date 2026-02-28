"""Database engine and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from webmacs_backend.config import settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


async def init_db() -> None:
    """Ensure all tables exist (idempotent).

    ``create_all()`` is a no-op for tables that already exist, so it is
    always safe to call.  In Docker-based production deployments the
    entrypoint script runs ``create_all`` followed by
    ``alembic upgrade head`` *before* the application starts, so this
    call is an inexpensive safety-net that guarantees the base schema
    (users, events, experiments …) is present regardless of runtime mode.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency that provides an async database session.

    Commits automatically after each request. The overhead of an empty
    commit on read-only requests is negligible compared to the risk of
    silently dropping writes from Core-level operations (e.g. bulk insert).
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Standalone async context manager for use outside FastAPI DI.

    Use this in WebSocket handlers, background tasks, startup/shutdown hooks,
    and anywhere you can't use Depends(get_db).
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
