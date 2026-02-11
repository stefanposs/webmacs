"""Rule Evaluator — evaluates datapoint values against configured rules.

Design:
- Pure-function condition check for all RuleOperator values.
- Cooldown / hysteresis: suppresses re-triggering within `cooldown_seconds`.
- On trigger: dispatches a webhook event (fire-and-forget) and/or logs.
- Called from datapoint ingestion (single + batch).
"""

from __future__ import annotations

import asyncio
import datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from webmacs_backend.enums import RuleActionType, RuleOperator, WebhookEventType
from webmacs_backend.models import Rule
from webmacs_backend.services import build_payload, dispatch_event

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# Store background tasks so they aren't garbage-collected (RUF006)
_background_tasks: set[asyncio.Task[None]] = set()


# ─── Pure condition evaluation ───────────────────────────────────────────────


# Tolerance for float equality comparison (ADC noise on RPi)
_FLOAT_EPSILON = 1e-9


def evaluate_condition(
    value: float,
    operator: RuleOperator,
    threshold: float,
    threshold_high: float | None = None,
) -> bool:
    """Evaluate a value against a rule condition. Pure function, no side-effects."""
    simple_ops: dict[RuleOperator, bool] = {
        RuleOperator.gt: value > threshold,
        RuleOperator.lt: value < threshold,
        RuleOperator.eq: abs(value - threshold) < _FLOAT_EPSILON,
        RuleOperator.gte: value >= threshold,
        RuleOperator.lte: value <= threshold,
    }

    if operator in simple_ops:
        return simple_ops[operator]

    if threshold_high is None:
        return False
    if operator == RuleOperator.between:
        return threshold <= value <= threshold_high
    if operator == RuleOperator.not_between:
        return value < threshold or value > threshold_high

    return False  # pragma: no cover


def _is_in_cooldown(rule: Rule, now: datetime.datetime) -> bool:
    """Check whether a rule is still within its cooldown window."""
    if rule.last_triggered_at is None:
        return False
    elapsed = (now - rule.last_triggered_at).total_seconds()
    return elapsed < rule.cooldown_seconds


# ─── Trigger action ──────────────────────────────────────────────────────────


def _fire_rule_action(rule: Rule, event_public_id: str, value: float) -> None:
    """Execute the rule's action (webhook dispatch and/or log) as fire-and-forget."""
    if rule.action_type == RuleActionType.webhook:
        wh_event_type = WebhookEventType(rule.webhook_event_type or WebhookEventType.sensor_threshold_exceeded)
        payload = build_payload(
            wh_event_type,
            sensor=event_public_id,
            value=value,
            extra={"rule": rule.name, "operator": rule.operator, "threshold": rule.threshold},
        )
        task = asyncio.create_task(dispatch_event(wh_event_type, payload))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    elif rule.action_type == RuleActionType.log:
        logger.warning(
            "Rule triggered",
            rule=rule.name,
            sensor=event_public_id,
            value=value,
            operator=rule.operator,
            threshold=rule.threshold,
        )


# ─── Main entry point ────────────────────────────────────────────────────────


async def evaluate_rules_for_datapoint(
    db: AsyncSession,
    event_public_id: str,
    value: float,
) -> int:
    """Evaluate all enabled rules for a given event and value.

    Returns the number of rules that triggered.
    """
    result = await db.execute(
        select(Rule).where(
            Rule.event_public_id == event_public_id,
            Rule.enabled.is_(True),
        )
    )
    rules = result.scalars().all()

    if not rules:
        return 0

    now = datetime.datetime.now(datetime.UTC)
    triggered = 0

    for rule in rules:
        if not evaluate_condition(value, rule.operator, rule.threshold, rule.threshold_high):
            continue

        if _is_in_cooldown(rule, now):
            logger.debug("Rule in cooldown, skipping", rule=rule.name, sensor=event_public_id)
            continue

        # Mark triggered and flush immediately to prevent cooldown race
        rule.last_triggered_at = now
        triggered += 1
        await db.flush()

        _fire_rule_action(rule, event_public_id, value)
        logger.info("Rule triggered", rule=rule.name, sensor=event_public_id, value=value)

    return triggered
