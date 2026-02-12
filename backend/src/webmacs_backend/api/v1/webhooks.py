"""Webhook CRUD endpoints."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from webmacs_backend.dependencies import AdminUser, DbSession
from webmacs_backend.models import Webhook, WebhookDelivery
from webmacs_backend.repository import ConflictError, delete_by_public_id, get_or_404, paginate
from webmacs_backend.schemas import (
    PaginatedResponse,
    StatusResponse,
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
)

router = APIRouter()


def _webhook_to_response(wh: Webhook) -> WebhookResponse:
    """Convert Webhook ORM model to response, parsing JSON events."""
    return WebhookResponse(
        public_id=wh.public_id,
        url=wh.url,
        events=json.loads(wh.events),
        enabled=wh.enabled,
        created_on=wh.created_on,
        user_public_id=wh.user_public_id,
    )


@router.get("", response_model=PaginatedResponse[WebhookResponse])
async def list_webhooks(
    db: DbSession,
    admin_user: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[WebhookResponse]:
    """List all webhooks (admin only)."""
    query = select(Webhook)
    total_result = await db.execute(select(func.count()).select_from(Webhook))
    total = total_result.scalar_one()

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    rows = result.scalars().all()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total=total,
        data=[_webhook_to_response(wh) for wh in rows],
    )


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(data: WebhookCreate, db: DbSession, admin_user: AdminUser) -> StatusResponse:
    """Create a new webhook subscription (admin only)."""
    # Check for duplicate URL
    result = await db.execute(select(Webhook).where(Webhook.url == data.url))
    if result.scalar_one_or_none():
        raise ConflictError("Webhook")

    db.add(
        Webhook(
            public_id=str(uuid.uuid4()),
            url=data.url,
            secret=data.secret,
            events=json.dumps([e.value for e in data.events]),
            enabled=data.enabled,
            user_public_id=admin_user.public_id,
        )
    )
    return StatusResponse(status="success", message="Webhook successfully created.")


@router.get("/{public_id}", response_model=WebhookResponse)
async def get_webhook(public_id: str, db: DbSession, admin_user: AdminUser) -> WebhookResponse:
    """Get a single webhook by public_id."""
    wh = await get_or_404(db, Webhook, public_id, entity_name="Webhook")
    return _webhook_to_response(wh)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_webhook(
    public_id: str,
    data: WebhookUpdate,
    db: DbSession,
    admin_user: AdminUser,
) -> StatusResponse:
    """Update a webhook (admin only)."""
    wh = await get_or_404(db, Webhook, public_id, entity_name="Webhook")

    update_data = data.model_dump(exclude_unset=True)
    if "events" in update_data and update_data["events"] is not None:
        update_data["events"] = json.dumps([e.value for e in (data.events or [])])

    for field, value in update_data.items():
        setattr(wh, field, value)

    return StatusResponse(status="success", message="Webhook successfully updated.")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_webhook(public_id: str, db: DbSession, admin_user: AdminUser) -> StatusResponse:
    """Delete a webhook (admin only)."""
    return await delete_by_public_id(db, Webhook, public_id, entity_name="Webhook")


# ─── Delivery Log ────────────────────────────────────────────────────────────


@router.get("/{public_id}/deliveries", response_model=PaginatedResponse[WebhookDeliveryResponse])
async def list_deliveries(
    public_id: str,
    db: DbSession,
    admin_user: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> PaginatedResponse[WebhookDeliveryResponse]:
    """List delivery attempts for a webhook."""
    wh = await get_or_404(db, Webhook, public_id, entity_name="Webhook")

    query = select(WebhookDelivery).where(WebhookDelivery.webhook_id == wh.id)
    if status_filter:
        query = query.where(WebhookDelivery.status == status_filter)
    query = query.order_by(WebhookDelivery.created_on.desc())

    return await paginate(
        db,
        WebhookDelivery,
        WebhookDeliveryResponse,
        page=page,
        page_size=page_size,
        base_query=query,
    )
