"""Event (sensor/actuator channel) endpoints."""

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from webmacs_backend.dependencies import CurrentUser, DbSession
from webmacs_backend.models import Event
from webmacs_backend.repository import ConflictError, delete_by_public_id, get_or_404, paginate, update_from_schema
from webmacs_backend.schemas import EventCreate, EventResponse, EventUpdate, PaginatedResponse, StatusResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[EventResponse])
async def list_events(
    db: DbSession, current_user: CurrentUser, page: int = 1, page_size: int = 25,
) -> PaginatedResponse[EventResponse]:
    return await paginate(db, Event, EventResponse, page=page, page_size=page_size)


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_event(data: EventCreate, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    result = await db.execute(select(Event).where(Event.name == data.name))
    if result.scalar_one_or_none():
        raise ConflictError("Event")

    db.add(Event(
        public_id=str(uuid.uuid4()),
        name=data.name,
        min_value=data.min_value,
        max_value=data.max_value,
        unit=data.unit,
        type=data.type,
        user_public_id=current_user.public_id,
    ))
    return StatusResponse(status="success", message="Event successfully created.")


@router.get("/{public_id}", response_model=EventResponse)
async def get_event(public_id: str, db: DbSession, current_user: CurrentUser) -> EventResponse:
    event = await get_or_404(db, Event, public_id, entity_name="Event")
    return EventResponse.model_validate(event)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_event(
    public_id: str, data: EventUpdate, db: DbSession, current_user: CurrentUser,
) -> StatusResponse:
    return await update_from_schema(db, Event, public_id, data, entity_name="Event")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_event(public_id: str, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    return await delete_by_public_id(db, Event, public_id, entity_name="Event")
