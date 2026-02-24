"""Logging endpoints."""

from __future__ import annotations

import csv
import datetime
import io
import uuid
from collections.abc import Generator

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, select

from webmacs_backend.dependencies import DbSession, OperatorUser, ViewerUser
from webmacs_backend.enums import LoggingType
from webmacs_backend.models import LogEntry
from webmacs_backend.repository import get_or_404, paginate, update_from_schema
from webmacs_backend.schemas import LogEntryCreate, LogEntryResponse, LogEntryUpdate, PaginatedResponse, StatusResponse

router = APIRouter()


def _build_log_query(
    *,
    logging_type: LoggingType | None,
    search: str | None,
    from_date: datetime.datetime | None,
    to_date: datetime.datetime | None,
) -> Select[tuple[LogEntry]]:
    query = select(LogEntry)

    if logging_type is not None:
        query = query.where(LogEntry.logging_type == logging_type)

    if search:
        query = query.where(LogEntry.content.ilike(f"%{search}%"))

    if from_date is not None:
        query = query.where(LogEntry.created_on >= from_date)

    if to_date is not None:
        query = query.where(LogEntry.created_on <= to_date)

    return query.order_by(LogEntry.created_on.desc())


@router.get("", response_model=PaginatedResponse[LogEntryResponse])
async def list_log_entries(
    db: DbSession,
    current_user: ViewerUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    logging_type: LoggingType | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    from_date: datetime.datetime | None = Query(default=None),
    to_date: datetime.datetime | None = Query(default=None),
) -> PaginatedResponse[LogEntryResponse]:
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="from_date must be <= to_date.")

    query = _build_log_query(
        logging_type=logging_type,
        search=search,
        from_date=from_date,
        to_date=to_date,
    )
    return await paginate(db, LogEntry, LogEntryResponse, page=page, page_size=page_size, base_query=query)


@router.get("/export/csv")
async def export_log_entries_csv(
    db: DbSession,
    current_user: ViewerUser,
    logging_type: LoggingType | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1),
    from_date: datetime.datetime | None = Query(default=None),
    to_date: datetime.datetime | None = Query(default=None),
) -> StreamingResponse:
    """Export log entries as CSV (optionally filtered)."""
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="from_date must be <= to_date.")

    query = _build_log_query(
        logging_type=logging_type,
        search=search,
        from_date=from_date,
        to_date=to_date,
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    def generate() -> Generator[str]:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "created_on",
                "public_id",
                "logging_type",
                "status_type",
                "content",
                "user_public_id",
            ]
        )
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for row in rows:
            writer.writerow(
                [
                    row.created_on.isoformat() if row.created_on else "",
                    row.public_id,
                    row.logging_type.value if row.logging_type else "",
                    row.status_type.value if row.status_type else "",
                    row.content,
                    row.user_public_id,
                ]
            )
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    filename = f"logs_{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_log_entry(data: LogEntryCreate, db: DbSession, current_user: OperatorUser) -> StatusResponse:
    db.add(
        LogEntry(
            public_id=str(uuid.uuid4()),
            content=data.content,
            logging_type=data.logging_type,
            user_public_id=current_user.public_id,
        )
    )
    return StatusResponse(status="success", message="Log entry successfully created.")


@router.get("/{public_id}", response_model=LogEntryResponse)
async def get_log_entry(public_id: str, db: DbSession, current_user: ViewerUser) -> LogEntryResponse:
    entry = await get_or_404(db, LogEntry, public_id, entity_name="LogEntry")
    return LogEntryResponse.model_validate(entry)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_log_entry(
    public_id: str,
    data: LogEntryUpdate,
    db: DbSession,
    current_user: OperatorUser,
) -> StatusResponse:
    return await update_from_schema(db, LogEntry, public_id, data, entity_name="LogEntry")
