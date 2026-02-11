"""Tests for Logging CRUD API."""

import pytest

pytestmark = pytest.mark.anyio

BASE = "/api/v1/logging"


# ─── Create ──────────────────────────────────────────────────────────────────


async def test_create_log_entry(client, auth_headers, admin_user):
    """POST /logging creates a new log entry with default type=info."""
    r = await client.post(
        BASE,
        json={"content": "System started successfully"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "success"


async def test_create_log_entry_with_type(client, auth_headers, admin_user):
    """POST /logging respects logging_type field."""
    r = await client.post(
        BASE,
        json={"content": "Disk almost full", "logging_type": "warning"},
        headers=auth_headers,
    )
    assert r.status_code == 201


async def test_create_log_entry_error_type(client, auth_headers, admin_user):
    """POST /logging accepts error type."""
    r = await client.post(
        BASE,
        json={"content": "Critical failure", "logging_type": "error"},
        headers=auth_headers,
    )
    assert r.status_code == 201


async def test_create_log_entry_empty_content(client, auth_headers, admin_user):
    """POST /logging rejects empty content."""
    r = await client.post(
        BASE,
        json={"content": ""},
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_create_log_entry_invalid_type(client, auth_headers, admin_user):
    """POST /logging rejects invalid logging_type."""
    r = await client.post(
        BASE,
        json={"content": "Test", "logging_type": "nonexistent"},
        headers=auth_headers,
    )
    assert r.status_code == 422


# ─── List ────────────────────────────────────────────────────────────────────


async def test_list_log_entries(client, auth_headers, admin_user):
    """GET /logging returns paginated list."""
    await client.post(BASE, json={"content": "Log 1"}, headers=auth_headers)
    await client.post(BASE, json={"content": "Log 2"}, headers=auth_headers)

    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["data"]) == 2


async def test_list_log_entries_pagination(client, auth_headers, admin_user):
    """GET /logging pagination works correctly."""
    for i in range(3):
        await client.post(BASE, json={"content": f"Log {i}"}, headers=auth_headers)

    r = await client.get(f"{BASE}?page=1&page_size=2", headers=auth_headers)
    data = r.json()
    assert data["total"] == 3
    assert len(data["data"]) == 2

    r2 = await client.get(f"{BASE}?page=2&page_size=2", headers=auth_headers)
    data2 = r2.json()
    assert len(data2["data"]) == 1


# ─── Get ─────────────────────────────────────────────────────────────────────


async def test_get_log_entry(client, auth_headers, admin_user):
    """GET /logging/{id} returns a single log entry."""
    await client.post(BASE, json={"content": "FindMe"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    entry = list_r.json()["data"][0]

    r = await client.get(f"{BASE}/{entry['public_id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["content"] == "FindMe"


async def test_get_log_entry_not_found(client, auth_headers, admin_user):
    """GET /logging/{id} returns 404 for missing entry."""
    r = await client.get(f"{BASE}/nonexistent", headers=auth_headers)
    assert r.status_code == 404


# ─── Update ──────────────────────────────────────────────────────────────────


async def test_update_log_entry_status(client, auth_headers, admin_user):
    """PUT /logging/{id} updates status_type."""
    await client.post(BASE, json={"content": "Unread log"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    entry = list_r.json()["data"][0]

    r = await client.put(
        f"{BASE}/{entry['public_id']}",
        json={"status_type": "read"},
        headers=auth_headers,
    )
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{entry['public_id']}", headers=auth_headers)
    assert get_r.json()["status_type"] == "read"


async def test_update_log_entry_content(client, auth_headers, admin_user):
    """PUT /logging/{id} updates content."""
    await client.post(BASE, json={"content": "Original"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    entry = list_r.json()["data"][0]

    r = await client.put(
        f"{BASE}/{entry['public_id']}",
        json={"content": "Updated content"},
        headers=auth_headers,
    )
    assert r.status_code == 200


async def test_update_log_entry_not_found(client, auth_headers, admin_user):
    """PUT /logging/{id} returns 404 for missing entry."""
    r = await client.put(
        f"{BASE}/nonexistent",
        json={"status_type": "read"},
        headers=auth_headers,
    )
    assert r.status_code == 404


# ─── Auth ────────────────────────────────────────────────────────────────────


async def test_logging_requires_auth(client):
    """Logging endpoints require authentication."""
    r = await client.get(BASE)
    assert r.status_code == 401


# ─── Ordering ────────────────────────────────────────────────────────────────


async def test_list_log_entries_ordered_newest_first(client, auth_headers, admin_user):
    """GET /logging returns entries ordered by created_on DESC (newest first)."""
    await client.post(BASE, json={"content": "First"}, headers=auth_headers)
    await client.post(BASE, json={"content": "Second"}, headers=auth_headers)
    await client.post(BASE, json={"content": "Third"}, headers=auth_headers)

    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()["data"]
    assert len(entries) == 3
    # Most recent entry should come first
    assert entries[0]["content"] == "Third"
    assert entries[2]["content"] == "First"


# ─── Auto-logging on login ──────────────────────────────────────────────────


async def test_login_creates_log_entry(client, admin_user):
    """POST /auth/login creates an audit log entry."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "adminpass123"},
    )
    assert r.status_code == 200

    # Now check that a log entry was created
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    logs_r = await client.get(BASE, headers=headers)
    assert logs_r.status_code == 200
    entries = logs_r.json()["data"]
    assert any("logged in" in e["content"] for e in entries)


# ─── Auto-logging on experiment lifecycle ────────────────────────────────────


async def test_experiment_create_creates_log_entry(client, auth_headers, admin_user):
    """POST /experiments creates a log entry."""
    r = await client.post(
        "/api/v1/experiments",
        json={"name": "AutoLogExperiment"},
        headers=auth_headers,
    )
    assert r.status_code == 201

    logs_r = await client.get(BASE, headers=auth_headers)
    entries = logs_r.json()["data"]
    assert any("AutoLogExperiment" in e["content"] and "started" in e["content"] for e in entries)


async def test_experiment_stop_creates_log_entry(client, auth_headers, admin_user):
    """PUT /experiments/{id}/stop creates a log entry."""
    # Create experiment
    await client.post(
        "/api/v1/experiments",
        json={"name": "StopLogExperiment"},
        headers=auth_headers,
    )
    list_r = await client.get("/api/v1/experiments", headers=auth_headers)
    exp = list_r.json()["data"][0]

    # Stop it
    r = await client.put(f"/api/v1/experiments/{exp['public_id']}/stop", headers=auth_headers)
    assert r.status_code == 200

    logs_r = await client.get(BASE, headers=auth_headers)
    entries = logs_r.json()["data"]
    assert any("StopLogExperiment" in e["content"] and "stopped" in e["content"] for e in entries)
