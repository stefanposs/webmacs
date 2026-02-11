"""Tests for dashboard endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDashboards:
    """Dashboard CRUD tests."""

    async def test_create_dashboard(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.post(
            "/api/v1/dashboards",
            json={"name": "My Dashboard", "is_global": False},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Dashboard"
        assert data["is_global"] is False
        assert "public_id" in data
        assert data["widgets"] == []

    async def test_list_dashboards(self, client: AsyncClient, auth_headers: dict) -> None:
        await client.post(
            "/api/v1/dashboards",
            json={"name": "Dashboard 1"},
            headers=auth_headers,
        )
        response = await client.get("/api/v1/dashboards", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    async def test_get_dashboard(self, client: AsyncClient, auth_headers: dict) -> None:
        create_resp = await client.post(
            "/api/v1/dashboards",
            json={"name": "Detail Dashboard"},
            headers=auth_headers,
        )
        pid = create_resp.json()["public_id"]
        response = await client.get(f"/api/v1/dashboards/{pid}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Detail Dashboard"

    async def test_update_dashboard(self, client: AsyncClient, auth_headers: dict) -> None:
        create_resp = await client.post(
            "/api/v1/dashboards",
            json={"name": "Before"},
            headers=auth_headers,
        )
        pid = create_resp.json()["public_id"]
        response = await client.put(
            f"/api/v1/dashboards/{pid}",
            json={"name": "After"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    async def test_delete_dashboard(self, client: AsyncClient, auth_headers: dict) -> None:
        create_resp = await client.post(
            "/api/v1/dashboards",
            json={"name": "ToDelete"},
            headers=auth_headers,
        )
        pid = create_resp.json()["public_id"]
        response = await client.delete(f"/api/v1/dashboards/{pid}", headers=auth_headers)
        assert response.status_code == 200

        get_resp = await client.get(f"/api/v1/dashboards/{pid}", headers=auth_headers)
        assert get_resp.status_code == 404

    async def test_unauthorized_access(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/dashboards")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestDashboardWidgets:
    """Widget CRUD within a dashboard."""

    async def _create_dashboard(self, client: AsyncClient, auth_headers: dict) -> str:
        resp = await client.post(
            "/api/v1/dashboards",
            json={"name": "Widget Test Board"},
            headers=auth_headers,
        )
        return resp.json()["public_id"]

    async def test_add_widget(self, client: AsyncClient, auth_headers: dict, sample_event) -> None:
        dash_id = await self._create_dashboard(client, auth_headers)
        response = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "line_chart",
                "title": "Temperature",
                "event_public_id": sample_event.public_id,
                "x": 0,
                "y": 0,
                "w": 6,
                "h": 4,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["widget_type"] == "line_chart"
        assert data["title"] == "Temperature"
        assert data["w"] == 6

    async def test_widget_appears_in_dashboard(self, client: AsyncClient, auth_headers: dict, sample_event) -> None:
        dash_id = await self._create_dashboard(client, auth_headers)
        await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "stat_card",
                "title": "Live Temp",
                "event_public_id": sample_event.public_id,
                "x": 0,
                "y": 0,
                "w": 3,
                "h": 2,
            },
            headers=auth_headers,
        )
        get_resp = await client.get(f"/api/v1/dashboards/{dash_id}", headers=auth_headers)
        assert len(get_resp.json()["widgets"]) == 1

    async def test_delete_widget(self, client: AsyncClient, auth_headers: dict, sample_event) -> None:
        dash_id = await self._create_dashboard(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "gauge",
                "title": "Gauge",
                "event_public_id": sample_event.public_id,
                "x": 0,
                "y": 0,
                "w": 4,
                "h": 3,
            },
            headers=auth_headers,
        )
        widget_id = create_resp.json()["public_id"]
        del_resp = await client.delete(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 200

        # Dashboard should now have 0 widgets
        get_resp = await client.get(f"/api/v1/dashboards/{dash_id}", headers=auth_headers)
        assert len(get_resp.json()["widgets"]) == 0

    async def test_add_widget_invalid_event(self, client: AsyncClient, auth_headers: dict) -> None:
        dash_id = await self._create_dashboard(client, auth_headers)
        response = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "line_chart",
                "title": "Bad Event",
                "event_public_id": "nonexistent",
                "x": 0,
                "y": 0,
                "w": 4,
                "h": 3,
            },
            headers=auth_headers,
        )
        assert response.status_code == 404
