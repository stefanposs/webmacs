"""Cross-feature integration tests — verify end-to-end flows across multiple API domains.

These tests simulate real user workflows and verify that features interact correctly.
This is the "regression safety net" — if these pass, core flows are intact.
"""

import pytest

pytestmark = pytest.mark.anyio


# ─── Flow 1: Experiment lifecycle → datapoints → CSV export ─────────────────


async def test_experiment_lifecycle_with_data(client, auth_headers, admin_user, sample_event):
    """Create experiment → push data → stop → verify CSV export contains data."""
    # 1. Create experiment
    r = await client.post(
        "/api/v1/experiments", json={"name": "Integration Exp"}, headers=auth_headers
    )
    assert r.status_code == 201

    # 2. Get experiment public_id
    list_r = await client.get("/api/v1/experiments", headers=auth_headers)
    exp = list_r.json()["data"][0]
    exp_pid = exp["public_id"]
    assert exp["stopped_on"] is None  # running

    # 3. Push datapoints (auto-linked to active experiment)
    for val in [22.5, 35.0, 48.7]:
        r = await client.post(
            "/api/v1/datapoints",
            json={"value": val, "event_public_id": sample_event.public_id},
            headers=auth_headers,
        )
        assert r.status_code == 201

    # 4. Verify datapoints exist
    dp_r = await client.get("/api/v1/datapoints", headers=auth_headers)
    assert dp_r.json()["total"] == 3

    # 5. Verify /latest returns one per event
    latest_r = await client.get("/api/v1/datapoints/latest", headers=auth_headers)
    assert latest_r.status_code == 200
    latest = latest_r.json()
    assert len(latest) == 1
    assert latest[0]["value"] == 48.7  # most recent

    # 6. Stop experiment
    r = await client.put(f"/api/v1/experiments/{exp_pid}/stop", headers=auth_headers)
    assert r.status_code == 200

    # 7. Export CSV
    csv_r = await client.get(f"/api/v1/experiments/{exp_pid}/export/csv", headers=auth_headers)
    assert csv_r.status_code == 200
    lines = csv_r.text.strip().split("\n")
    assert len(lines) == 4  # header + 3 data rows
    assert "22.5" in csv_r.text
    assert "48.7" in csv_r.text


# ─── Flow 2: Event → Rule → Datapoint triggers rule evaluation ──────────────


