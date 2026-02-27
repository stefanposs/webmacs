"""Centralised logging service — writes LogEntry rows for auditable system events."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
import json

from webmacs_backend.enums import LoggingType
from webmacs_backend.models import LogEntry

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


_LOG_CONTENT_MAX = 500


async def create_log(
    db: "AsyncSession",
    content: str,
    user_public_id: str,
    logging_type: LoggingType = LoggingType.info,
    metadata: dict | None = None,
) -> None:
    """Persist a new log entry.

    - `metadata` (optional): structured context that will be serialized and
      appended to the content up to the column size limit. This keeps the
      database schema unchanged while enabling richer, structured events.
    The caller is responsible for committing / flushing.
    """
    # Compact metadata into a short JSON snippet and append to content.
    meta_snip = ""
    if metadata:
        try:
            meta_snip = json.dumps(metadata, separators=(",", ":"))
        except Exception:
            meta_snip = "{\"meta\":\"<unserializable>\"}"

    full = content or ""
    if meta_snip:
        full = f"{full} | meta: {meta_snip}"

    # Truncate to fit DB column
    if len(full) > _LOG_CONTENT_MAX:
        full = full[: _LOG_CONTENT_MAX - 3] + "..."

    db.add(
        LogEntry(
            public_id=str(uuid.uuid4()),
            content=full,
            logging_type=logging_type,
            user_public_id=user_public_id,
        )
    )
