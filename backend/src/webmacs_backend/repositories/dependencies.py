"""FastAPI dependency injection for repository layer.

Provides swappable storage backends controlled by the STORAGE_BACKEND
environment variable. Currently supports:
  - 'postgresql' (default): Standard SQLAlchemy async
  - 'timescale': TimescaleDB-aware (extends SQLAlchemy, same wire protocol)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from webmacs_backend.config import settings
from webmacs_backend.database import get_db
from webmacs_backend.repositories.protocols import DatapointRepository, ExperimentRepository
from webmacs_backend.repositories.sqlalchemy_repo import (
    SQLAlchemyDatapointRepository,
    SQLAlchemyExperimentRepository,
)
from webmacs_backend.repositories.timescale_repo import (
    TimescaleDatapointRepository,
    TimescaleExperimentRepository,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession


def _get_storage_backend() -> str:
    return getattr(settings, "storage_backend", "postgresql")


async def get_datapoint_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[DatapointRepository]:
    if _get_storage_backend() == "timescale":
        yield TimescaleDatapointRepository(db)
    else:
        yield SQLAlchemyDatapointRepository(db)


async def get_experiment_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[ExperimentRepository]:
    if _get_storage_backend() == "timescale":
        yield TimescaleExperimentRepository(db)
    else:
        yield SQLAlchemyExperimentRepository(db)


# Type aliases for use in router signatures
DatapointRepo = Annotated[DatapointRepository, Depends(get_datapoint_repo)]
ExperimentRepo = Annotated[ExperimentRepository, Depends(get_experiment_repo)]
