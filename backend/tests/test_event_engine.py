"""Tests for Event Engine LITE — Rule model, CRUD API, and rule evaluator."""

import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from webmacs_backend.enums import RuleOperator
from webmacs_backend.services.rule_evaluator import evaluate_condition, evaluate_rules_for_datapoint

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from webmacs_backend.models import Event, Rule, User

# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests — evaluate_condition (pure function, no DB)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("value", "operator", "threshold", "threshold_high", "expected"),
    [
        # gt
        (101.0, RuleOperator.gt, 100.0, None, True),
        (100.0, RuleOperator.gt, 100.0, None, False),
        (99.0, RuleOperator.gt, 100.0, None, False),
        # lt
        (99.0, RuleOperator.lt, 100.0, None, True),
        (100.0, RuleOperator.lt, 100.0, None, False),
        (101.0, RuleOperator.lt, 100.0, None, False),
        # eq
        (100.0, RuleOperator.eq, 100.0, None, True),
        (100.1, RuleOperator.eq, 100.0, None, False),
        # gte
        (100.0, RuleOperator.gte, 100.0, None, True),
        (101.0, RuleOperator.gte, 100.0, None, True),
        (99.0, RuleOperator.gte, 100.0, None, False),
        # lte
        (100.0, RuleOperator.lte, 100.0, None, True),
        (99.0, RuleOperator.lte, 100.0, None, True),
        (101.0, RuleOperator.lte, 100.0, None, False),
        # between
        (50.0, RuleOperator.between, 10.0, 90.0, True),
        (10.0, RuleOperator.between, 10.0, 90.0, True),   # inclusive low
        (90.0, RuleOperator.between, 10.0, 90.0, True),   # inclusive high
        (5.0, RuleOperator.between, 10.0, 90.0, False),
        (95.0, RuleOperator.between, 10.0, 90.0, False),
        (50.0, RuleOperator.between, 10.0, None, False),   # no threshold_high
        # not_between
        (5.0, RuleOperator.not_between, 10.0, 90.0, True),
        (95.0, RuleOperator.not_between, 10.0, 90.0, True),
        (50.0, RuleOperator.not_between, 10.0, 90.0, False),
        (10.0, RuleOperator.not_between, 10.0, 90.0, False),  # boundary → not outside
        (50.0, RuleOperator.not_between, 10.0, None, False),  # no threshold_high
    ],
)
def test_evaluate_condition(
    value: float,
    operator: RuleOperator,
    threshold: float,
    threshold_high: float | None,
    expected: bool,
) -> None:
    assert evaluate_condition(value, operator, threshold, threshold_high) is expected


# ═══════════════════════════════════════════════════════════════════════════════
# Integration tests — evaluate_rules_for_datapoint
# ═══════════════════════════════════════════════════════════════════════════════


async def test_evaluate_rules_triggers_matching_rule(
    db_session: AsyncSession,
    sample_rule: Rule,
) -> None:
    """A value exceeding threshold should trigger the rule."""
    with patch("webmacs_backend.services.rule_evaluator._fire_rule_action") as mock_fire:
        triggered = await evaluate_rules_for_datapoint(
            db_session, sample_rule.event_public_id, 150.0
        )
    assert triggered == 1
    mock_fire.assert_called_once()


async def test_evaluate_rules_skips_non_matching(
    db_session: AsyncSession,
    sample_rule: Rule,
) -> None:
    """A value below threshold should NOT trigger the rule."""
    with patch("webmacs_backend.services.rule_evaluator._fire_rule_action") as mock_fire:
        triggered = await evaluate_rules_for_datapoint(
            db_session, sample_rule.event_public_id, 50.0
        )
    assert triggered == 0
    mock_fire.assert_not_called()


async def test_evaluate_rules_cooldown(
    db_session: AsyncSession,
    sample_rule: Rule,
) -> None:
    """Second trigger within cooldown window should be suppressed."""
    # First trigger
    with patch("webmacs_backend.services.rule_evaluator._fire_rule_action"):
        t1 = await evaluate_rules_for_datapoint(
            db_session, sample_rule.event_public_id, 150.0
        )
    assert t1 == 1

    # Second trigger immediately — should be in cooldown
    with patch("webmacs_backend.services.rule_evaluator._fire_rule_action") as mock_fire:
        t2 = await evaluate_rules_for_datapoint(
            db_session, sample_rule.event_public_id, 150.0
        )
    assert t2 == 0
    mock_fire.assert_not_called()


