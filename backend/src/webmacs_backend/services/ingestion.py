"""Shared datapoint ingestion pipeline.

Single source of truth for: validate → filter active plugins → persist →
fire webhooks → evaluate rules → broadcast to frontend WebSocket.

Both the REST ``POST /datapoints`` endpoints and the WebSocket
``controller_telemetry`` handler delegate to this module so that bug-fixes
and new post-ingestion hooks only need to be applied once.
"""

from __future__ import annotations

import asyncio
import datetime
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import insert, select

from webmacs_backend.enums import WebhookEventType
from webmacs_backend.models import ChannelMapping, Datapoint, Experiment, PluginInstance
from webmacs_backend.services import build_payload, dispatch_event
from webmacs_backend.services.metrics import incr as metrics_incr
from webmacs_backend.services.rule_evaluator import evaluate_rules_for_datapoint
from webmacs_backend.ws.connection_manager import manager

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# Store background tasks so they aren't garbage-collected (RUF006)
_background_tasks: set[asyncio.Task[None]] = set()

# ─── Webhook throttle for sensor.reading ─────────────────────────────────────
# Minimum seconds between webhook dispatches per sensor channel.
# Prevents high-frequency datapoint ingestion from flooding external receivers.
_SENSOR_WEBHOOK_INTERVAL: float = 5.0
_last_sensor_dispatch: dict[str, float] = {}

# ─── Frontend broadcast throttle ─────────────────────────────────────────────
# Minimum seconds between WS broadcasts per event to avoid overwhelming
# browser clients when sub-second polling is active.
_BROADCAST_INTERVAL: float = 0.2
_last_broadcast: dict[str, float] = {}

# Ingest tuning and metrics
_MAX_INGEST_BATCH = 1000
_BACKPRESSURE_THRESHOLD = 800
_BACKPRESSURE_SLEEP = 0.05

# Metrics are collected in `webmacs_backend.services.metrics`


