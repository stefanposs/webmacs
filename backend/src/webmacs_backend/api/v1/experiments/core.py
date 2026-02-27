"""Experiment CRUD endpoints (core)."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from webmacs_backend.dependencies import DbSession, OperatorUser, ViewerUser
from webmacs_backend.models import Experiment
from webmacs_backend.repository import delete_by_public_id, get_or_404, paginate, update_from_schema
from webmacs_backend.schemas import (
    ExperimentCreate,
    ExperimentResponse,
    ExperimentUpdate,
    PaginatedResponse,
    StatusResponse,
)
from webmacs_backend.services import build_payload, dispatch_event
from webmacs_backend.services.log_service import create_log
from webmacs_backend.enums import WebhookEventType

router = APIRouter()

# Store background tasks so they aren't garbage-collected (RUF006)
_background_tasks: set[asyncio.Task[None]] = set()


@router.get("", response_model=PaginatedResponse[ExperimentResponse])
async def list_experiments(
    db: DbSession,
    current_user: ViewerUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[ExperimentResponse]:
    return await paginate(db, Experiment, ExperimentResponse, page=page, page_size=page_size)


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(data: ExperimentCreate, db: DbSession, current_user: OperatorUser) -> StatusResponse:
    db.add(
        Experiment(
            public_id=str(uuid.uuid4()),
            name=data.name,
            user_public_id=current_user.public_id,
        )
    )
    await create_log(db, f"Experiment '{data.name}' started.", current_user.public_id)

    # Fire webhook for experiment.started
    payload = build_payload(WebhookEventType.experiment_started, extra={"experiment": data.name})
    task = asyncio.create_task(dispatch_event(WebhookEventType.experiment_started, payload))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return StatusResponse(status="success", message="Experiment successfully created.")


@router.get("/{public_id}", response_model=ExperimentResponse)
async def get_experiment(public_id: str, db: DbSession, current_user: ViewerUser) -> ExperimentResponse:
    exp = await get_or_404(db, Experiment, public_id, entity_name="Experiment")
    return ExperimentResponse.model_validate(exp)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_experiment(
    public_id: str,
    data: ExperimentUpdate,
    db: DbSession,
    current_user: OperatorUser,
) -> StatusResponse:
    return await update_from_schema(db, Experiment, public_id, data, entity_name="Experiment")


@router.put("/{public_id}/stop", response_model=StatusResponse)
async def stop_experiment(public_id: str, db: DbSession, current_user: OperatorUser) -> StatusResponse:
    exp = await get_or_404(db, Experiment, public_id, entity_name="Experiment")
    import datetime

    exp.stopped_on = datetime.datetime.now(datetime.UTC)
    await create_log(db, f"Experiment '{exp.name}' stopped.", current_user.public_id)

    # Fire webhook for experiment.stopped
    payload = build_payload(WebhookEventType.experiment_stopped, extra={"experiment": exp.name})
    task = asyncio.create_task(dispatch_event(WebhookEventType.experiment_stopped, payload))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return StatusResponse(status="success", message="Experiment successfully stopped.")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_experiment(public_id: str, db: DbSession, current_user: OperatorUser) -> StatusResponse:
    return await delete_by_public_id(db, Experiment, public_id, entity_name="Experiment")
