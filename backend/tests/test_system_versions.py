"""Tests for the /system/ endpoints (versions, trigger, update-progress).

These tests cover:
  - GET  /system/versions          — installed + available versions per service
  - POST /system/trigger           — write a trigger file for the updater
  - GET  /system/update-progress   — poll update status from shared file
  - IPC helpers: _write_trigger, _read_current_status, _extract_tag_from_image

All Docker and GitHub interactions are mocked. File-based IPC uses ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from webmacs_backend.schemas.system import UpdateProgressResponse
from webmacs_backend.services.version_detector import ServiceInfo

if TYPE_CHECKING:
    from httpx import AsyncClient

    from webmacs_backend.models import User

pytestmark = pytest.mark.anyio


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

_MOCK_VERSIONS: dict[str, ServiceInfo] = {
    "backend": ServiceInfo(installed="2.4.2", image="stefanposs/webmacs-backend:2.4.2", status="running"),
    "frontend": ServiceInfo(installed="2.4.2", image="stefanposs/webmacs-frontend:2.4.2", status="running"),
    "controller": ServiceInfo(installed="2.4.2", image="stefanposs/webmacs-controller:2.4.2", status="running"),
}


def _patch_versions(versions: dict[str, ServiceInfo] | None = None):
    """Patch ``get_all_service_versions`` to return ``versions`` (defaults to _MOCK_VERSIONS)."""
    return patch(
        "webmacs_backend.api.v1.system.versions.get_all_service_versions",
        return_value=versions or _MOCK_VERSIONS,
    )


def _patch_github(version: str | None = None):
    """Patch ``_get_github_latest`` to return the given ``version``."""
    from unittest.mock import AsyncMock

    return patch(
        "webmacs_backend.api.v1.system.versions._get_github_latest",
        new_callable=AsyncMock,
        return_value=version,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests — _extract_tag_from_image
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractTagFromImage:
    """Pure-function tests for ``_extract_tag_from_image``."""

    @pytest.mark.parametrize(
        ("image", "expected"),
        [
            ("stefanposs/webmacs-backend:2.4.2", "2.4.2"),
            ("registry:5000/repo:v1", "v1"),
            ("my-img:latest", "latest"),
            ("my-img", None),
            ("my-img@sha256:abc123", None),
            (None, None),
            ("", None),
        ],
    )
    def test_extract_tag(self, image: str | None, expected: str | None) -> None:
        from webmacs_backend.api.v1.system.versions import _extract_tag_from_image

        assert _extract_tag_from_image(image) == expected


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests — _read_current_status / _write_trigger
# ═══════════════════════════════════════════════════════════════════════════════


class TestFilIPC:
    """Test file-based IPC helpers with a temporary directory."""

    def test_read_status_missing_file_returns_idle(self, tmp_path: Path) -> None:
        """When no status file exists, return idle."""
        with patch("webmacs_backend.api.v1.system.versions._STATUS_FILE", tmp_path / "status.json"):
            from webmacs_backend.api.v1.system.versions import _read_current_status

            result = _read_current_status()
            assert result.overall_status == "idle"
            assert result.services == {}

    def test_read_status_valid_file(self, tmp_path: Path) -> None:
        """Reading a valid status file returns the serialised state."""
        status_file = tmp_path / "update-status.json"
        payload = {
            "overall_status": "pulling",
            "services": {"backend": "updating", "frontend": "updating", "controller": "updating"},
            "current_step": "Pulling images…",
            "started_at": "2026-03-01T12:00:00+00:00",
        }
        status_file.write_text(json.dumps(payload))

        with patch("webmacs_backend.api.v1.system.versions._STATUS_FILE", status_file):
            from webmacs_backend.api.v1.system.versions import _read_current_status

            result = _read_current_status()
            assert result.overall_status == "pulling"
            assert result.services["backend"] == "updating"

    def test_read_status_malformed_json_returns_idle(self, tmp_path: Path) -> None:
        """If the status file contains invalid JSON, return idle gracefully."""
        status_file = tmp_path / "update-status.json"
        status_file.write_text("not-json{{{")

        with patch("webmacs_backend.api.v1.system.versions._STATUS_FILE", status_file):
            from webmacs_backend.api.v1.system.versions import _read_current_status

            result = _read_current_status()
            assert result.overall_status == "idle"

    def test_write_trigger_creates_file(self, tmp_path: Path) -> None:
        """_write_trigger writes trigger.json to the update dir."""
        trigger_file = tmp_path / "trigger.json"

        with (
            patch("webmacs_backend.api.v1.system.versions._TRIGGER_FILE", trigger_file),
            patch("webmacs_backend.api.v1.system.versions._UPDATE_DIR", tmp_path),
        ):
            from webmacs_backend.api.v1.system.versions import _write_trigger
            from webmacs_backend.schemas.system import UpdateTriggerRequest

            req = UpdateTriggerRequest(
                backend_image="stefanposs/webmacs-backend:2.5.0",
                frontend_image="stefanposs/webmacs-frontend:2.5.0",
                version="2.5.0",
            )
            _write_trigger(req)

            assert trigger_file.exists()
            data = json.loads(trigger_file.read_text())
            assert data["version"] == "2.5.0"
            assert len(data["images"]) == 2

    def test_write_trigger_raises_when_pending(self, tmp_path: Path) -> None:
        """_write_trigger raises RuntimeError when trigger.json already exists."""
        trigger_file = tmp_path / "trigger.json"
        trigger_file.write_text("{}")

        with (
            patch("webmacs_backend.api.v1.system.versions._TRIGGER_FILE", trigger_file),
            patch("webmacs_backend.api.v1.system.versions._UPDATE_DIR", tmp_path),
        ):
            from webmacs_backend.api.v1.system.versions import _write_trigger
            from webmacs_backend.schemas.system import UpdateTriggerRequest

            req = UpdateTriggerRequest(version="2.5.0")
            with pytest.raises(RuntimeError, match="already pending"):
                _write_trigger(req)


# ═══════════════════════════════════════════════════════════════════════════════
# API tests — GET /system/versions
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetVersions:
    """Integration tests for ``GET /api/v1/system/versions``."""

    async def test_returns_three_services(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        with _patch_versions(), _patch_github("2.5.0"):
            resp = await client.get("/api/v1/system/versions", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["services"]) == 3
        names = [s["name"] for s in data["services"]]
        assert names == ["backend", "frontend", "controller"]

    async def test_installed_version_from_docker(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        with _patch_versions(), _patch_github():
            resp = await client.get("/api/v1/system/versions", headers=auth_headers)

        backend = resp.json()["services"][0]
        assert backend["installed"] == "2.4.2"
        assert backend["image"] == "stefanposs/webmacs-backend:2.4.2"

    async def test_available_from_github(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        with _patch_versions(), _patch_github("3.0.0"):
            resp = await client.get("/api/v1/system/versions", headers=auth_headers)

        services = resp.json()["services"]
        for svc in services:
            assert svc["available"] == "3.0.0"

    async def test_status_reflects_running(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        with _patch_versions(), _patch_github():
            resp = await client.get("/api/v1/system/versions", headers=auth_headers)

        for svc in resp.json()["services"]:
            assert svc["status"] == "running"

    async def test_status_updating_when_progress_active(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        tmp_path: Path,
    ) -> None:
        """When the status file indicates pulling, service status is 'updating'."""
        status_file = tmp_path / "update-status.json"
        status_file.write_text(
            json.dumps(
                {
                    "overall_status": "pulling",
                    "services": {"backend": "updating"},
                    "current_step": "Pulling…",
                }
            )
        )

        with (
            _patch_versions(),
            _patch_github(),
            patch("webmacs_backend.api.v1.system.versions._STATUS_FILE", status_file),
        ):
            resp = await client.get("/api/v1/system/versions", headers=auth_headers)

        for svc in resp.json()["services"]:
            assert svc["status"] == "updating"

    async def test_unauthenticated_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/system/versions")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# API tests — GET /system/update-progress
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetUpdateProgress:
    """Integration tests for ``GET /api/v1/system/update-progress``."""

    async def test_idle_when_no_file(
        self, client: AsyncClient, auth_headers: dict[str, str], tmp_path: Path
    ) -> None:
        with patch("webmacs_backend.api.v1.system.versions._STATUS_FILE", tmp_path / "nope.json"):
            resp = await client.get("/api/v1/system/update-progress", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "idle"

    async def test_returns_pulling_status(
        self, client: AsyncClient, auth_headers: dict[str, str], tmp_path: Path
    ) -> None:
        sf = tmp_path / "status.json"
        sf.write_text(
            json.dumps(
                {
                    "overall_status": "pulling",
                    "services": {"backend": "updating"},
                    "current_step": "Pulling images…",
                }
            )
        )

        with patch("webmacs_backend.api.v1.system.versions._STATUS_FILE", sf):
            resp = await client.get("/api/v1/system/update-progress", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "pulling"

    async def test_unauthenticated_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/system/update-progress")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# API tests — POST /system/trigger
# ═══════════════════════════════════════════════════════════════════════════════


class TestTriggerUpdate:
    """Integration tests for ``POST /api/v1/system/trigger``."""

    async def test_success(
        self, client: AsyncClient, auth_headers: dict[str, str], tmp_path: Path
    ) -> None:
        trigger_f = tmp_path / "trigger.json"

        with (
            patch("webmacs_backend.api.v1.system.versions._TRIGGER_FILE", trigger_f),
            patch("webmacs_backend.api.v1.system.versions._UPDATE_DIR", tmp_path),
        ):
            resp = await client.post(
                "/api/v1/system/trigger",
                json={"version": "2.5.0", "backend_image": "stefanposs/webmacs-backend:2.5.0"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"
        assert trigger_f.exists()

    async def test_409_when_trigger_pending(
        self, client: AsyncClient, auth_headers: dict[str, str], tmp_path: Path
    ) -> None:
        trigger_f = tmp_path / "trigger.json"
        trigger_f.write_text("{}")

        with (
            patch("webmacs_backend.api.v1.system.versions._TRIGGER_FILE", trigger_f),
            patch("webmacs_backend.api.v1.system.versions._UPDATE_DIR", tmp_path),
        ):
            resp = await client.post(
                "/api/v1/system/trigger",
                json={"version": "2.5.0"},
                headers=auth_headers,
            )

        assert resp.status_code == 409
        assert "pending" in resp.json()["detail"].lower()

    async def test_400_empty_request(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/system/trigger",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_unauthenticated_401(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/system/trigger", json={"version": "2.5.0"})
        assert resp.status_code == 401

    async def test_image_validation_rejects_shell_injection(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        resp = await client.post(
            "/api/v1/system/trigger",
            json={"backend_image": "$(rm -rf /)"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests — version_detector
# ═══════════════════════════════════════════════════════════════════════════════


class TestVersionDetector:
    """Pure-function / mocked tests for ``version_detector``."""

    def test_get_all_versions_no_docker(self) -> None:
        """When Docker socket is absent, backend falls back to __version__."""
        with patch("webmacs_backend.services.version_detector.os.path.exists", return_value=False):
            from webmacs_backend.services.version_detector import get_all_service_versions

            result = get_all_service_versions()

        assert "backend" in result
        assert "frontend" in result
        assert "controller" in result
        assert result["backend"].installed is not None  # from __version__
        assert result["frontend"].installed is None
        assert result["controller"].installed is None

    def test_extract_tag_from_image(self) -> None:
        from webmacs_backend.services.version_detector import _extract_tag

        assert _extract_tag("stefanposs/webmacs-backend:2.4.2") == "2.4.2"
        assert _extract_tag("image:latest") is None
        assert _extract_tag("image") is None
        assert _extract_tag("image@sha256:abc") is None
        assert _extract_tag(None) is None


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests — updater IPC (scan_for_trigger, process_trigger)
# ═══════════════════════════════════════════════════════════════════════════════


class TestUpdaterIPC:
    """Test the trigger-file IPC in ``services/updater``."""

    def test_scan_for_trigger_no_file(self, tmp_path: Path) -> None:
        with patch("webmacs_backend.services.updater.TRIGGER_FILE", tmp_path / "trigger.json"):
            from webmacs_backend.services.updater import scan_for_trigger

            assert scan_for_trigger() is None

    def test_scan_for_trigger_valid(self, tmp_path: Path) -> None:
        trigger_f = tmp_path / "trigger.json"
        payload = {"version": "2.5.0", "images": ["img:2.5.0"], "requested_at": "2026-03-01T12:00:00"}
        trigger_f.write_text(json.dumps(payload))

        with patch("webmacs_backend.services.updater.TRIGGER_FILE", trigger_f):
            from webmacs_backend.services.updater import scan_for_trigger

            result = scan_for_trigger()
            assert result is not None
            assert result["version"] == "2.5.0"

    def test_scan_for_trigger_invalid_json(self, tmp_path: Path) -> None:
        trigger_f = tmp_path / "trigger.json"
        trigger_f.write_text("not valid json{{{")

        with patch("webmacs_backend.services.updater.TRIGGER_FILE", trigger_f):
            from webmacs_backend.services.updater import scan_for_trigger

            result = scan_for_trigger()
            assert result is None
            # Invalid file gets cleaned up
            assert not trigger_f.exists()

    def test_process_trigger_success(self, tmp_path: Path) -> None:
        trigger_f = tmp_path / "trigger.json"
        trigger_f.write_text(json.dumps({"version": "2.5.0", "images": ["img:2.5.0"]}))
        status_f = tmp_path / "update-status.json"

        with (
            patch("webmacs_backend.services.updater.TRIGGER_FILE", trigger_f),
            patch("webmacs_backend.services.updater.STATUS_FILE", status_f),
            patch("webmacs_backend.services.updater.pull_images", return_value=True) as mock_pull,
            patch("webmacs_backend.services.updater.restart_services", return_value=True) as mock_restart,
        ):
            from webmacs_backend.services.updater import process_trigger

            process_trigger({"version": "2.5.0", "images": ["img:2.5.0"]})

            mock_pull.assert_called_once_with(["img:2.5.0"])
            mock_restart.assert_called_once_with("2.5.0")

            # trigger file should be consumed (deleted)
            assert not trigger_f.exists()

            # status file should show completed
            final = json.loads(status_f.read_text())
            assert final["overall_status"] == "completed"

    def test_process_trigger_pull_failure(self, tmp_path: Path) -> None:
        trigger_f = tmp_path / "trigger.json"
        trigger_f.write_text("{}")
        status_f = tmp_path / "update-status.json"

        with (
            patch("webmacs_backend.services.updater.TRIGGER_FILE", trigger_f),
            patch("webmacs_backend.services.updater.STATUS_FILE", status_f),
            patch("webmacs_backend.services.updater.pull_images", return_value=False),
            patch("webmacs_backend.services.updater.restart_services") as mock_restart,
        ):
            from webmacs_backend.services.updater import process_trigger

            process_trigger({"version": "2.5.0", "images": ["img:2.5.0"]})

            mock_restart.assert_not_called()
            final = json.loads(status_f.read_text())
            assert final["overall_status"] == "failed"

    def test_process_trigger_restart_failure(self, tmp_path: Path) -> None:
        trigger_f = tmp_path / "trigger.json"
        trigger_f.write_text("{}")
        status_f = tmp_path / "update-status.json"

        with (
            patch("webmacs_backend.services.updater.TRIGGER_FILE", trigger_f),
            patch("webmacs_backend.services.updater.STATUS_FILE", status_f),
            patch("webmacs_backend.services.updater.pull_images", return_value=True),
            patch("webmacs_backend.services.updater.restart_services", return_value=False),
        ):
            from webmacs_backend.services.updater import process_trigger

            process_trigger({"version": "2.5.0", "images": ["img:2.5.0"]})

            final = json.loads(status_f.read_text())
            assert final["overall_status"] == "failed"
            assert "restart" in final["error"].lower()

    def test_write_update_status(self, tmp_path: Path) -> None:
        status_f = tmp_path / "update-status.json"

        with patch("webmacs_backend.services.updater.STATUS_FILE", status_f):
            from webmacs_backend.services.updater import _write_update_status

            _write_update_status("pulling", {"backend": "updating"}, "Pulling images…")

            data = json.loads(status_f.read_text())
            assert data["overall_status"] == "pulling"
            assert data["services"]["backend"] == "updating"
            assert data["current_step"] == "Pulling images…"
