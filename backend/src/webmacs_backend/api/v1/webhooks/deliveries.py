"""Webhook delivery listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from webmacs_backend.dependencies import AdminUser, DbSession
from webmacs_backend.models import Webhook, WebhookDelivery
from webmacs_backend.repository import get_or_404, paginate
from webmacs_backend.schemas import PaginatedResponse, WebhookDeliveryResponse

router = APIRouter()


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
