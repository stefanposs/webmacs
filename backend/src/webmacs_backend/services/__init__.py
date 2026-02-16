"""Async webhook dispatcher with retry logic and dead-letter support.

Design:
- Dispatches webhook payloads via httpx with exponential backoff (max 3 retries).
- On success: marks delivery as 'delivered'.
- After all retries exhausted: marks as 'dead_letter'.
- All delivery attempts are recorded in the webhook_deliveries table.
- HMAC-SHA256 signature sent in X-Webhook-Signature header when secret is configured.
"""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import hmac
import json
import uuid
from typing import Any

import httpx
import structlog

from webmacs_backend.database import db_session
from webmacs_backend.enums import WebhookDeliveryStatus, WebhookEventType
from webmacs_backend.models import Webhook, WebhookDelivery

logger = structlog.get_logger()

# ─── Configuration ───────────────────────────────────────────────────────────

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds: 2, 4, 8
DELIVERY_TIMEOUT = 10.0  # seconds


def _sign_payload(payload: str, secret: str, timestamp: str) -> str:
    """Create HMAC-SHA256 signature for webhook payload with timestamp (replay protection)."""
    message = f"{timestamp}.{payload}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def build_payload(
    event_type: WebhookEventType,
    *,
    device: str = "",
    sensor: str = "",
    value: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable webhook payload structure."""
    payload: dict[str, Any] = {
        "type": event_type.value,
        "time": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    if device:
        payload["device"] = device
    if sensor:
        payload["sensor"] = sensor
    if value is not None:
        payload["value"] = value
    if extra:
        payload.update(extra)
    return payload


async def _deliver_single(
    client: httpx.AsyncClient,
    webhook: Webhook,
    payload_str: str,
) -> tuple[int | None, str | None]:
    """Attempt a single HTTP POST delivery. Returns (status_code, error)."""
    timestamp = str(int(datetime.datetime.now(datetime.UTC).timestamp()))
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Webhook-Timestamp": timestamp,
    }
    if webhook.secret:
        headers["X-Webhook-Signature"] = _sign_payload(payload_str, webhook.secret, timestamp)

    try:
        response = await client.post(
            webhook.url,
            content=payload_str,
            headers=headers,
            timeout=DELIVERY_TIMEOUT,
        )
        if response.status_code < 300:
            return response.status_code, None
        return response.status_code, f"HTTP {response.status_code}"
    except httpx.TimeoutException:
        return None, "Timeout"
    except httpx.TransportError as exc:
        return None, f"Transport error: {exc}"


async def _dispatch_to_webhook(
    webhook: Webhook,
    event_type: WebhookEventType,
    payload: dict[str, Any],
) -> None:
    """Dispatch payload to a single webhook with retry logic."""
    payload_str = json.dumps(payload)

    async with db_session() as session:
        delivery = WebhookDelivery(
            public_id=str(uuid.uuid4()),
            webhook_id=webhook.id,
            event_type=event_type.value,
            payload=payload_str,
            status=WebhookDeliveryStatus.pending,
            attempts=0,
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)
        delivery_id = delivery.id

    async with httpx.AsyncClient() as client:
        for attempt in range(1, MAX_RETRIES + 1):
            status_code, error = await _deliver_single(client, webhook, payload_str)

            async with db_session() as session:
                delivery_obj = await session.get(WebhookDelivery, delivery_id)
                if delivery_obj is None:
                    return
                delivery_obj.attempts = attempt
                delivery_obj.response_code = status_code

                if error is None:
                    # Success
                    delivery_obj.status = WebhookDeliveryStatus.delivered
                    delivery_obj.delivered_on = datetime.datetime.now(datetime.UTC)
                    delivery_obj.last_error = None
                    await session.commit()
                    logger.info(
                        "Webhook delivered",
                        webhook_url=webhook.url,
                        event=event_type.value,
                        attempt=attempt,
                    )
                    return

                delivery_obj.last_error = error
                await session.commit()

            logger.warning(
                "Webhook delivery failed, retrying",
                webhook_url=webhook.url,
                event=event_type.value,
                attempt=attempt,
                error=error,
            )

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)

    # All retries exhausted → dead letter
    async with db_session() as session:
        delivery_final = await session.get(WebhookDelivery, delivery_id)
        if delivery_final:
            delivery_final.status = WebhookDeliveryStatus.dead_letter
            await session.commit()

    logger.error(
        "Webhook dead-lettered after max retries",
        webhook_url=webhook.url,
        event=event_type.value,
        max_retries=MAX_RETRIES,
    )


async def dispatch_event(
    event_type: WebhookEventType,
    payload: dict[str, Any],
) -> None:
    """Fan out a webhook event to all matching, enabled subscriptions.

    Runs deliveries concurrently via asyncio.gather (fire-and-forget style,
    errors are caught per-webhook so one failure doesn't block others).
    """
    from sqlalchemy import select

    async with db_session() as session:
        result = await session.execute(select(Webhook).where(Webhook.enabled.is_(True)))
        webhooks = result.scalars().all()

    matching: list[Webhook] = []
    for wh in webhooks:
        try:
            if event_type.value in json.loads(wh.events):
                matching.append(wh)
        except (json.JSONDecodeError, TypeError):
            logger.warning("invalid_webhook_events_json", webhook_id=wh.public_id)

    if not matching:
        return

    logger.info(
        "Dispatching webhook event",
        event=event_type.value,
        target_count=len(matching),
    )

    tasks = [_dispatch_to_webhook(wh, event_type, payload) for wh in matching]
    await asyncio.gather(*tasks, return_exceptions=True)
