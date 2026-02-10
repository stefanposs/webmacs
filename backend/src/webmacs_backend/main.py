"""WebMACS Backend - FastAPI Application Factory."""

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from webmacs_backend.api.v1 import auth, datapoints, events, experiments, users
from webmacs_backend.api.v1 import logging as logging_api
from webmacs_backend.config import settings
from webmacs_backend.database import async_session, engine, init_db
from webmacs_backend.models import User
from webmacs_backend.security import hash_password
from webmacs_backend.ws import endpoints as ws_endpoints

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = structlog.get_logger()


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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application startup and shutdown lifecycle."""
    logger.info("Starting WebMACS Backend", version="2.0.0")
    await init_db()
    await _seed_admin()
    yield
    logger.info("Shutting down WebMACS Backend")
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="WebMACS API",
        description="Web-based Monitoring and Control System for IoT experiments",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API v1 routers
    api_prefix = "/api/v1"
    application.include_router(auth.router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
    application.include_router(users.router, prefix=f"{api_prefix}/users", tags=["Users"])
    application.include_router(events.router, prefix=f"{api_prefix}/events", tags=["Events"])
    application.include_router(experiments.router, prefix=f"{api_prefix}/experiments", tags=["Experiments"])
    application.include_router(datapoints.router, prefix=f"{api_prefix}/datapoints", tags=["Datapoints"])
    application.include_router(logging_api.router, prefix=f"{api_prefix}/logging", tags=["Logging"])

    # WebSocket endpoints
    application.include_router(ws_endpoints.router, prefix="/ws", tags=["WebSocket"])

    @application.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "version": "2.0.0"}

    return application


app = create_app()
