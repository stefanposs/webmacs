"""Tests for Experiment CRUD API + stop + CSV export."""

import pytest

pytestmark = pytest.mark.anyio

BASE = "/api/v1/experiments"


# ─── CRUD ────────────────────────────────────────────────────────────────────


async def test_create_experiment(client, auth_headers, admin_user):
    """POST /experiments creates a new experiment."""
    r = await client.post(BASE, json={"name": "Experiment Alpha"}, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["status"] == "success"


async def test_create_multiple_experiments(client, auth_headers, admin_user):
    """POST /experiments allows creating multiple experiments with different names."""
    r1 = await client.post(BASE, json={"name": "Experiment A"}, headers=auth_headers)
    r2 = await client.post(BASE, json={"name": "Experiment B"}, headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201

    list_r = await client.get(BASE, headers=auth_headers)
    assert list_r.json()["total"] == 2


async def test_create_experiment_empty_name(client, auth_headers, admin_user):
    """POST /experiments rejects empty name."""
    r = await client.post(BASE, json={"name": ""}, headers=auth_headers)
    assert r.status_code == 422


async def test_list_experiments(client, auth_headers, admin_user):
    """GET /experiments returns paginated list."""
    await client.post(BASE, json={"name": "Exp1"}, headers=auth_headers)
    await client.post(BASE, json={"name": "Exp2"}, headers=auth_headers)
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["data"]) == 2
    assert data["page"] == 1


async def test_list_experiments_pagination(client, auth_headers, admin_user):
    """GET /experiments?page_size=1 paginates correctly."""
    await client.post(BASE, json={"name": "ExpA"}, headers=auth_headers)
    await client.post(BASE, json={"name": "ExpB"}, headers=auth_headers)
    r = await client.get(f"{BASE}?page=1&page_size=1", headers=auth_headers)
    data = r.json()
    assert data["total"] == 2
    assert len(data["data"]) == 1
    assert data["page_size"] == 1


async def test_get_experiment(client, auth_headers, admin_user):
    """GET /experiments/{id} returns a single experiment."""
    # Create and find the public_id
    await client.post(BASE, json={"name": "GetMe"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    exp = list_r.json()["data"][0]

    r = await client.get(f"{BASE}/{exp['public_id']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "GetMe"


async def test_get_experiment_not_found(client, auth_headers, admin_user):
    """GET /experiments/{id} returns 404 for missing experiment."""
    r = await client.get(f"{BASE}/nonexistent", headers=auth_headers)
    assert r.status_code == 404


async def test_update_experiment(client, auth_headers, admin_user):
    """PUT /experiments/{id} updates experiment name."""
    await client.post(BASE, json={"name": "OldName"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    pid = list_r.json()["data"][0]["public_id"]

    r = await client.put(f"{BASE}/{pid}", json={"name": "NewName"}, headers=auth_headers)
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert get_r.json()["name"] == "NewName"


async def test_delete_experiment(client, auth_headers, admin_user):
    """DELETE /experiments/{id} removes experiment."""
    await client.post(BASE, json={"name": "DeleteMe"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    pid = list_r.json()["data"][0]["public_id"]

    r = await client.delete(f"{BASE}/{pid}", headers=auth_headers)
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert get_r.status_code == 404


async def test_delete_experiment_not_found(client, auth_headers, admin_user):
    """DELETE /experiments/{id} returns 404 for missing experiment."""
    r = await client.delete(f"{BASE}/nonexistent", headers=auth_headers)
    assert r.status_code == 404


# ─── Stop ────────────────────────────────────────────────────────────────────


async def test_stop_experiment(client, auth_headers, admin_user):
    """PUT /experiments/{id}/stop sets stopped_on timestamp."""
    await client.post(BASE, json={"name": "StopMe"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    pid = list_r.json()["data"][0]["public_id"]

    r = await client.put(f"{BASE}/{pid}/stop", headers=auth_headers)
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{pid}", headers=auth_headers)
    assert get_r.json()["stopped_on"] is not None


async def test_stop_experiment_not_found(client, auth_headers, admin_user):
    """PUT /experiments/{id}/stop returns 404 for missing experiment."""
    r = await client.put(f"{BASE}/nonexistent/stop", headers=auth_headers)
    assert r.status_code == 404


# ─── CSV Export ──────────────────────────────────────────────────────────────


async def test_export_csv_empty(client, auth_headers, admin_user):
    """GET /experiments/{id}/export/csv returns CSV with headers only for empty experiment."""
    await client.post(BASE, json={"name": "EmptyCSV"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    pid = list_r.json()["data"][0]["public_id"]

    r = await client.get(f"{BASE}/{pid}/export/csv", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "timestamp" in r.text  # CSV header row


async def test_export_csv_with_data(client, auth_headers, admin_user, sample_event):
    """GET /experiments/{id}/export/csv includes datapoints."""
    # Create experiment (becomes active since stopped_on is None)
    await client.post(BASE, json={"name": "DataCSV"}, headers=auth_headers)
    list_r = await client.get(BASE, headers=auth_headers)
    pid = list_r.json()["data"][0]["public_id"]

    # Create a datapoint linked to the active experiment
    await client.post(
        "/api/v1/datapoints",
        json={"value": 42.5, "event_public_id": sample_event.public_id},
        headers=auth_headers,
    )

    r = await client.get(f"{BASE}/{pid}/export/csv", headers=auth_headers)
    assert r.status_code == 200
    lines = r.text.strip().split("\n")
    assert len(lines) >= 2  # header + at least 1 data row
    assert "42.5" in lines[1]


async def test_export_csv_not_found(client, auth_headers, admin_user):
    """GET /experiments/{id}/export/csv returns 404 for missing experiment."""
    r = await client.get(f"{BASE}/nonexistent/export/csv", headers=auth_headers)
    assert r.status_code == 404


# ─── Auth ────────────────────────────────────────────────────────────────────


async def test_experiments_require_auth(client):
    """Experiment endpoints require authentication."""
    r = await client.get(BASE)
    assert r.status_code == 401
