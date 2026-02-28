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
    """Ensure all tables exist and Alembic migrations are applied.

    1. ``create_all()`` is always run first — it is idempotent and a no-op
       for tables that already exist.  This guarantees that the base schema
       (users, events, experiments, …) is present before any Alembic
       migration that references those tables via foreign keys.
    2. In production the Alembic migration head is applied automatically
       so that incremental migrations (plugin tables, RBAC, etc.) are
       executed on first start without manual intervention.
    """
    import structlog

    log = structlog.get_logger()

    # Step 1 — ensure base tables exist (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database_tables_ensured")

    # Step 2 — run Alembic migrations (production only)
    if settings.env.lower() == "production":
        import subprocess  # noqa: S404

        log.info("running_alembic_migrations")
        result = subprocess.run(  # noqa: S603, S607
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log.info("alembic_migrations_applied", stdout=result.stdout.strip())
        else:
            log.warning(
                "alembic_migrations_failed",
                returncode=result.returncode,
                stderr=result.stderr.strip(),
            )


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
