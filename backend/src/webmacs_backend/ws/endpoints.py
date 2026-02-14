"""WebSocket endpoints for real-time controller telemetry and frontend streaming.

Endpoints:
  - /ws/controller/telemetry  — Controller pushes sensor batches via WebSocket
  - /ws/datapoints/stream     — Browsers receive live datapoint updates

Authentication:
  All WebSocket endpoints require a valid JWT token passed as a query parameter:
    ws://host/ws/controller/telemetry?token=<jwt>
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from webmacs_backend.database import db_session
from webmacs_backend.models import BlacklistToken, User
from webmacs_backend.security import InvalidTokenError, decode_access_token
from webmacs_backend.services.ingestion import IncomingDatapoint, ingest_datapoints
from webmacs_backend.ws.connection_manager import manager

logger = structlog.get_logger()

router = APIRouter()


async def _authenticate_ws(ws: WebSocket) -> User | None:
    """Validate JWT token from query parameter and return the User, or None on failure.

    Accepts the WebSocket first, then closes with code 1008 (Policy Violation)
    if authentication fails.  Accepting before closing is required for portable
    behaviour across ASGI servers (Uvicorn, Hypercorn, Daphne).
    """
    token: str | None = ws.query_params.get("token")

    # Accept first — required for reliable close() across ASGI servers
    await ws.accept()

    if not token:
        await ws.close(code=1008, reason="Authentication required")
        logger.warning("ws_auth_failed", reason="missing_token")
        return None

    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        await ws.close(code=1008, reason="Invalid or expired token")
        logger.warning("ws_auth_failed", reason="invalid_token")
        return None

    async with db_session() as session:
        # Check blacklist
        bl_result = await session.execute(select(BlacklistToken).where(BlacklistToken.token == token))
        if bl_result.scalar_one_or_none():
            await ws.close(code=1008, reason="Token has been revoked")
            logger.warning("ws_auth_failed", reason="revoked_token")
            return None

        result = await session.execute(select(User).where(User.id == payload.user_id))
        user = result.scalar_one_or_none()

    if not user:
        await ws.close(code=1008, reason="User not found")
        logger.warning("ws_auth_failed", reason="user_not_found")
        return None

    logger.info("ws_authenticated", user_id=user.public_id)
    return user


@router.websocket("/controller/telemetry")
async def controller_telemetry(ws: WebSocket) -> None:
    """Receive sensor data batches from the IoT controller via WebSocket.

    Requires JWT token as query parameter: ``?token=<jwt>``

    Expected JSON message format:
    {
      "datapoints": [
        {"value": 23.5, "event_public_id": "abc-123"},
        ...
      ]
    }

    Each batch is persisted and immediately broadcast to frontend subscribers.
    """
    user = await _authenticate_ws(ws)
    if user is None:
        return

    await manager.connect("controller", ws)
    try:
        while True:
            data = await ws.receive_json()
            raw_datapoints = data.get("datapoints", [])
            if not raw_datapoints:
                continue

            # Validate each datapoint has the required fields
            valid: list[IncomingDatapoint] = []
            for dp in raw_datapoints:
                if not isinstance(dp, dict):
                    continue
                value = dp.get("value")
                event_pid = dp.get("event_public_id")
                if value is None or event_pid is None:
                    continue
                try:
                    valid.append(IncomingDatapoint(value=float(value), event_public_id=str(event_pid)))
                except (TypeError, ValueError):
                    continue

            if not valid:
                await ws.send_json({"type": "error", "message": "No valid datapoints in batch"})
                continue

            # Delegate to shared ingestion pipeline
            async with db_session() as session:
                result = await ingest_datapoints(session, valid)

            logger.debug(
                "ws_telemetry_batch",
                accepted=result.accepted,
                rejected=result.rejected,
            )

    except WebSocketDisconnect:
        logger.info("controller_ws_disconnected")
    except Exception as exc:
        logger.exception("controller_ws_error", error=str(exc))
    finally:
        await manager.disconnect("controller", ws)


@router.websocket("/datapoints/stream")
async def datapoints_stream(ws: WebSocket) -> None:
    """Stream live datapoint updates to browser clients.

    Requires JWT token as query parameter: ``?token=<jwt>``

    This is a read-only subscription endpoint. Frontend clients connect here
    and receive real-time broadcast when the controller pushes new data.

    The client should send periodic ping/pong or a keep-alive JSON message.
    """
    user = await _authenticate_ws(ws)
    if user is None:
        return

    await manager.connect("frontend", ws)
    try:
        # Send initial confirmation
        await ws.send_json(
            {
                "type": "connected",
                "message": "Subscribed to live datapoint stream.",
            }
        )

        # Keep connection alive — wait for client messages (pings/close)
        while True:
            msg = await ws.receive_json()
            # Handle optional ping
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("frontend_ws_disconnected")
    except Exception as exc:
        logger.exception("frontend_ws_error", error=str(exc))
    finally:
        await manager.disconnect("frontend", ws)
