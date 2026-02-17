"""WebMACS Backend - FastAPI Application Factory."""

from __future__ import annotations

import asyncio
import contextlib
import datetime
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select

from webmacs_backend import __version__
from webmacs_backend.api.v1 import auth, datapoints, events, experiments, users
from webmacs_backend.api.v1 import dashboards as dashboards_api
from webmacs_backend.api.v1 import health as health_api
from webmacs_backend.api.v1 import logging as logging_api
from webmacs_backend.api.v1 import ota as ota_api
from webmacs_backend.api.v1 import plugins as plugins_api
from webmacs_backend.api.v1 import rules as rules_api
from webmacs_backend.api.v1 import webhooks as webhooks_api
from webmacs_backend.api.v1.health import reset_start_time
from webmacs_backend.config import settings, validate_secret_key
from webmacs_backend.database import async_session, engine, init_db
from webmacs_backend.middleware.rate_limit import RateLimitMiddleware
from webmacs_backend.middleware.request_id import RequestIdMiddleware
from webmacs_backend.models import BlacklistToken, User
from webmacs_backend.security import hash_password
from webmacs_backend.services.log_service import create_log
from webmacs_backend.ws import endpoints as ws_endpoints

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = structlog.get_logger()


# ─── Structlog configuration ────────────────────────────────────────────────


def _configure_structlog() -> None:
    """Configure structlog with standard processors including log level and request context."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ─── Token blacklist cleanup ────────────────────────────────────────────────

_CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour


async def _cleanup_expired_tokens() -> None:
    """Periodically delete blacklisted tokens that have expired (older than JWT expiry)."""
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
        try:
            cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
                minutes=settings.access_token_expire_minutes
            )
            async with async_session() as session:
                result = await session.execute(
                    delete(BlacklistToken).where(BlacklistToken.blacklisted_on < cutoff).returning(BlacklistToken.id)
                )
                count = len(result.scalars().all())
                await session.commit()
            if count:
                logger.info("blacklist_cleanup", deleted=count)
        except Exception as exc:
            logger.error("blacklist_cleanup_error", error=str(exc))


# ─── Seed admin ─────────────────────────────────────────────────────────────


async def _seed_admin() -> None:
    """Create initial admin user if no users exist."""
    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            return

        admin = User(
            email=settings.initial_admin_email,
            username=settings.initial_admin_username,
            password_hash=hash_password(settings.initial_admin_password),
            admin=True,
        )
        session.add(admin)
        await session.commit()
        logger.info("Seeded initial admin user", email=settings.initial_admin_email)


async def _log_startup() -> None:
    """Create a log entry recording that the backend has started."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.admin.is_(True)).limit(1))
        admin = result.scalar_one_or_none()
        if admin is None:
            return
        await create_log(session, f"WebMACS Backend v{__version__} started.", admin.public_id)
        await session.commit()


# ─── Lifespan ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application startup and shutdown lifecycle."""
    _configure_structlog()
    validate_secret_key()

    # Optional Sentry error tracking
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2, release=f"webmacs@{__version__}")
        logger.info("Sentry initialized")

    logger.info("Starting WebMACS Backend", version=__version__)
    await init_db()
    await _seed_admin()
    await _log_startup()
    reset_start_time()

    # Start background token cleanup task
    cleanup_task = asyncio.create_task(_cleanup_expired_tokens())

    yield

    # Cancel background task on shutdown
    cleanup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await cleanup_task
    logger.info("Shutting down WebMACS Backend")
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="WebMACS API",
        description="Web-based Monitoring and Control System for IoT experiments",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Middleware order (Starlette uses LIFO: last added = outermost):
    #   Request flow: RequestIdMiddleware → CORSMiddleware → RateLimitMiddleware → app
    #   This ensures 429 responses from RateLimit still get CORS headers.

    # Rate limiting (innermost — runs closest to the app)
    application.add_middleware(RateLimitMiddleware)

    # CORS (wraps rate-limit 429s so the frontend can read them)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID (outermost — every log line includes request_id)
    application.add_middleware(RequestIdMiddleware)

    # API v1 routers
    api_prefix = "/api/v1"
    application.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
    application.include_router(users.router, prefix=f"{api_prefix}/users", tags=["Users"])
    application.include_router(events.router, prefix=f"{api_prefix}/events", tags=["Events"])
    application.include_router(experiments.router, prefix=f"{api_prefix}/experiments", tags=["Experiments"])
    application.include_router(datapoints.router, prefix=f"{api_prefix}/datapoints", tags=["Datapoints"])
    application.include_router(logging_api.router, prefix=f"{api_prefix}/logging", tags=["Logging"])
    application.include_router(webhooks_api.router, prefix=f"{api_prefix}/webhooks", tags=["Webhooks"])
    application.include_router(rules_api.router, prefix=f"{api_prefix}/rules", tags=["Rules"])
    application.include_router(ota_api.router, prefix=f"{api_prefix}/ota", tags=["OTA Updates"])
    application.include_router(dashboards_api.router, prefix=f"{api_prefix}/dashboards", tags=["Dashboards"])
    application.include_router(plugins_api.router, prefix=f"{api_prefix}/plugins", tags=["Plugins"])

    # WebSocket endpoints
    application.include_router(ws_endpoints.router, prefix="/ws", tags=["WebSocket"])

    # Health endpoint (no auth, no prefix)
    application.include_router(health_api.router, prefix="/health", tags=["Health"])

    return application


app = create_app()
