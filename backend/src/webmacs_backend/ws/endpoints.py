"""WebSocket endpoints for real-time controller telemetry and frontend streaming.

Endpoints:
  - /ws/controller/telemetry  — Controller pushes sensor batches via WebSocket
  - /ws/datapoints/stream     — Browsers receive live datapoint updates
"""

from __future__ import annotations

import datetime
import uuid

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import insert

from webmacs_backend.database import db_session
from webmacs_backend.models import Datapoint, Experiment
from webmacs_backend.ws.connection_manager import manager
from sqlalchemy import select

logger = structlog.get_logger()

router = APIRouter()


@router.websocket("/controller/telemetry")
async def controller_telemetry(ws: WebSocket) -> None:
    """Receive sensor data batches from the IoT controller via WebSocket.

    Expected JSON message format:
    {
      "datapoints": [
        {"value": 23.5, "event_public_id": "abc-123"},
        ...
      ]
    }

    Each batch is persisted and immediately broadcast to frontend subscribers.
    """
    await manager.connect("controller", ws)
    try:
        while True:
            data = await ws.receive_json()
            datapoints = data.get("datapoints", [])
            if not datapoints:
                continue

            # Persist batch using standalone session (not FastAPI DI)
            async with db_session() as session:
                # Find active experiment
                result = await session.execute(
                    select(Experiment.public_id).where(Experiment.stopped_on.is_(None))
                )
                row = result.first()
                exp_id = row[0] if row else None

                now = datetime.datetime.now(datetime.UTC)
                rows = [
                    {
                        "public_id": str(uuid.uuid4()),
                        "value": dp["value"],
                        "timestamp": now,
                        "event_public_id": dp["event_public_id"],
                        "experiment_public_id": exp_id,
                    }
                    for dp in datapoints
                ]
                await session.execute(insert(Datapoint), rows)

            # Broadcast to all frontend subscribers
            broadcast_payload = {
                "type": "datapoints_batch",
                "datapoints": [
                    {
                        "value": dp["value"],
                        "event_public_id": dp["event_public_id"],
                        "timestamp": now.isoformat(),
                        "experiment_public_id": exp_id,
                    }
                    for dp in datapoints
                ],
            }
            await manager.broadcast("frontend", broadcast_payload)

    except WebSocketDisconnect:
        logger.info("controller_ws_disconnected")
    except Exception as exc:
        logger.error("controller_ws_error", error=str(exc))
    finally:
        await manager.disconnect("controller", ws)


@router.websocket("/datapoints/stream")
async def datapoints_stream(ws: WebSocket) -> None:
    """Stream live datapoint updates to browser clients.

    This is a read-only subscription endpoint. Frontend clients connect here
    and receive real-time broadcast when the controller pushes new data.

    The client should send periodic ping/pong or a keep-alive JSON message.
    """
    await manager.connect("frontend", ws)
    try:
        # Send initial confirmation
        await ws.send_json({
            "type": "connected",
            "message": "Subscribed to live datapoint stream.",
        })

        # Keep connection alive — wait for client messages (pings/close)
        while True:
            msg = await ws.receive_json()
            # Handle optional ping
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("frontend_ws_disconnected")
    except Exception as exc:
        logger.error("frontend_ws_error", error=str(exc))
    finally:
        await manager.disconnect("frontend", ws)
