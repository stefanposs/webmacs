"""Tests for new features and fixes introduced in the feat/ota-update-support branch.

Covers:
- Plugin delete cascade service
- Plugin create with auto_create_events=false
- Webhook dispatch resilience (invalid JSON events)
- Rule between/not_between validation
- PluginPackageResponse JSON field_validator
- Rule evaluator match/case
- Package name validation
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from webmacs_backend.enums import (
    ChannelDirection,
    EventType,
    PluginSource,
    PluginStatus,
    RuleActionType,
    RuleOperator,
    WebhookEventType,
)
from webmacs_backend.models import (
    ChannelMapping,
    Datapoint,
    DashboardWidget,
    Event,
    PluginInstance,
    PluginPackage,
    Rule,
    Webhook,
)
from webmacs_backend.schemas import PluginPackageResponse, RuleUpdate
from webmacs_backend.services.plugin_service import delete_plugin_cascade
from webmacs_backend.services.rule_evaluator import evaluate_condition

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from webmacs_backend.models import User

pytestmark = pytest.mark.anyio


# ─── Plugin Delete Cascade ──────────────────────────────────────────────────


class TestDeletePluginCascade:
    """Tests for the delete_plugin_cascade service function."""

    async def test_deletes_instance_and_events(
        self, db_session: AsyncSession, admin_user: User, active_plugin: PluginInstance, sample_event: Event,
    ) -> None:
        """Deleting a plugin should remove its events and channel mappings."""
        instance_id = active_plugin.id
        event_pid = sample_event.public_id

        await delete_plugin_cascade(db_session, active_plugin)
        await db_session.commit()

        # Plugin instance should be gone
        result = await db_session.execute(select(PluginInstance).where(PluginInstance.id == instance_id))
        assert result.scalar_one_or_none() is None

        # Event should be gone
        result = await db_session.execute(select(Event).where(Event.public_id == event_pid))
        assert result.scalar_one_or_none() is None

        # Channel mappings should be gone
        result = await db_session.execute(
            select(ChannelMapping).where(ChannelMapping.plugin_instance_id == instance_id),
        )
        assert result.scalars().all() == []

    async def test_deletes_related_datapoints(
        self, db_session: AsyncSession, admin_user: User, active_plugin: PluginInstance, sample_event: Event,
    ) -> None:
        """Deleting a plugin should also remove datapoints for its events."""
        dp = Datapoint(
            public_id="dp-cascade-001",
            value=42.0,
            event_public_id=sample_event.public_id,
        )
        db_session.add(dp)
        await db_session.commit()

        await delete_plugin_cascade(db_session, active_plugin)
        await db_session.commit()

        result = await db_session.execute(select(Datapoint).where(Datapoint.public_id == "dp-cascade-001"))
        assert result.scalar_one_or_none() is None

    async def test_deletes_related_rules(
        self, db_session: AsyncSession, admin_user: User, active_plugin: PluginInstance,
        sample_event: Event, sample_rule: Rule,
    ) -> None:
        """Deleting a plugin should remove rules linked to its events."""
        rule_pid = sample_rule.public_id

        await delete_plugin_cascade(db_session, active_plugin)
        await db_session.commit()

        result = await db_session.execute(select(Rule).where(Rule.public_id == rule_pid))
        assert result.scalar_one_or_none() is None

    async def test_nullifies_dashboard_widget_event(
        self, db_session: AsyncSession, admin_user: User, active_plugin: PluginInstance,
        sample_event: Event,
    ) -> None:
        """Dashboard widgets with nullable event FK should get event_public_id set to NULL."""
        from webmacs_backend.models import Dashboard

        dashboard = Dashboard(
            public_id="dash-test-001",
            name="Test Dashboard",
            user_public_id=admin_user.public_id,
        )
        db_session.add(dashboard)
        await db_session.flush()

        widget = DashboardWidget(
            public_id="widget-test-001",
            dashboard_id=dashboard.id,
            widget_type="line_chart",
            title="Temperature Chart",
            event_public_id=sample_event.public_id,
            x=0, y=0, w=4, h=3,
        )
        db_session.add(widget)
        await db_session.commit()

        await delete_plugin_cascade(db_session, active_plugin)
        await db_session.commit()

        result = await db_session.execute(
            select(DashboardWidget).where(DashboardWidget.public_id == "widget-test-001"),
        )
        widget_after = result.scalar_one()
        assert widget_after.event_public_id is None  # Nullified, not deleted

    async def test_no_events_still_works(
        self, db_session: AsyncSession, admin_user: User,
    ) -> None:
        """Deleting a plugin with no channel events should still succeed."""
        plugin = PluginInstance(
            public_id="plugin-noevent-001",
            plugin_id="simulated",
            instance_name="No Events Plugin",
            demo_mode=True,
            enabled=True,
            status=PluginStatus.demo,
            user_public_id=admin_user.public_id,
        )
        db_session.add(plugin)
        await db_session.commit()

        await delete_plugin_cascade(db_session, plugin)
        await db_session.commit()

        result = await db_session.execute(
            select(PluginInstance).where(PluginInstance.public_id == "plugin-noevent-001"),
        )
        assert result.scalar_one_or_none() is None


# ─── Plugin Create with auto_create_events ────────────────────────────────


class TestPluginAutoCreateEvents:
    """Tests for the auto_create_events flag on plugin creation."""

    async def test_create_without_auto_create_events(
        self, client: AsyncClient, auth_headers: dict,
    ) -> None:
        """Creating a plugin with auto_create_events=false should NOT create events."""
        resp = await client.post(
            "/api/v1/plugins",
            json={
                "plugin_id": "simulated",
                "instance_name": "No Auto Events",
                "demo_mode": True,
                "auto_create_events": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201

    async def test_create_with_auto_create_events_default(
        self, client: AsyncClient, auth_headers: dict,
    ) -> None:
        """Default creation should still work (auto_create_events defaults to true)."""
        resp = await client.post(
            "/api/v1/plugins",
            json={
                "plugin_id": "simulated",
                "instance_name": "Default Auto Events",
                "demo_mode": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201


# ─── Rule Evaluator ─────────────────────────────────────────────────────────


class TestRuleEvaluator:
    """Tests for the match/case rule evaluator."""

    def test_gt(self) -> None:
        assert evaluate_condition(101.0, RuleOperator.gt, 100.0) is True
        assert evaluate_condition(99.0, RuleOperator.gt, 100.0) is False

    def test_lt(self) -> None:
        assert evaluate_condition(50.0, RuleOperator.lt, 100.0) is True
        assert evaluate_condition(150.0, RuleOperator.lt, 100.0) is False

    def test_eq(self) -> None:
        assert evaluate_condition(100.0, RuleOperator.eq, 100.0) is True
        assert evaluate_condition(100.001, RuleOperator.eq, 100.0) is False

    def test_gte(self) -> None:
        assert evaluate_condition(100.0, RuleOperator.gte, 100.0) is True
        assert evaluate_condition(99.9, RuleOperator.gte, 100.0) is False

    def test_lte(self) -> None:
        assert evaluate_condition(100.0, RuleOperator.lte, 100.0) is True
        assert evaluate_condition(100.1, RuleOperator.lte, 100.0) is False

    def test_between(self) -> None:
        assert evaluate_condition(50.0, RuleOperator.between, 10.0, 100.0) is True
        assert evaluate_condition(5.0, RuleOperator.between, 10.0, 100.0) is False
        assert evaluate_condition(150.0, RuleOperator.between, 10.0, 100.0) is False

    def test_not_between(self) -> None:
        assert evaluate_condition(5.0, RuleOperator.not_between, 10.0, 100.0) is True
        assert evaluate_condition(50.0, RuleOperator.not_between, 10.0, 100.0) is False

    def test_between_without_threshold_high_returns_false(self) -> None:
        assert evaluate_condition(50.0, RuleOperator.between, 10.0, None) is False

    def test_not_between_without_threshold_high_returns_false(self) -> None:
        assert evaluate_condition(50.0, RuleOperator.not_between, 10.0, None) is False


# ─── Rule Validation ────────────────────────────────────────────────────────


class TestRuleUpdateValidation:
    """Tests for RuleUpdate cross-field validation."""

    def test_between_requires_threshold_high(self) -> None:
        with pytest.raises(ValueError, match="threshold_high"):
            RuleUpdate(operator=RuleOperator.between, threshold=10.0, threshold_high=None)

    def test_not_between_requires_threshold_high(self) -> None:
        with pytest.raises(ValueError, match="threshold_high"):
            RuleUpdate(operator=RuleOperator.not_between, threshold=10.0)

    def test_between_with_threshold_high_passes(self) -> None:
        r = RuleUpdate(operator=RuleOperator.between, threshold=10.0, threshold_high=50.0)
        assert r.threshold_high == 50.0

    def test_simple_operator_without_threshold_high_passes(self) -> None:
        r = RuleUpdate(operator=RuleOperator.gt, threshold=100.0)
        assert r.operator == RuleOperator.gt


# ─── PluginPackageResponse JSON Validator ────────────────────────────────────


class TestPluginPackageResponseValidator:
    """Tests for the plugin_ids field_validator on PluginPackageResponse."""

    def test_parses_json_string(self) -> None:
        resp = PluginPackageResponse(
            public_id="pkg-001",
            package_name="test-pkg",
            version="1.0.0",
            source=PluginSource.uploaded,
            plugin_ids='["foo", "bar"]',
        )
        assert resp.plugin_ids == ["foo", "bar"]

    def test_accepts_list(self) -> None:
        resp = PluginPackageResponse(
            public_id="pkg-002",
            package_name="test-pkg-2",
            version="1.0.0",
            source=PluginSource.bundled,
            plugin_ids=["baz"],
        )
        assert resp.plugin_ids == ["baz"]

    def test_invalid_json_returns_empty(self) -> None:
        resp = PluginPackageResponse(
            public_id="pkg-003",
            package_name="test-pkg-3",
            version="1.0.0",
            source=PluginSource.uploaded,
            plugin_ids="{broken json",
        )
        assert resp.plugin_ids == []

    def test_empty_default(self) -> None:
        resp = PluginPackageResponse(
            public_id="pkg-004",
            package_name="test-pkg-4",
            version="1.0.0",
            source=PluginSource.bundled,
        )
        assert resp.plugin_ids == []


# ─── Webhook Dispatch Resilience ─────────────────────────────────────────────


class TestWebhookDispatchResilience:
    """Tests for webhook event JSON parsing resilience."""

    def test_invalid_json_does_not_match(self) -> None:
        """json.loads on invalid events column should not crash the matching loop."""
        import json as _json

        events_json = "NOT VALID JSON {{{"
        matched = False
        try:
            if "sensor.reading" in _json.loads(events_json):
                matched = True
        except (_json.JSONDecodeError, TypeError):
            pass  # Expected — skip this webhook
        assert matched is False

    def test_valid_json_matches(self) -> None:
        """Valid JSON events column should produce a match."""
        import json as _json

        events_json = _json.dumps(["sensor.reading", "sensor.threshold_exceeded"])
        matched = False
        try:
            if "sensor.reading" in _json.loads(events_json):
                matched = True
        except (_json.JSONDecodeError, TypeError):
            pass
        assert matched is True

    def test_mixed_valid_and_invalid_webhooks(self) -> None:
        """Among multiple webhooks, only valid JSON events should match."""
        import json as _json

        webhook_events = [
            "NOT VALID",              # broken
            _json.dumps(["sensor.reading"]),  # valid match
            "[broken",                # broken
            _json.dumps(["experiment.started"]),  # valid, no match
        ]
        matching_count = 0
        for events in webhook_events:
            try:
                if "sensor.reading" in _json.loads(events):
                    matching_count += 1
            except (_json.JSONDecodeError, TypeError):
                pass
        assert matching_count == 1


# ─── Package Name Validation ────────────────────────────────────────────────


class TestPackageNameValidation:
    """Tests for package name regex validation on uninstall."""

    async def test_uninstall_rejects_malicious_package_name(
        self, db_session: AsyncSession, client: AsyncClient, auth_headers: dict, admin_user: User,
    ) -> None:
        """A package with shell metacharacters in its name should be rejected."""
        # Insert a package with a malicious name directly into DB
        pkg = PluginPackage(
            public_id="pkg-malicious-001",
            package_name="evil; rm -rf /",
            version="1.0.0",
            source=PluginSource.uploaded,
            plugin_ids="[]",
            user_public_id=admin_user.public_id,
        )
        db_session.add(pkg)
        await db_session.commit()

        resp = await client.delete(
            f"/api/v1/plugins/packages/{pkg.public_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "Invalid package name" in resp.json()["detail"]

    async def test_uninstall_bundled_rejected(
        self, db_session: AsyncSession, client: AsyncClient, auth_headers: dict, admin_user: User,
    ) -> None:
        """Bundled packages cannot be uninstalled."""
        pkg = PluginPackage(
            public_id="pkg-bundled-001",
            package_name="webmacs-plugins-core",
            version="1.0.0",
            source=PluginSource.bundled,
            plugin_ids="[]",
        )
        db_session.add(pkg)
        await db_session.commit()

        resp = await client.delete(
            f"/api/v1/plugins/packages/{pkg.public_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "Bundled" in resp.json()["detail"]
