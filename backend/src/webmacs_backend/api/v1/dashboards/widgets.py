"""Dashboard widget endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi import Query
from sqlalchemy import select

from webmacs_backend.dependencies import DbSession, OperatorUser
from webmacs_backend.models import Dashboard, DashboardWidget, Event
from webmacs_backend.repository import get_or_404
from webmacs_backend.schemas import (
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
    StatusResponse,
)

router = APIRouter()


@router.post("/{dashboard_id}/widgets", response_model=DashboardWidgetResponse, status_code=status.HTTP_201_CREATED)
async def add_widget(
    dashboard_id: str,
    data: DashboardWidgetCreate,
    db: DbSession,
    current_user: OperatorUser,
) -> DashboardWidgetResponse:
    dashboard = await get_or_404(db, Dashboard, dashboard_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id and not current_user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")

    # Validate event exists (if provided)
    if data.event_public_id:
        ev = await db.execute(select(Event.public_id).where(Event.public_id == data.event_public_id))
        if not ev.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    widget = DashboardWidget(
        public_id=str(uuid.uuid4()),
        dashboard_id=dashboard.id,
        widget_type=data.widget_type,
        title=data.title,
        event_public_id=data.event_public_id,
        x=data.x,
        y=data.y,
        w=data.w,
        h=data.h,
        config_json=data.config_json,
    )
    db.add(widget)
    await db.flush()
    return DashboardWidgetResponse.model_validate(widget)


@router.put("/{dashboard_id}/widgets/{widget_id}", response_model=StatusResponse)
async def update_widget(
    dashboard_id: str,
    widget_id: str,
    data: DashboardWidgetUpdate,
    db: DbSession,
    current_user: OperatorUser,
) -> StatusResponse:
    dashboard = await get_or_404(db, Dashboard, dashboard_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id and not current_user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    widget = await get_or_404(db, DashboardWidget, widget_id, entity_name="DashboardWidget")
    if widget.dashboard_id != dashboard.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not on this dashboard.")

    # Validate event exists when caller explicitly sets event_public_id
    update_fields = data.model_dump(exclude_unset=True)
    new_event_pid = update_fields.get("event_public_id")
    if new_event_pid is not None:
        ev = await db.execute(select(Event.public_id).where(Event.public_id == new_event_pid))
        if not ev.first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    for field, value in update_fields.items():
        setattr(widget, field, value)
    return StatusResponse(status="success", message="Widget successfully updated.")


@router.delete("/{dashboard_id}/widgets/{widget_id}", response_model=StatusResponse)
async def delete_widget(
    dashboard_id: str,
    widget_id: str,
    db: DbSession,
    current_user: OperatorUser,
) -> StatusResponse:
    dashboard = await get_or_404(db, Dashboard, dashboard_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id and not current_user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    widget = await get_or_404(db, DashboardWidget, widget_id, entity_name="DashboardWidget")
    if widget.dashboard_id != dashboard.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not on this dashboard.")
    await db.delete(widget)
    return StatusResponse(status="success", message="Widget successfully deleted.")