async def test_evaluate_rules_cooldown_expired(
    db_session: AsyncSession,
    sample_rule: Rule,
) -> None:
    """After cooldown expires, the rule should trigger again."""
    # Simulate a trigger that happened long ago
    sample_rule.last_triggered_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=120)

    with patch("webmacs_backend.services.rule_evaluator._fire_rule_action") as mock_fire:
        triggered = await evaluate_rules_for_datapoint(
            db_session, sample_rule.event_public_id, 150.0
        )
    assert triggered == 1
    mock_fire.assert_called_once()


async def test_evaluate_rules_disabled_rule(
    db_session: AsyncSession,
    sample_rule: Rule,
) -> None:
    """Disabled rules should not be evaluated."""
    sample_rule.enabled = False
    await db_session.flush()

    with patch("webmacs_backend.services.rule_evaluator._fire_rule_action") as mock_fire:
        triggered = await evaluate_rules_for_datapoint(
            db_session, sample_rule.event_public_id, 150.0
        )
    assert triggered == 0
    mock_fire.assert_not_called()


async def test_evaluate_rules_no_rules_for_event(
    db_session: AsyncSession,
    sample_event: Event,
) -> None:
    """No rules for event → 0 triggers, no crash."""
    triggered = await evaluate_rules_for_datapoint(
        db_session, sample_event.public_id, 42.0
    )
    assert triggered == 0


# ═══════════════════════════════════════════════════════════════════════════════
# API tests — Rule CRUD
# ═══════════════════════════════════════════════════════════════════════════════

RULES_URL = "/api/v1/rules"


async def test_create_rule(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_event: Event,
) -> None:
    resp = await client.post(
        RULES_URL,
        json={
            "name": "High Temp Alert",
            "event_public_id": sample_event.public_id,
            "operator": "gt",
            "threshold": 100.0,
            "action_type": "webhook",
            "webhook_event_type": "sensor.threshold_exceeded",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "success"


async def test_create_rule_duplicate_name(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_event: Event,
    sample_rule: Rule,
) -> None:
    """Duplicate rule name should return 409."""
    resp = await client.post(
        RULES_URL,
        json={
            "name": sample_rule.name,
            "event_public_id": sample_event.public_id,
            "operator": "gt",
            "threshold": 50.0,
            "action_type": "log",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 409


async def test_create_rule_invalid_event(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Creating a rule for a non-existent event should return 404."""
    resp = await client.post(
        RULES_URL,
        json={
            "name": "Ghost Rule",
            "event_public_id": "nonexistent-event",
            "operator": "gt",
            "threshold": 50.0,
            "action_type": "log",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_list_rules(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_rule: Rule,
) -> None:
    resp = await client.get(RULES_URL, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(r["name"] == sample_rule.name for r in body["data"])


async def test_get_rule(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_rule: Rule,
) -> None:
    resp = await client.get(f"{RULES_URL}/{sample_rule.public_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == sample_rule.name
    assert resp.json()["operator"] == "gt"


async def test_get_rule_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
) -> None:
    resp = await client.get(f"{RULES_URL}/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


async def test_update_rule(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_rule: Rule,
) -> None:
    resp = await client.put(
        f"{RULES_URL}/{sample_rule.public_id}",
        json={"threshold": 200.0, "enabled": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify the update
    get_resp = await client.get(f"{RULES_URL}/{sample_rule.public_id}", headers=auth_headers)
    assert get_resp.json()["threshold"] == 200.0
    assert get_resp.json()["enabled"] is False


async def test_delete_rule(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_rule: Rule,
) -> None:
    resp = await client.delete(f"{RULES_URL}/{sample_rule.public_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify it's gone
    get_resp = await client.get(f"{RULES_URL}/{sample_rule.public_id}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_rules_require_auth(client: AsyncClient) -> None:
    """All rule endpoints should require authentication."""
    resp = await client.get(RULES_URL)
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Integration test — datapoint ingestion triggers rule evaluation
# ═══════════════════════════════════════════════════════════════════════════════


async def test_datapoint_triggers_rule_evaluation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sample_event: Event,
    sample_rule: Rule,
) -> None:
    """Creating a datapoint with value > threshold should trigger rule evaluation."""
    with patch("webmacs_backend.api.v1.datapoints.evaluate_rules_for_datapoint", new_callable=AsyncMock) as mock_eval:
        mock_eval.return_value = 1
        resp = await client.post(
            "/api/v1/datapoints",
            json={"value": 150.0, "event_public_id": sample_event.public_id},
            headers=auth_headers,
        )
    assert resp.status_code == 201
    mock_eval.assert_called_once()
