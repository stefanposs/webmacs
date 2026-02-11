"""Rule engine - manages valve interval cycling logic."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

from webmacs_controller.schemas import EventSchema, EventType

if TYPE_CHECKING:
    from webmacs_controller.services.api_client import APIClient
    from webmacs_controller.services.hardware import HardwareInterface

logger = structlog.get_logger()


class RuleEngine:
    """Controls timed valve cycling based on open/close interval events.

    Monitors a start_button event. When activated, cycles a rule-controlled
    valve: open for ``opened`` seconds, close for ``closed`` seconds.
    """

    def __init__(
        self,
        events: list[EventSchema],
        hardware: HardwareInterface,
        api_client: APIClient,
        rule_event_id: str,
    ) -> None:
        self._hardware = hardware
        self._api_client = api_client
        self._rule_event_id = rule_event_id

        self._opened_event: EventSchema | None = None
        self._closed_event: EventSchema | None = None
        self._start_button: EventSchema | None = None
        self._rule_event: EventSchema | None = None

        for event in events:
            match event.type:
                case EventType.cmd_opened:
                    self._opened_event = event
                case EventType.cmd_closed:
                    self._closed_event = event
                case EventType.cmd_button:
                    self._start_button = event
            if event.public_id == rule_event_id:
                self._rule_event = event

        logger.info(
            "RuleEngine initialized",
            has_opened=self._opened_event is not None,
            has_closed=self._closed_event is not None,
            has_start_button=self._start_button is not None,
            has_rule=self._rule_event is not None,
        )

    async def run(self) -> None:
        """Check start button and execute one valve cycle if active."""
        if not all([self._start_button, self._opened_event, self._closed_event, self._rule_event]):
            return

        # Narrowed after all() guard — these are guaranteed non-None
        assert self._start_button is not None
        assert self._opened_event is not None
        assert self._closed_event is not None
        assert self._rule_event is not None

        try:
            start_value = await self._get_latest_value(self._start_button.public_id)
            if start_value is None or int(float(start_value)) != 1:
                return

            logger.info("Rule cycle START")
            await self._execute_cycle()
            logger.info("Rule cycle STOP")

        except Exception as e:
            logger.exception("RuleEngine run failed", error=str(e))

    async def _execute_cycle(self) -> None:
        """Run one open/close cycle of the valve."""
        assert self._opened_event is not None
        assert self._closed_event is not None
        assert self._start_button is not None

        open_duration = await self._get_latest_value(self._opened_event.public_id)
        close_duration = await self._get_latest_value(self._closed_event.public_id)

        open_secs = float(open_duration) if open_duration else 1.0
        close_secs = float(close_duration) if close_duration else 1.0

        # Phase 1: Open valve
        logger.debug("Valve OPEN", duration=open_secs)
        await self._post_rule_value(1.0)
        await asyncio.sleep(open_secs)

        # Phase 2: Close valve
        logger.debug("Valve CLOSE", duration=close_secs)
        await self._post_rule_value(0.0)
        await asyncio.sleep(close_secs)

        # Reset start button
        await self._post_event_value(self._start_button.public_id, 0.0)

    async def _post_rule_value(self, value: float) -> None:
        """Post the rule datapoint value to backend."""
        assert self._rule_event is not None
        await self._post_event_value(self._rule_event.public_id, value)

    async def _post_event_value(self, event_public_id: str, value: float) -> None:
        """Post a datapoint value for a specific event."""
        await self._api_client.post(
            "/datapoints",
            json={"event_public_id": event_public_id, "value": str(value)},
        )

    async def _get_latest_value(self, event_public_id: str) -> str | None:
        """Fetch the latest datapoint value for an event."""
        try:
            data = await self._api_client.get("/datapoints/latest")
            if isinstance(data, list):
                for dp in data:
                    if isinstance(dp, dict) and dp.get("event_public_id") == event_public_id:
                        return dp.get("value")
        except Exception as e:
            logger.warning("Failed to get latest value", event=event_public_id, error=str(e))
        return None
