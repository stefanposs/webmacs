"""Tests for User management CRUD API (admin endpoints)."""

import pytest

from tests.conftest import ADMIN_EMAIL, ADMIN_USERNAME

pytestmark = pytest.mark.anyio

BASE = "/api/v1/users"


# ─── Create ──────────────────────────────────────────────────────────────────


async def test_create_user(client, auth_headers, admin_user):
    """POST /users creates a new user (admin only)."""
    r = await client.post(
        BASE,
        json={"email": "new@test.io", "username": "newuser", "password": "securepass123"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "success"


async def test_create_user_duplicate_email(client, auth_headers, admin_user):
    """POST /users rejects duplicate email."""
    r = await client.post(
        BASE,
        json={"email": ADMIN_EMAIL, "username": "different", "password": "securepass123"},
        headers=auth_headers,
    )
    assert r.status_code == 409


async def test_create_user_short_password(client, auth_headers, admin_user):
    """POST /users rejects password < 8 chars."""
    r = await client.post(
        BASE,
        json={"email": "short@test.io", "username": "shortpw", "password": "1234567"},
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_create_user_invalid_email(client, auth_headers, admin_user):
    """POST /users rejects malformed email."""
    r = await client.post(
        BASE,
        json={"email": "not-an-email", "username": "bademail", "password": "securepass123"},
        headers=auth_headers,
    )
    assert r.status_code == 422


async def test_create_user_short_username(client, auth_headers, admin_user):
    """POST /users rejects username < 2 chars."""
    r = await client.post(
        BASE,
        json={"email": "ok@test.io", "username": "x", "password": "securepass123"},
        headers=auth_headers,
    )
    assert r.status_code == 422


# ─── List (admin only) ──────────────────────────────────────────────────────


async def test_list_users(client, auth_headers, admin_user):
    """GET /users returns paginated list (admin only)."""
    r = await client.get(BASE, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["data"][0]["email"] == ADMIN_EMAIL


async def test_list_users_requires_admin(client, auth_headers, db_session, admin_user):
    """GET /users rejects non-admin users."""
    # Create a non-admin user via API (requires admin)
    await client.post(
        BASE,
        json={"email": "regular@test.io", "username": "regular", "password": "securepass123"},
        headers=auth_headers,
    )
    # Login as non-admin
    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": "regular@test.io", "password": "securepass123"},
    )
    token = login_r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(BASE, headers=headers)
    assert r.status_code == 403


# ─── Get ─────────────────────────────────────────────────────────────────────


async def test_get_user(client, auth_headers, admin_user):
    """GET /users/{id} returns a single user."""
    r = await client.get(f"{BASE}/{admin_user.public_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["username"] == ADMIN_USERNAME


async def test_get_user_not_found(client, auth_headers, admin_user):
    """GET /users/{id} returns 404 for missing user."""
    r = await client.get(f"{BASE}/nonexistent", headers=auth_headers)
    assert r.status_code == 404


# ─── Update ──────────────────────────────────────────────────────────────────


async def test_update_user_email(client, auth_headers, admin_user):
    """PUT /users/{id} updates email."""
    r = await client.put(
        f"{BASE}/{admin_user.public_id}",
        json={"email": "updated@test.io"},
        headers=auth_headers,
    )
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{admin_user.public_id}", headers=auth_headers)
    assert get_r.json()["email"] == "updated@test.io"


async def test_update_user_username(client, auth_headers, admin_user):
    """PUT /users/{id} updates username."""
    r = await client.put(
        f"{BASE}/{admin_user.public_id}",
        json={"username": "newadmin"},
        headers=auth_headers,
    )
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{admin_user.public_id}", headers=auth_headers)
    assert get_r.json()["username"] == "newadmin"


async def test_update_user_password(client, auth_headers, admin_user):
    """PUT /users/{id} updates password (verifiable via re-login)."""
    new_pw = "updatedpass123"
    r = await client.put(
        f"{BASE}/{admin_user.public_id}",
        json={"password": new_pw},
        headers=auth_headers,
    )
    assert r.status_code == 200

    # Re-login with new password should succeed
    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": new_pw},
    )
    assert login_r.status_code == 200


async def test_update_user_not_found(client, auth_headers, admin_user):
    """PUT /users/{id} returns 404 for missing user."""
    r = await client.put(
        f"{BASE}/nonexistent",
        json={"email": "nope@test.io"},
        headers=auth_headers,
    )
    assert r.status_code == 404


# ─── Delete (admin only) ────────────────────────────────────────────────────


async def test_delete_user(client, auth_headers, admin_user):
    """DELETE /users/{id} removes a user (admin only)."""
    # Create a user to delete (requires admin)
    await client.post(
        BASE,
        json={"email": "delete@test.io", "username": "deleteme", "password": "securepass123"},
        headers=auth_headers,
    )
    list_r = await client.get(BASE, headers=auth_headers)
    victim = next(u for u in list_r.json()["data"] if u["email"] == "delete@test.io")

    r = await client.delete(f"{BASE}/{victim['public_id']}", headers=auth_headers)
    assert r.status_code == 200

    get_r = await client.get(f"{BASE}/{victim['public_id']}", headers=auth_headers)
    assert get_r.status_code == 404


async def test_delete_user_not_found(client, auth_headers, admin_user):
    """DELETE /users/{id} returns 404 for missing user."""
    r = await client.delete(f"{BASE}/nonexistent", headers=auth_headers)
    assert r.status_code == 404


async def test_delete_requires_admin(client, auth_headers, db_session, admin_user):
    """DELETE /users/{id} rejects non-admin users."""
    # Create a non-admin user (requires admin)
    await client.post(
        BASE,
        json={"email": "regular2@test.io", "username": "regular2", "password": "securepass123"},
        headers=auth_headers,
    )
    login_r = await client.post(
        "/api/v1/auth/login",
        json={"email": "regular2@test.io", "password": "securepass123"},
    )
    token = login_r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.delete(f"{BASE}/{admin_user.public_id}", headers=headers)
    assert r.status_code == 403


# ─── Auth ────────────────────────────────────────────────────────────────────


async def test_users_list_requires_auth(client):
    """GET /users requires authentication."""
    r = await client.get(BASE)
    assert r.status_code == 401
