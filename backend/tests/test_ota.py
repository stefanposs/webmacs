"""Tests for OTA firmware update service and API."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from webmacs_backend.enums import UpdateStatus
from webmacs_backend.services.ota_service import compare_versions, get_current_version, verify_update

if TYPE_CHECKING:
    from httpx import AsyncClient

    from webmacs_backend.models import FirmwareUpdate, User

pytestmark = pytest.mark.anyio

# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests — compare_versions
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    ("current", "candidate", "expected"),
    [
        ("1.0.0", "2.0.0", True),
        ("2.0.0", "2.1.0", True),
        ("2.0.0", "2.0.1", True),
        ("2.1.0", "2.0.0", False),
        ("2.0.0", "2.0.0", False),
        ("1.0.0", "1.0.0", False),
        ("10.0.0", "9.9.9", False),
        ("0.9.9", "1.0.0", True),
    ],
)
def test_compare_versions(current: str, candidate: str, expected: bool) -> None:
    """compare_versions returns True only when candidate > current."""
    assert compare_versions(current, candidate) is expected


def test_get_current_version() -> None:
    """get_current_version returns a non-empty semver string."""
    version = get_current_version()
    assert version
    parts = version.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests — verify_update
# ═══════════════════════════════════════════════════════════════════════════════


def test_verify_update_correct_hash() -> None:
    """verify_update returns True when the SHA-256 hash matches."""
    content = b"firmware binary content for testing"
    expected_hash = hashlib.sha256(content).hexdigest()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        assert verify_update(tmp_path, expected_hash) is True
    finally:
        Path(tmp_path).unlink()


def test_verify_update_wrong_hash() -> None:
    """verify_update returns False when the SHA-256 hash does not match."""
    content = b"firmware binary content for testing"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        assert verify_update(tmp_path, "0" * 64) is False
    finally:
        Path(tmp_path).unlink()


def test_verify_update_missing_file() -> None:
    """verify_update returns False when the file does not exist."""
    assert verify_update("/nonexistent/firmware.bin", "abc123") is False


# ═══════════════════════════════════════════════════════════════════════════════
# API tests — OTA CRUD
# ═══════════════════════════════════════════════════════════════════════════════


async def test_create_firmware_update(
    client: AsyncClient, auth_headers: dict[str, str], admin_user: User
) -> None:
    """POST /api/v1/ota creates a firmware record (201)."""
    response = await client.post(
        "/api/v1/ota",
        json={"version": "3.0.0", "changelog": "Major release"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "Firmware" in data["message"]


async def test_create_firmware_update_duplicate_version(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """POST /api/v1/ota rejects duplicate version (409)."""
    response = await client.post(
        "/api/v1/ota",
        json={"version": "2.1.0"},
        headers=auth_headers,
    )
    assert response.status_code == 409


async def test_create_firmware_update_invalid_version(
    client: AsyncClient, auth_headers: dict[str, str], admin_user: User
) -> None:
    """POST /api/v1/ota rejects non-semver version strings (422)."""
    response = await client.post(
        "/api/v1/ota",
        json={"version": "not-semver"},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_list_firmware_updates(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """GET /api/v1/ota returns paginated list (200)."""
    response = await client.get("/api/v1/ota", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["data"][0]["version"] == "2.1.0"
    assert data["data"][0]["status"] == UpdateStatus.pending


async def test_get_firmware_update(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """GET /api/v1/ota/{id} returns a single firmware update (200)."""
    response = await client.get("/api/v1/ota/fw-update-001", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "2.1.0"
    assert data["changelog"] == "Bug fixes and improvements"


async def test_get_firmware_update_not_found(
    client: AsyncClient, auth_headers: dict[str, str], admin_user: User
) -> None:
    """GET /api/v1/ota/{id} returns 404 for missing firmware update."""
    response = await client.get("/api/v1/ota/nonexistent", headers=auth_headers)
    assert response.status_code == 404


async def test_check_for_updates_with_pending(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """GET /api/v1/ota/check returns update_available=True when newer version exists."""
    response = await client.get("/api/v1/ota/check", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["current_version"] == "2.0.0"
    assert data["latest_version"] == "2.1.0"
    assert data["update_available"] is True


async def test_check_for_updates_without_pending(
    client: AsyncClient, auth_headers: dict[str, str], admin_user: User
) -> None:
    """GET /api/v1/ota/check returns update_available=False when no updates exist."""
    response = await client.get("/api/v1/ota/check", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["update_available"] is False
    assert data["latest_version"] is None


async def test_apply_firmware_update(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """POST /api/v1/ota/{id}/apply marks update as completed (200)."""
    response = await client.post("/api/v1/ota/fw-update-001/apply", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify status changed
    detail = await client.get("/api/v1/ota/fw-update-001", headers=auth_headers)
    assert detail.json()["status"] == UpdateStatus.completed


async def test_rollback_firmware_update(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """POST /api/v1/ota/{id}/rollback marks update as rolled_back (200)."""
    # First apply (pending → completed)
    apply_resp = await client.post("/api/v1/ota/fw-update-001/apply", headers=auth_headers)
    assert apply_resp.status_code == 200

    # Then rollback (completed → rolled_back)
    response = await client.post("/api/v1/ota/fw-update-001/rollback", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify status changed
    detail = await client.get("/api/v1/ota/fw-update-001", headers=auth_headers)
    assert detail.json()["status"] == UpdateStatus.rolled_back


async def test_delete_firmware_update(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """DELETE /api/v1/ota/{id} deletes the record (200)."""
    response = await client.delete("/api/v1/ota/fw-update-001", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify gone
    detail = await client.get("/api/v1/ota/fw-update-001", headers=auth_headers)
    assert detail.status_code == 404


async def test_ota_endpoints_require_auth(client: AsyncClient) -> None:
    """OTA endpoints return 401 without authentication."""
    assert (await client.get("/api/v1/ota")).status_code == 401
    assert (await client.post("/api/v1/ota", json={"version": "1.0.0"})).status_code == 401
    assert (await client.get("/api/v1/ota/check")).status_code == 401
    assert (await client.get("/api/v1/ota/some-id")).status_code == 401
    assert (await client.post("/api/v1/ota/some-id/apply")).status_code == 401
    assert (await client.post("/api/v1/ota/some-id/rollback")).status_code == 401
    assert (await client.delete("/api/v1/ota/some-id")).status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# State machine tests
# ═════════════════════════════════════════════════════════════════════════════


async def test_apply_already_completed_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """POST /api/v1/ota/{id}/apply returns 409 on invalid state transition."""
    # Apply once (pending → completed)
    resp1 = await client.post("/api/v1/ota/fw-update-001/apply", headers=auth_headers)
    assert resp1.status_code == 200

    # Apply again (completed → completed is not allowed)
    resp2 = await client.post("/api/v1/ota/fw-update-001/apply", headers=auth_headers)
    assert resp2.status_code == 409


async def test_rollback_pending_returns_409(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """POST /api/v1/ota/{id}/rollback returns 409 when update was never applied."""
    response = await client.post("/api/v1/ota/fw-update-001/rollback", headers=auth_headers)
    assert response.status_code == 409


async def test_firmware_response_hides_file_path(
    client: AsyncClient,
    auth_headers: dict[str, str],
    admin_user: User,
    sample_firmware_update: FirmwareUpdate,
) -> None:
    """Response includes has_firmware_file but not file_path."""
    response = await client.get("/api/v1/ota/fw-update-001", headers=auth_headers)
    data = response.json()
    assert "file_path" not in data
    assert data["has_firmware_file"] is False


@pytest.mark.parametrize(
    ("current", "candidate", "expected"),
    [
        ("1.0.0", "abc", False),
        ("abc", "1.0.0", False),
        ("1.0", "2.0.0", False),
        ("", "1.0.0", False),
        ("1.0.0", "", False),
    ],
)
def test_compare_versions_malformed_input(current: str, candidate: str, expected: bool) -> None:
    """compare_versions returns False for malformed input."""
    assert compare_versions(current, candidate) is expected
