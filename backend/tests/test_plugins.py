"""Tests for the plugin management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

    from webmacs_backend.models import PluginInstance


@pytest.mark.asyncio
class TestPluginInstances:
    """CRUD tests for /api/v1/plugins."""

    async def test_list_empty(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/v1/plugins", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["data"] == []

    async def test_create_instance(self, client: AsyncClient, auth_headers: dict) -> None:
        payload = {
            "plugin_id": "simulated",
            "instance_name": "Test Simulated",
            "demo_mode": True,
            "enabled": True,
        }
        resp = await client.post("/api/v1/plugins", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["status"] == "success"

    async def test_create_duplicate_name_fails(self, client: AsyncClient, auth_headers: dict) -> None:
        payload = {
            "plugin_id": "simulated",
            "instance_name": "Duplicate Name",
            "demo_mode": True,
        }
        resp1 = await client.post("/api/v1/plugins", json=payload, headers=auth_headers)
        assert resp1.status_code == 201

        resp2 = await client.post("/api/v1/plugins", json=payload, headers=auth_headers)
        assert resp2.status_code == 409

    async def test_get_instance(self, client: AsyncClient, auth_headers: dict, sample_plugin: PluginInstance) -> None:
        resp = await client.get(f"/api/v1/plugins/{sample_plugin.public_id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["instance_name"] == sample_plugin.instance_name
        assert body["plugin_id"] == sample_plugin.plugin_id

    async def test_update_instance(
        self, client: AsyncClient, auth_headers: dict, sample_plugin: PluginInstance,
    ) -> None:
        resp = await client.put(
            f"/api/v1/plugins/{sample_plugin.public_id}",
            json={"instance_name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    async def test_delete_instance(
        self, client: AsyncClient, auth_headers: dict, sample_plugin: PluginInstance,
    ) -> None:
        resp = await client.delete(f"/api/v1/plugins/{sample_plugin.public_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # Verify it's gone
        resp2 = await client.get(f"/api/v1/plugins/{sample_plugin.public_id}", headers=auth_headers)
        assert resp2.status_code == 404

    async def test_get_nonexistent_returns_404(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/v1/plugins/nonexistent-id", headers=auth_headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestAvailablePlugins:
    """Tests for /api/v1/plugins/available endpoint."""

    async def test_list_available(self, client: AsyncClient, auth_headers: dict) -> None:
        resp = await client.get("/api/v1/plugins/available", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)


@pytest.mark.asyncio
class TestChannelMappings:
    """Tests for channel mapping sub-resource endpoints."""

    async def test_list_channels(self, client: AsyncClient, auth_headers: dict, sample_plugin: PluginInstance) -> None:
        resp = await client.get(f"/api/v1/plugins/{sample_plugin.public_id}/channels", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_create_channel_mapping(
        self, client: AsyncClient, auth_headers: dict, sample_plugin: PluginInstance
    ) -> None:
        payload = {
            "channel_id": "temp_sensor",
            "channel_name": "Temperature Sensor",
            "direction": "input",
            "unit": "°C",
        }
        resp = await client.post(
            f"/api/v1/plugins/{sample_plugin.public_id}/channels",
            json=payload,
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "success"
