"""Centralised logging service — writes LogEntry rows for auditable system events."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from webmacs_backend.enums import LoggingType
from webmacs_backend.models import LogEntry

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def create_log(
    db: AsyncSession,
    content: str,
    user_public_id: str,
    logging_type: LoggingType = LoggingType.info,
) -> None:
    """Persist a new log entry.  The caller is responsible for committing / flushing."""
    db.add(
        LogEntry(
            public_id=str(uuid.uuid4()),
            content=content,
            logging_type=logging_type,
            user_public_id=user_public_id,
        )
    )
