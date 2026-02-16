#!/usr/bin/env python3
"""Production-ready WebMACS webhook receiver using FastAPI.

Install dependencies::

    pip install fastapi uvicorn

Run::

    WEBHOOK_SECRET=my-secret uvicorn receiver_fastapi:app --host 0.0.0.0 --port 9000

Features:
- HMAC-SHA256 signature verification with replay protection
- Structured JSON logging
- Separate handlers per event type (easy to extend)
- Health check endpoint at GET /health
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from verify import verify_signature

# ── Configuration ────────────────────────────────────────────────────────────

WEBHOOK_SECRET: str | None = os.environ.get("WEBHOOK_SECRET")

app = FastAPI(title="WebMACS Webhook Receiver", version="1.0.0")
logger = logging.getLogger("webhook-receiver")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)


# ── Event handlers ───────────────────────────────────────────────────────────


def handle_threshold_exceeded(payload: dict[str, Any]) -> dict[str, Any]:
    """React to sensor.threshold_exceeded events.

    Examples of actions you could take here:
    - Send a Slack / Teams / PagerDuty alert
    - Write to an InfluxDB metric
    - Trigger an actuator via the WebMACS write API
    """
    sensor = payload.get("sensor", "unknown")
    value = payload.get("value")
    logger.warning("THRESHOLD EXCEEDED  sensor=%s  value=%s", sensor, value)
    return {"action": "alert_sent", "sensor": sensor, "value": value}


def handle_sensor_reading(payload: dict[str, Any]) -> dict[str, Any]:
    """React to sensor.reading events.

    Useful for forwarding readings to an external time-series database.
    """
    sensor = payload.get("sensor", "unknown")
    value = payload.get("value")
    logger.info("SENSOR READING  sensor=%s  value=%s", sensor, value)
    return {"action": "reading_logged", "sensor": sensor, "value": value}


def handle_experiment_started(payload: dict[str, Any]) -> dict[str, Any]:
    """React to experiment.started events."""
    logger.info("EXPERIMENT STARTED  %s", json.dumps(payload))
    return {"action": "experiment_tracked"}


def handle_experiment_stopped(payload: dict[str, Any]) -> dict[str, Any]:
    """React to experiment.stopped events."""
    logger.info("EXPERIMENT STOPPED  %s", json.dumps(payload))
    return {"action": "experiment_tracked"}


def handle_health_changed(payload: dict[str, Any]) -> dict[str, Any]:
    """React to system.health_changed events.

    Example: page on-call engineers when the controller goes unhealthy.
    """
    logger.warning("HEALTH CHANGED  %s", json.dumps(payload))
    return {"action": "health_alert_sent"}


# Map event type strings to handler functions
EVENT_HANDLERS: dict[str, Any] = {
    "sensor.threshold_exceeded": handle_threshold_exceeded,
    "sensor.reading": handle_sensor_reading,
    "experiment.started": handle_experiment_started,
    "experiment.stopped": handle_experiment_stopped,
    "system.health_changed": handle_health_changed,
}


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_webhook_timestamp: str | None = Header(default=None),
    x_webhook_signature: str | None = Header(default=None),
) -> dict[str, Any]:
    """Receive and process a WebMACS webhook delivery."""
    body = await request.body()

    # ── Signature verification ───────────────────────────────────────────
    if WEBHOOK_SECRET:
        if not x_webhook_timestamp or not x_webhook_signature:
            raise HTTPException(status_code=401, detail="Missing signature headers")
        if not verify_signature(body, WEBHOOK_SECRET, x_webhook_timestamp, x_webhook_signature):
            raise HTTPException(status_code=401, detail="Invalid signature or replay detected")

    # ── Parse payload ────────────────────────────────────────────────────
    try:
        payload: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    event_type: str = payload.get("type", "unknown")

    # ── Dispatch to handler ──────────────────────────────────────────────
    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        logger.warning("Unhandled event type: %s", event_type)
        return {"status": "ignored", "event_type": event_type}

    result = handler(payload)
    return {"status": "processed", "event_type": event_type, **result}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}
