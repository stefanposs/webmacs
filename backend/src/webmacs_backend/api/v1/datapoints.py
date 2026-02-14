"""Datapoint endpoints."""

from __future__ import annotations

import datetime

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import desc, func, select

from webmacs_backend.dependencies import CurrentUser, DbSession
from webmacs_backend.models import Datapoint, Event
from webmacs_backend.repository import delete_by_public_id, get_or_404
from webmacs_backend.schemas import (
    DatapointBatchCreate,
    DatapointCreate,
    DatapointResponse,
    DatapointSeriesRequest,
    PaginatedResponse,
    StatusResponse,
)
from webmacs_backend.services.ingestion import (
    IncomingDatapoint,
    active_plugin_event_ids,
    ingest_datapoints,
)

logger = structlog.get_logger()

router = APIRouter()


@router.get("", response_model=PaginatedResponse[DatapointResponse])
async def list_datapoints(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[DatapointResponse]:
    total = (await db.execute(select(func.count(Datapoint.id)))).scalar_one()
    result = await db.execute(
        select(Datapoint).order_by(desc(Datapoint.timestamp)).offset((page - 1) * page_size).limit(page_size)
    )
    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total=total,
        data=[DatapointResponse.model_validate(dp) for dp in result.scalars().all()],
    )


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_datapoint(data: DatapointCreate, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    event_result = await db.execute(select(Event.public_id).where(Event.public_id == data.event_public_id))
    if not event_result.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    # Reject if the event is not linked to an enabled plugin
    active = await active_plugin_event_ids(db, [data.event_public_id])
    if data.event_public_id not in active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event is not linked to an enabled plugin instance.",
        )

    result = await ingest_datapoints(db, [IncomingDatapoint(value=data.value, event_public_id=data.event_public_id)])
    return StatusResponse(status="success", message=f"{result.accepted} datapoint successfully created.")


@router.post("/batch", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_datapoints_batch(
    data: DatapointBatchCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    incoming = [IncomingDatapoint(value=dp.value, event_public_id=dp.event_public_id) for dp in data.datapoints]
    result = await ingest_datapoints(db, incoming)
    return StatusResponse(status="success", message=f"{result.accepted} datapoints successfully created.")


@router.post("/series", response_model=dict[str, list[DatapointResponse]])
async def get_datapoint_series(
    data: DatapointSeriesRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, list[DatapointResponse]]:
    """Return recent datapoints grouped by event_public_id (for dashboard charts)."""
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=data.minutes)
    result = await db.execute(
        select(Datapoint)
        .where(Datapoint.event_public_id.in_(data.event_public_ids), Datapoint.timestamp >= cutoff)
        .order_by(Datapoint.timestamp)
    )
    series: dict[str, list[DatapointResponse]] = {eid: [] for eid in data.event_public_ids}
    for dp in result.scalars().all():
        if dp.event_public_id in series:
            series[dp.event_public_id].append(DatapointResponse.model_validate(dp))
    # Downsample to max_points for mini-computer performance
    for eid, points in series.items():
        if len(points) > data.max_points:
            step = len(points) / data.max_points
            sampled = [points[int(i * step)] for i in range(data.max_points - 1)]
            sampled.append(points[-1])
            series[eid] = sampled
    return series


@router.get("/latest", response_model=list[DatapointResponse])
async def get_latest_datapoints(db: DbSession, current_user: CurrentUser) -> list[DatapointResponse]:
    # Subquery: for each event, find the max id among the rows with the latest timestamp.
    ts_subq = (
        select(Datapoint.event_public_id, func.max(Datapoint.timestamp).label("max_ts"))
        .group_by(Datapoint.event_public_id)
        .subquery()
    )
    id_subq = (
        select(func.max(Datapoint.id).label("max_id"))
        .join(
            ts_subq,
            (Datapoint.event_public_id == ts_subq.c.event_public_id) & (Datapoint.timestamp == ts_subq.c.max_ts),
        )
        .group_by(Datapoint.event_public_id)
        .subquery()
    )
    result = await db.execute(select(Datapoint).where(Datapoint.id.in_(select(id_subq.c.max_id))))
    return [DatapointResponse.model_validate(dp) for dp in result.scalars().all()]


@router.get("/{public_id}", response_model=DatapointResponse)
async def get_datapoint(public_id: str, db: DbSession, current_user: CurrentUser) -> DatapointResponse:
    dp = await get_or_404(db, Datapoint, public_id, entity_name="Datapoint")
    return DatapointResponse.model_validate(dp)


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_datapoint(public_id: str, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    return await delete_by_public_id(db, Datapoint, public_id, entity_name="Datapoint")
