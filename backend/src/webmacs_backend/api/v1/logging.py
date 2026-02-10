"""Logging endpoints."""

import uuid

from fastapi import APIRouter, status

from webmacs_backend.dependencies import CurrentUser, DbSession
from webmacs_backend.models import LogEntry
from webmacs_backend.repository import get_or_404, paginate, update_from_schema
from webmacs_backend.schemas import LogEntryCreate, LogEntryResponse, LogEntryUpdate, PaginatedResponse, StatusResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[LogEntryResponse])
async def list_log_entries(
    db: DbSession, current_user: CurrentUser, page: int = 1, page_size: int = 25,
) -> PaginatedResponse[LogEntryResponse]:
    return await paginate(db, LogEntry, LogEntryResponse, page=page, page_size=page_size)


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_log_entry(data: LogEntryCreate, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    db.add(LogEntry(
        public_id=str(uuid.uuid4()),
        content=data.content,
        logging_type=data.logging_type,
        user_public_id=current_user.public_id,
    ))
    return StatusResponse(status="success", message="Log entry successfully created.")


@router.get("/{public_id}", response_model=LogEntryResponse)
async def get_log_entry(public_id: str, db: DbSession, current_user: CurrentUser) -> LogEntryResponse:
    entry = await get_or_404(db, LogEntry, public_id, entity_name="LogEntry")
    return LogEntryResponse.model_validate(entry)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_log_entry(
    public_id: str, data: LogEntryUpdate, db: DbSession, current_user: CurrentUser,
) -> StatusResponse:
    return await update_from_schema(db, LogEntry, public_id, data, entity_name="LogEntry")
