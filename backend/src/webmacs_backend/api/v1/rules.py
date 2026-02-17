"""Rule CRUD endpoints (Event Engine LITE)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from webmacs_backend.dependencies import DbSession, OperatorUser
from webmacs_backend.enums import RuleOperator
from webmacs_backend.models import Event, Rule
from webmacs_backend.repository import ConflictError, delete_by_public_id, get_or_404, paginate
from webmacs_backend.schemas import (
    PaginatedResponse,
    RuleCreate,
    RuleResponse,
    RuleUpdate,
    StatusResponse,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[RuleResponse])
async def list_rules(
    db: DbSession,
    current_user: OperatorUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[RuleResponse]:
    """List all rules (operator+)."""
    return await paginate(db, Rule, RuleResponse, page=page, page_size=page_size)


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(data: RuleCreate, db: DbSession, current_user: OperatorUser) -> StatusResponse:
    """Create a new rule (operator+)."""
    # Verify event exists
    result = await db.execute(select(Event).where(Event.public_id == data.event_public_id))
    if not result.scalar_one_or_none():
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    # Check unique name
    result = await db.execute(select(Rule).where(Rule.name == data.name))
    if result.scalar_one_or_none():
        raise ConflictError("Rule")

    db.add(
        Rule(
            public_id=str(uuid.uuid4()),
            name=data.name,
            event_public_id=data.event_public_id,
            operator=data.operator,
            threshold=data.threshold,
            threshold_high=data.threshold_high,
            action_type=data.action_type,
            webhook_event_type=data.webhook_event_type.value if data.webhook_event_type else None,
            enabled=data.enabled,
            cooldown_seconds=data.cooldown_seconds,
            user_public_id=current_user.public_id,
        )
    )
    return StatusResponse(status="success", message="Rule successfully created.")


@router.get("/{public_id}", response_model=RuleResponse)
async def get_rule(public_id: str, db: DbSession, current_user: OperatorUser) -> RuleResponse:
    """Get a single rule by public_id."""
    rule = await get_or_404(db, Rule, public_id, entity_name="Rule")
    return RuleResponse.model_validate(rule)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_rule(
    public_id: str,
    data: RuleUpdate,
    db: DbSession,
    current_user: OperatorUser,
) -> StatusResponse:
    """Update a rule (operator+)."""
    rule = await get_or_404(db, Rule, public_id, entity_name="Rule")

    update_data = data.model_dump(exclude_unset=True)
    # Convert webhook_event_type enum to string value for DB storage
    if "webhook_event_type" in update_data and update_data["webhook_event_type"] is not None:
        update_data["webhook_event_type"] = update_data["webhook_event_type"].value

    for field, value in update_data.items():
        setattr(rule, field, value)

    # Validate consistency after partial update
    if rule.operator in (RuleOperator.between, RuleOperator.not_between) and rule.threshold_high is None:
        raise HTTPException(status_code=422, detail="threshold_high required for between/not_between operators")
    if rule.threshold_high is not None and rule.threshold_high < rule.threshold:
        raise HTTPException(status_code=422, detail="threshold_high must be >= threshold")

    return StatusResponse(status="success", message="Rule successfully updated.")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_rule(public_id: str, db: DbSession, current_user: OperatorUser) -> StatusResponse:
    """Delete a rule (operator+)."""
    return await delete_by_public_id(db, Rule, public_id, entity_name="Rule")