@dataclass(frozen=True, slots=True)
class IncomingDatapoint:
    """A single datapoint before persistence."""

    value: float
    event_public_id: str


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Outcome of an ingestion batch."""

    accepted: int
    rejected: int


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def active_plugin_event_ids(db: AsyncSession, event_public_ids: list[str]) -> set[str]:
    """Return the subset of *event_public_ids* linked to an enabled PluginInstance.

    Only events that have a ChannelMapping pointing to a plugin instance with
    ``enabled=True`` are considered active.  This prevents data ingestion for
    events that no longer belong to a running plugin.
    """
    if not event_public_ids:
        return set()
    result = await db.execute(
        select(ChannelMapping.event_public_id)
        .join(PluginInstance, ChannelMapping.plugin_instance_id == PluginInstance.id)
        .where(
            ChannelMapping.event_public_id.in_(event_public_ids),
            PluginInstance.enabled.is_(True),
        )
    )
    return {row[0] for row in result.all()}


async def active_experiment_id(db: AsyncSession) -> str | None:
    """Return the ``public_id`` of the currently running experiment, or ``None``."""
    result = await db.execute(select(Experiment.public_id).where(Experiment.stopped_on.is_(None)))
    row = result.first()
    return row[0] if row else None


def _fire_webhook(event_public_id: str, value: float) -> None:
    """Schedule a fire-and-forget webhook dispatch for a new datapoint.

    Throttled: at most one dispatch per sensor every ``_SENSOR_WEBHOOK_INTERVAL``
    seconds.  This prevents high-frequency ingestion from creating thousands of
    concurrent webhook HTTP requests and overwhelming the event loop.
    """
    now = time.monotonic()
    last = _last_sensor_dispatch.get(event_public_id, 0.0)
    if now - last < _SENSOR_WEBHOOK_INTERVAL:
        return  # throttled — skip this dispatch
    _last_sensor_dispatch[event_public_id] = now

    payload = build_payload(
        WebhookEventType.sensor_reading,
        sensor=event_public_id,
        value=value,
    )
    task = asyncio.create_task(dispatch_event(WebhookEventType.sensor_reading, payload))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# ─── Public API ──────────────────────────────────────────────────────────────


async def ingest_datapoints(
    db: AsyncSession,
    datapoints: list[IncomingDatapoint],
) -> IngestionResult:
    """Persist a batch of datapoints and run all post-ingestion side-effects.

    1. Filter to events linked to an enabled plugin instance.
    2. Bulk-insert accepted datapoints.
    3. Fire webhooks (fire-and-forget).
    4. Evaluate rules per datapoint (best-effort, logged on failure).
    5. Broadcast to frontend WebSocket subscribers.

    Returns an :class:`IngestionResult` with accepted/rejected counts.
    """
    if not datapoints:
        return IngestionResult(accepted=0, rejected=0)

    # If extremely large batch, process in chunks to avoid long-running DB ops
    total_accepted = 0
    total_rejected = 0
    # If caller provided more than max, we'll chunk and apply light back-pressure
    chunks = [datapoints[i : i + _MAX_INGEST_BATCH] for i in range(0, len(datapoints), _MAX_INGEST_BATCH)]
    for idx, chunk in enumerate(chunks):
        # Add small pause when processing many chunks to avoid overwhelming DB
        if idx > 0 and len(chunk) >= _BACKPRESSURE_THRESHOLD:
            await asyncio.sleep(_BACKPRESSURE_SLEEP)
        res = await _ingest_chunk(db, chunk)
        total_accepted += res.accepted
        total_rejected += res.rejected

    # Update metrics
    metrics_incr("ingest_accepted_total", total_accepted)
    metrics_incr("ingest_rejected_total", total_rejected)
    return IngestionResult(accepted=total_accepted, rejected=total_rejected)


async def _ingest_chunk(db: AsyncSession, datapoints: list[IncomingDatapoint]) -> IngestionResult:
    """Process a single chunk of datapoints. Returns IngestionResult for the chunk."""
    if not datapoints:
        return IngestionResult(accepted=0, rejected=0)

    # Basic validation & sanitization: ensure finite floats and non-empty event ids
    import math

    valid: list[IncomingDatapoint] = []
    invalid_count = 0
    for dp in datapoints:
        try:
            v = float(dp.value)
        except Exception:
            invalid_count += 1
            logger.debug("ingest_invalid_value", value=dp.value, event=dp.event_public_id)
            continue
        if not math.isfinite(v) or not dp.event_public_id:
            invalid_count += 1
            logger.debug("ingest_invalid_value_or_event", value=v, event=dp.event_public_id)
            continue
        valid.append(IncomingDatapoint(value=v, event_public_id=dp.event_public_id))

    if not valid:
        return IngestionResult(accepted=0, rejected=len(datapoints))

    # 1. Filter by active plugin linkage
    requested_eids = list({dp.event_public_id for dp in valid})
    active_eids = await active_plugin_event_ids(db, requested_eids)
    accepted = [dp for dp in valid if dp.event_public_id in active_eids]

    if not accepted:
        return IngestionResult(accepted=0, rejected=len(datapoints))

    # 2. Persist
    exp_id = await active_experiment_id(db)
    now = datetime.datetime.now(datetime.UTC)
    rows = [
        {
            "public_id": str(uuid.uuid4()),
            "value": dp.value,
            "timestamp": now,
            "event_public_id": dp.event_public_id,
            "experiment_public_id": exp_id,
        }
        for dp in accepted
    ]
    try:
        await db.execute(insert(Datapoint), rows)
    except Exception:
        # Persistent storage failure — log and return zero accepted to let caller decide
        logger.exception("datapoint_insert_failed", count=len(rows))
        metrics_incr("ingest_errors_total", 1)
        return IngestionResult(accepted=0, rejected=len(datapoints))

    # 3. Webhooks (fire-and-forget)
    for dp in accepted:
        _fire_webhook(dp.event_public_id, dp.value)
        metrics_incr("webhook_dispatches", 1)

    # 4. Rules — evaluate only the *last* value per event to avoid redundant
    #    evaluations when a fast poller sends multiple readings for the same
    #    sensor in one batch.
    last_per_event: dict[str, float] = {}
    for dp in accepted:
        last_per_event[dp.event_public_id] = dp.value
    for event_pid, value in last_per_event.items():
        try:
            await evaluate_rules_for_datapoint(db, event_pid, value)
        except Exception:
            logger.exception(
                "rule_evaluation_failed",
                event_public_id=event_pid,
            )

    # 5. Broadcast to frontend WebSocket (throttled per event)
    broadcast_now = time.monotonic()
    broadcast_events: set[str] = set()
    for dp in accepted:
        eid = dp.event_public_id
        last_b = _last_broadcast.get(eid, 0.0)
        if broadcast_now - last_b >= _BROADCAST_INTERVAL:
            broadcast_events.add(eid)
            _last_broadcast[eid] = broadcast_now

    # Only include datapoints whose events passed the throttle
    broadcast_dps = [dp for dp in accepted if dp.event_public_id in broadcast_events]
    if broadcast_dps:
        await manager.broadcast(
            "frontend",
            {
                "type": "datapoints_batch",
                "datapoints": [
                    {
                        "value": dp.value,
                        "event_public_id": dp.event_public_id,
                        "timestamp": now.isoformat(),
                        "experiment_public_id": exp_id,
                    }
                    for dp in broadcast_dps
                ],
            },
        )
        metrics_incr("ws_broadcasts", len(broadcast_dps))

    # Update simple metrics for this chunk
    metrics_incr("ingest_accepted_total", len(accepted))
    metrics_incr("ingest_rejected_total", (len(datapoints) - len(accepted)))

    return IngestionResult(accepted=len(accepted), rejected=len(datapoints) - len(accepted))

    return IngestionResult(accepted=len(accepted), rejected=len(datapoints) - len(accepted))
