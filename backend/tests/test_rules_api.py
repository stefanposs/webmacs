"""Tests for Rule CRUD API (Event Engine LITE endpoints)."""

import pytest

pytestmark = pytest.mark.anyio

BASE = "/api/v1/rules"


# ─── Create ──────────────────────────────────────────────────────────────────


async def test_create_rule(client, auth_headers, admin_user, sample_event):
    """POST /rules creates a rule (admin only)."""
    r = await client.post(
        BASE,
        json={
            "name": "High Temp Rule",
            "event_public_id": sample_event.public_id,
            "operator": "gt",
            "threshold": 80.0,
            "action_type": "webhook",
            "webhook_event_type": "sensor.threshold_exceeded",
            "cooldown_seconds": 30,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "success"


async def test_create_rule_with_log_action(client, auth_headers, admin_user, sample_event):
    """POST /rules allows action_type=log."""
    r = await client.post(
        BASE,
        json={
            "name": "Low Temp Log",
            "event_public_id": sample_event.public_id,
            "operator": "lt",
            "threshold": 10.0,
            "action_type": "log",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201


async def test_create_rule_between(client, auth_headers, admin_user, sample_event):
    """POST /rules with between operator requires threshold_high."""
    r = await client.post(
        BASE,
        json={
            "name": "Normal Range",
            "event_public_id": sample_event.public_id,
            "operator": "between",
            "threshold": 20.0,
            "threshold_high": 80.0,
            "action_type": "webhook",
            "webhook_event_type": "sensor.threshold_exceeded",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201


async def test_create_rule_between_missing_high(client, auth_headers, admin_user, sample_event):
    """POST /rules rejects between without threshold_high."""
    r = await client.post(
        BASE,
        json={
            "name": "Bad Between",
            "event_public_id": sample_event.public_id,
            "operator": "between",
            "threshold": 20.0,
            "action_type": "webhook",
            "webhook_event_type": "sensor.threshold_exceeded",
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_create_rule_between_high_less_than_low(client, auth_headers, admin_user, sample_event):
    """POST /rules rejects threshold_high < threshold."""
    r = await client.post(
        BASE,
        json={
            "name": "Bad Range",
            "event_public_id": sample_event.public_id,
            "operator": "between",
            "threshold": 80.0,
            "threshold_high": 20.0,
            "action_type": "webhook",
            "webhook_event_type": "sensor.threshold_exceeded",
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_create_rule_duplicate_name(client, auth_headers, admin_user, sample_event):
    """POST /rules rejects duplicate rule name."""
    payload = {
        "name": "Unique Rule",
        "event_public_id": sample_event.public_id,
        "operator": "gt",
        "threshold": 50.0,
        "action_type": "webhook",
        "webhook_event_type": "sensor.threshold_exceeded",
    }
    await client.post(BASE, json=payload, headers=auth_headers)
    r = await client.post(BASE, json=payload, headers=auth_headers)
    assert r.status_code == 409


async def test_create_rule_invalid_event(client, auth_headers, admin_user):
    """POST /rules returns 404 for non-existent event."""
    r = await client.post(
        BASE,
        json={
            "name": "Orphan Rule",
            "event_public_id": "nonexistent-event",
            "operator": "gt",
            "threshold": 50.0,
            "action_type": "webhook",
            "webhook_event_type": "sensor.threshold_exceeded",
        },
        headers=auth_headers,
    )
    assert r.status_code == 404


async def test_create_rule_invalid_operator(client, auth_headers, admin_user, sample_event):
    """POST /rules rejects invalid operator."""
    r = await client.post(
        BASE,
        json={
            "name": "Bad Op",
            "event_public_id": sample_event.public_id,
            "operator": "invalid_op",
            "threshold": 50.0,
            "action_type": "webhook",
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_create_rule_all_operators(client, auth_headers, admin_user, sample_event):
    """POST /rules accepts all valid operators."""
    for i, op in enumerate(["gt", "lt", "eq", "gte", "lte"]):
        r = await client.post(
            BASE,
            json={
                "name": f"Rule {op} {i}",
                "event_public_id": sample_event.public_id,
                "operator": op,
                "threshold": 50.0,
                "action_type": "log",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, f"Failed for operator {op}"


# ─── List ────────────────────────────────────────────────────────────────────


async def test_list_rules(client, auth_headers, admin_user, sample_rule):
    """GET /rules returns paginated list (admin only)."""
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["data"][0]["name"] == "High Temperature Alert"


async def test_list_rules_pagination(client, auth_headers, admin_user, sample_event):
    """GET /rules pagination works correctly."""
    for i in range(3):
        await client.post(
            BASE,
            json={
                "name": f"Page Rule {i}",
                "event_public_id": sample_event.public_id,
                "operator": "gt",
                "threshold": float(i),
                "action_type": "log",
            },
            headers=auth_headers,
        )
    r = await client.get(f"{BASE}?page=1&page_size=2", headers=auth_headers)
    data = r.json()
    assert data["total"] == 3
    assert len(data["data"]) == 2


# ─── Get ─────────────────────────────────────────────────────────────────────


async def test_get_rule(client, auth_headers, admin_user, sample_rule):
    """GET /rules/{id} returns a single rule."""
    r = await client.get(f"{BASE}/{sample_rule.public_id}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "High Temperature Alert"
    assert data["operator"] == "gt"
    assert data["threshold"] == 100.0
    assert data["action_type"] == "webhook"


async def test_get_rule_not_found(client, auth_headers, admin_user):
    """GET /rules/{id} returns 404 for missing rule."""
    r = await client.get(f"{BASE}/nonexistent", headers=auth_headers)
    assert r.status_code == 404


# ─── Update ──────────────────────────────────────────────────────────────────


async def test_update_rule_threshold(client, auth_headers, admin_user, sample_rule):
    """PUT /rules/{id} updates threshold."""
    r = await client.put(
        f"{BASE}/{sample_rule.public_id}",
        json={"threshold": 150.0},
        headers=auth_headers,
    )
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{sample_rule.public_id}", headers=auth_headers)
    assert get_r.json()["threshold"] == 150.0


async def test_update_rule_disable(client, auth_headers, admin_user, sample_rule):
    """PUT /rules/{id} can disable a rule."""
    r = await client.put(
        f"{BASE}/{sample_rule.public_id}",
        json={"enabled": False},
        headers=auth_headers,
    )
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{sample_rule.public_id}", headers=auth_headers)
    assert get_r.json()["enabled"] is False


async def test_update_rule_operator(client, auth_headers, admin_user, sample_rule):
    """PUT /rules/{id} updates operator."""
    r = await client.put(
        f"{BASE}/{sample_rule.public_id}",
        json={"operator": "gte"},
        headers=auth_headers,
    )
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{sample_rule.public_id}", headers=auth_headers)
    assert get_r.json()["operator"] == "gte"


async def test_update_rule_not_found(client, auth_headers, admin_user):
    """PUT /rules/{id} returns 404 for missing rule."""
    r = await client.put(
        f"{BASE}/nonexistent",
        json={"threshold": 99.0},
        headers=auth_headers,
    )
    assert r.status_code == 404


# ─── Delete ──────────────────────────────────────────────────────────────────


async def test_delete_rule(client, auth_headers, admin_user, sample_rule):
    """DELETE /rules/{id} removes rule."""
    r = await client.delete(f"{BASE}/{sample_rule.public_id}", headers=auth_headers)
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{sample_rule.public_id}", headers=auth_headers)
    assert get_r.status_code == 404


async def test_delete_rule_not_found(client, auth_headers, admin_user):
    """DELETE /rules/{id} returns 404 for missing rule."""
    r = await client.delete(f"{BASE}/nonexistent", headers=auth_headers)
    assert r.status_code == 404


# ─── Auth (admin required) ──────────────────────────────────────────────────


async def test_rules_require_admin(client):
    """Rule endpoints require admin authentication."""
    r = await client.get(BASE)
    assert r.status_code in (401, 403)


async def test_rules_reject_non_admin(client, auth_headers, db_session, admin_user):
    """Rule endpoints reject non-admin authenticated users."""
    # Create a non-admin user (requires admin)
    await client.post(
        "/api/v1/users",
        json={"email": "nonadmin@test.io", "username": "nonadmin", "password": "securepass123"},
        headers=auth_headers,
    )
    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonadmin@test.io", "password": "securepass123"},
    )
    token = login_r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(BASE, headers=headers)
    assert r.status_code == 403