async def test_rule_triggers_on_datapoint(client, auth_headers, admin_user, sample_event):
    """Create rule → push datapoint that exceeds threshold → rule evaluation runs.

    Note: We can't directly verify webhook delivery in-process (httpx mock needed),
    but we verify the API flow doesn't error and the rule's metadata is consistent.
    """
    # 1. Create a rule: fire when temp > 50
    r = await client.post(
        "/api/v1/rules",
        json={
            "name": "Integration Rule",
            "event_public_id": sample_event.public_id,
            "operator": "gt",
            "threshold": 50.0,
            "action_type": "log",  # use log action to avoid httpx calls
            "cooldown_seconds": 0,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201

    # 2. Push a datapoint that exceeds threshold
    r = await client.post(
        "/api/v1/datapoints",
        json={"value": 75.0, "event_public_id": sample_event.public_id},
        headers=auth_headers,
    )
    assert r.status_code == 201  # No error — rule evaluation ran

    # 3. Push a datapoint below threshold (rule should NOT fire)
    r = await client.post(
        "/api/v1/datapoints",
        json={"value": 30.0, "event_public_id": sample_event.public_id},
        headers=auth_headers,
    )
    assert r.status_code == 201


# ─── Flow 3: Webhook lifecycle (CRUD + delivery listing) ────────────────────


async def test_webhook_full_lifecycle(client, auth_headers, admin_user):
    """Create → update → list deliveries → delete webhook."""
    # 1. Create webhook
    r = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://integration.test/hook",
            "secret": "integ-secret",
            "events": ["sensor.threshold_exceeded", "experiment.started"],
            "enabled": True,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201

    # 2. List and verify
    list_r = await client.get("/api/v1/webhooks", headers=auth_headers)
    wh = list_r.json()["data"][0]
    wh_pid = wh["public_id"]
    assert set(wh["events"]) == {"sensor.threshold_exceeded", "experiment.started"}

    # 3. Update events list
    r = await client.put(
        f"/api/v1/webhooks/{wh_pid}",
        json={"events": ["sensor.reading"]},
        headers=auth_headers,
    )
    assert r.status_code == 200

    get_r = await client.get(f"/api/v1/webhooks/{wh_pid}", headers=auth_headers)
    assert get_r.json()["events"] == ["sensor.reading"]

    # 4. List deliveries (empty initially)
    del_r = await client.get(f"/api/v1/webhooks/{wh_pid}/deliveries", headers=auth_headers)
    assert del_r.status_code == 200
    assert del_r.json()["total"] == 0

    # 5. Delete webhook
    r = await client.delete(f"/api/v1/webhooks/{wh_pid}", headers=auth_headers)
    assert r.status_code == 200


# ─── Flow 4: OTA update full lifecycle ───────────────────────────────────────


async def test_ota_full_lifecycle(client, auth_headers, admin_user, sample_firmware_update):
    """List → get → apply → verify state transition → delete."""
    pid = sample_firmware_update.public_id

    # 1. List
    r = await client.get("/api/v1/ota", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # 2. Get single
    r = await client.get(f"/api/v1/ota/{pid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "pending"

    # 3. Apply
    r = await client.post(f"/api/v1/ota/{pid}/apply", headers=auth_headers)
    assert r.status_code == 200

    # 4. Verify state changed (goes to 'completed' directly when no firmware file)
    r = await client.get(f"/api/v1/ota/{pid}", headers=auth_headers)
    assert r.json()["status"] in ("applying", "downloading", "verifying", "completed")

    # 5. Check endpoint
    r = await client.get("/api/v1/ota/check", headers=auth_headers)
    assert r.status_code == 200
    assert "current_version" in r.json()


# ─── Flow 5: Multi-event datapoints with batch create ────────────────────────


async def test_batch_datapoints_across_events(client, auth_headers, admin_user, sample_event, second_event):
    """Batch create datapoints for multiple events → verify /latest returns one per event."""
    r = await client.post(
        "/api/v1/datapoints/batch",
        json={
            "datapoints": [
                {"value": 10.0, "event_public_id": sample_event.public_id},
                {"value": 20.0, "event_public_id": sample_event.public_id},
                {"value": 5.5, "event_public_id": second_event.public_id},
                {"value": 7.7, "event_public_id": second_event.public_id},
            ]
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert "4 datapoints" in r.json()["message"]

    # /latest should return 2 rows — one per event
    latest_r = await client.get("/api/v1/datapoints/latest", headers=auth_headers)
    assert latest_r.status_code == 200
    latest = latest_r.json()
    assert len(latest) == 2

    # Verify latest values
    values_by_event = {dp["event_public_id"]: dp["value"] for dp in latest}
    assert values_by_event[sample_event.public_id] == 20.0
    assert values_by_event[second_event.public_id] == 7.7


# ─── Flow 6: User registration → login → access resources → logout ──────────


async def test_user_registration_to_logout_flow(client, auth_headers, admin_user):
    """Admin creates user → user logs in → access /me → logout → token rejected."""
    # 1. Admin creates user
    r = await client.post(
        "/api/v1/users",
        json={"email": "flow@test.io", "username": "flowuser", "password": "securepass123"},
        headers=auth_headers,
    )
    assert r.status_code == 201

    # 2. Login
    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": "flow@test.io", "password": "securepass123"},
    )
    assert login_r.status_code == 200
    token = login_r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Access /me
    me_r = await client.get("/api/v1/auth/me", headers=headers)
    assert me_r.status_code == 200
    assert me_r.json()["email"] == "flow@test.io"

    # 4. Logout
    logout_r = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_r.status_code == 200

    # 5. Token should be rejected after logout
    me_r2 = await client.get("/api/v1/auth/me", headers=headers)
    assert me_r2.status_code == 401


# ─── Flow 7: Logging → status tracking ──────────────────────────────────────


async def test_logging_status_flow(client, auth_headers, admin_user):
    """Create log entries → mark as read → verify status change."""
    base = "/api/v1/logging"

    # Create multiple log entries
    for content in ["System boot", "Sensor connected", "Warning: high temp"]:
        await client.post(base, json={"content": content}, headers=auth_headers)

    # All should be unread initially
    list_r = await client.get(base, headers=auth_headers)
    entries = list_r.json()["data"]
    assert all(e["status_type"] == "unread" for e in entries)

    # Mark first as read
    pid = entries[0]["public_id"]
    r = await client.put(f"{base}/{pid}", json={"status_type": "read"}, headers=auth_headers)
    assert r.status_code == 200

    # Verify mixed state
    list_r2 = await client.get(base, headers=auth_headers)
    statuses = {e["public_id"]: e["status_type"] for e in list_r2.json()["data"]}
    assert statuses[pid] == "read"
    unread_count = sum(1 for s in statuses.values() if s == "unread")
    assert unread_count == 2


# ─── Flow 8: Event deletion cascades to datapoints ──────────────────────────


async def test_event_deletion_cascades(client, auth_headers, admin_user, active_plugin):
    """Create event → push datapoints → delete event → datapoints gone."""
    # Create event
    r = await client.post(
        "/api/v1/events",
        json={"name": "Cascade Sensor", "min_value": 0, "max_value": 100, "unit": "V", "type": "sensor"},
        headers=auth_headers,
    )
    assert r.status_code == 201

    # Find event
    list_r = await client.get("/api/v1/events", headers=auth_headers)
    evt = next(e for e in list_r.json()["data"] if e["name"] == "Cascade Sensor")

    # Link event to active plugin via channel mapping
    r = await client.post(
        f"/api/v1/plugins/{active_plugin.public_id}/channels",
        json={"channel_id": "ch-cascade", "channel_name": "Cascade", "direction": "input", "unit": "V", "event_public_id": evt["public_id"]},
        headers=auth_headers,
    )
    assert r.status_code == 201

    # Push a datapoint
    r = await client.post(
        "/api/v1/datapoints",
        json={"value": 42.0, "event_public_id": evt["public_id"]},
        headers=auth_headers,
    )
    assert r.status_code == 201

    # Verify datapoint exists
    dp_r = await client.get("/api/v1/datapoints", headers=auth_headers)
    assert dp_r.json()["total"] >= 1

    # Delete event
    r = await client.delete(f"/api/v1/events/{evt['public_id']}", headers=auth_headers)
    assert r.status_code == 200

    # Datapoints should be gone (cascade delete)
    dp_r2 = await client.get("/api/v1/datapoints", headers=auth_headers)
    remaining = [dp for dp in dp_r2.json()["data"] if dp["event_public_id"] == evt["public_id"]]
    assert len(remaining) == 0


# ─── Flow 9: Health endpoint always works ────────────────────────────────────


async def test_health_no_auth(client, admin_user):
    """Health endpoint works without authentication."""
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("healthy", "ok")
    assert "version" in data


# ─── Flow 10: Full CRUD cycle for every resource ───────────────────────────


async def test_full_crud_events(client, auth_headers, admin_user):
    """Events: create → list → get → update → delete → get(404)."""
    base = "/api/v1/events"

    # Create
    r = await client.post(
        base,
        json={"name": "CRUD Sensor", "min_value": 0, "max_value": 50, "unit": "mA", "type": "actuator"},
        headers=auth_headers,
    )
    assert r.status_code == 201

    # List
    list_r = await client.get(base, headers=auth_headers)
    evt = list_r.json()["data"][0]
    pid = evt["public_id"]

    # Get
    r = await client.get(f"{base}/{pid}", headers=auth_headers)
    assert r.json()["name"] == "CRUD Sensor"
    assert r.json()["type"] == "actuator"

    # Update
    r = await client.put(f"{base}/{pid}", json={"name": "Updated Sensor"}, headers=auth_headers)
    assert r.status_code == 200

    r = await client.get(f"{base}/{pid}", headers=auth_headers)
    assert r.json()["name"] == "Updated Sensor"

    # Delete
    r = await client.delete(f"{base}/{pid}", headers=auth_headers)
    assert r.status_code == 200

    # Confirm 404
    r = await client.get(f"{base}/{pid}", headers=auth_headers)
    assert r.status_code == 404
