"""Dashboard CRUD endpoints (core)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from webmacs_backend.dependencies import DbSession, OperatorUser, ViewerUser
from webmacs_backend.models import Dashboard
from webmacs_backend.repository import delete_by_public_id, get_or_404, paginate
from webmacs_backend.schemas import DashboardCreate, DashboardResponse, DashboardUpdate, PaginatedResponse, StatusResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[DashboardResponse])
async def list_dashboards(
    db: DbSession,
    current_user: ViewerUser,
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
    current_user: OperatorUser,
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
async def get_dashboard(public_id: str, db: DbSession, current_user: ViewerUser) -> DashboardResponse:
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
    public_id: str, data: DashboardUpdate, db: DbSession, current_user: OperatorUser
) -> StatusResponse:
    dashboard = await get_or_404(db, Dashboard, public_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id and not current_user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dashboard, field, value)
    return StatusResponse(status="success", message="Dashboard successfully updated.")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_dashboard(public_id: str, db: DbSession, current_user: OperatorUser) -> StatusResponse:
    dashboard = await get_or_404(db, Dashboard, public_id, entity_name="Dashboard")
    if dashboard.user_public_id != current_user.public_id and not current_user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed.")
    return await delete_by_public_id(db, Dashboard, public_id, entity_name="Dashboard")
