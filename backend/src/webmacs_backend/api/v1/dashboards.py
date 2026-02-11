"""Dashboard CRUD endpoints."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from webmacs_backend.dependencies import CurrentUser, DbSession
from webmacs_backend.models import Dashboard, DashboardWidget, Event
from webmacs_backend.repository import delete_by_public_id, get_or_404, paginate
from webmacs_backend.schemas import (
    DashboardCreate,
    DashboardResponse,
    DashboardUpdate,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
    PaginatedResponse,
    StatusResponse,
)

router = APIRouter()
logger = structlog.get_logger()


# ─── Dashboard CRUD ─────────────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse[DashboardResponse])
async def list_dashboards(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[DashboardResponse]:
    """List dashboards visible to the current user (own + global)."""
    base = (
        select(Dashboard)
        .options(selectinload(Dashboard.widgets))
        .where(or_(Dashboard.user_public_id == current_user.public_id, Dashboard.is_global.is_(True)))
        .order_by(Dashboard.created_on.desc())
    )
    return await paginate(db, Dashboard, DashboardResponse, page=page, page_size=page_size, base_query=base)


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    data: DashboardCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> DashboardResponse:
    dashboard = Dashboard(
        public_id=str(uuid.uuid4()),
        name=data.name,
        is_global=data.is_global,
        user_public_id=current_user.public_id,
    )
    db.add(dashboard)
    await db.flush()
    await db.refresh(dashboard, attribute_names=["widgets"])
    return DashboardResponse.model_validate(dashboard)


@router.get("/{public_id}", response_model=DashboardResponse)
async def get_dashboard(public_id: str, db: DbSession, current_user: CurrentUser) -> DashboardResponse:
    result = await db.execute(
        select(Dashboard).options(selectinload(Dashboard.widgets)).where(Dashboard.public_id == public_id)
    )
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dashboard '{public_id}' not found.")
    # Visible if owned or global
    if dashboard.user_public_id != current_user.public_id and not dashboard.is_global:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    return DashboardResponse.model_validate(dashboard)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_dashboard(
    public_id: str, data: DashboardUpdate, db: DbSession, current_user: CurrentUser
) -> StatusResponse:
    dashboard = await get_or_404(db, Dashboard, public_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dashboard, field, value)
    return StatusResponse(status="success", message="Dashboard successfully updated.")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_dashboard(public_id: str, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    dashboard = await get_or_404(db, Dashboard, public_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    return await delete_by_public_id(db, Dashboard, public_id, entity_name="Dashboard")


# ─── Widget CRUD ─────────────────────────────────────────────────────────────


@router.post("/{dashboard_id}/widgets", response_model=DashboardWidgetResponse, status_code=status.HTTP_201_CREATED)
async def add_widget(
    dashboard_id: str,
    data: DashboardWidgetCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> DashboardWidgetResponse:
    dashboard = await get_or_404(db, Dashboard, dashboard_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id:
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
    current_user: CurrentUser,
) -> StatusResponse:
    dashboard = await get_or_404(db, Dashboard, dashboard_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    widget = await get_or_404(db, DashboardWidget, widget_id, entity_name="DashboardWidget")
    if widget.dashboard_id != dashboard.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not on this dashboard.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(widget, field, value)
    return StatusResponse(status="success", message="Widget successfully updated.")


@router.delete("/{dashboard_id}/widgets/{widget_id}", response_model=StatusResponse)
async def delete_widget(
    dashboard_id: str,
    widget_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    dashboard = await get_or_404(db, Dashboard, dashboard_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    widget = await get_or_404(db, DashboardWidget, widget_id, entity_name="DashboardWidget")
    if widget.dashboard_id != dashboard.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not on this dashboard.")
    await db.delete(widget)
    return StatusResponse(status="success", message="Widget successfully deleted.")
