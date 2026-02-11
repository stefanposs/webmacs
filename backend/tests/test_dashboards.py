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

    async def test_update_widget(self, client: AsyncClient, auth_headers: dict, sample_event) -> None:
        dash_id = await self._create_dashboard(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "line_chart",
                "title": "Original Title",
                "event_public_id": sample_event.public_id,
                "x": 0,
                "y": 0,
                "w": 4,
                "h": 3,
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        widget_id = create_resp.json()["public_id"]

        # Partial update — title + size
        update_resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"title": "Updated Title", "w": 6, "h": 5},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "success"

        # Verify the change persisted
        dash_resp = await client.get(f"/api/v1/dashboards/{dash_id}", headers=auth_headers)
        widget = dash_resp.json()["widgets"][0]
        assert widget["title"] == "Updated Title"
        assert widget["w"] == 6
        assert widget["h"] == 5
        # Unchanged fields should be preserved
        assert widget["event_public_id"] == sample_event.public_id

    async def test_update_widget_invalid_event(
        self, client: AsyncClient, auth_headers: dict, sample_event
    ) -> None:
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

        # Attempt to update with a nonexistent event → 404
        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"event_public_id": "does-not-exist"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_widget_clear_event(
        self, client: AsyncClient, auth_headers: dict, sample_event
    ) -> None:
        dash_id = await self._create_dashboard(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "stat_card",
                "title": "Card",
                "event_public_id": sample_event.public_id,
                "x": 0,
                "y": 0,
                "w": 3,
                "h": 2,
            },
            headers=auth_headers,
        )
        widget_id = create_resp.json()["public_id"]

        # Setting event_public_id to null should be allowed (clears the event)
        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"event_public_id": None},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        dash_resp = await client.get(f"/api/v1/dashboards/{dash_id}", headers=auth_headers)
        assert dash_resp.json()["widgets"][0]["event_public_id"] is None

    async def test_update_widget_empty_title_rejected(
        self, client: AsyncClient, auth_headers: dict, sample_event
    ) -> None:
        dash_id = await self._create_dashboard(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "gauge",
                "title": "Valid",
                "event_public_id": sample_event.public_id,
                "x": 0,
                "y": 0,
                "w": 4,
                "h": 3,
            },
            headers=auth_headers,
        )
        widget_id = create_resp.json()["public_id"]

        # Empty title should be rejected (422)
        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"title": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    # ── P0: Authorization & cross-dashboard boundary ──────────────────────

    async def test_update_widget_wrong_dashboard(
        self, client: AsyncClient, auth_headers: dict, sample_event
    ) -> None:
        """Widget exists but belongs to dashboard A — updating via dashboard B → 404."""
        dash_a = await self._create_dashboard(client, auth_headers)
        dash_b = await self._create_dashboard(client, auth_headers)

        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_a}/widgets",
            json={
                "widget_type": "line_chart",
                "title": "On Dash A",
                "event_public_id": sample_event.public_id,
                "x": 0, "y": 0, "w": 4, "h": 3,
            },
            headers=auth_headers,
        )
        widget_id = create_resp.json()["public_id"]

        # Attempt update through the wrong dashboard
        resp = await client.put(
            f"/api/v1/dashboards/{dash_b}/widgets/{widget_id}",
            json={"title": "Hacked"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert "Widget not on this dashboard" in resp.json()["detail"]

    async def test_update_widget_forbidden(
        self, client: AsyncClient, auth_headers: dict, sample_event, db_session
    ) -> None:
        """Another user cannot update widgets on a dashboard they don't own → 403."""
        from webmacs_backend.models import User
        from webmacs_backend.security import create_access_token, hash_password

        # Create dashboard + widget as admin
        dash_id = await self._create_dashboard(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "gauge",
                "title": "Admin Widget",
                "event_public_id": sample_event.public_id,
                "x": 0, "y": 0, "w": 4, "h": 3,
            },
            headers=auth_headers,
        )
        widget_id = create_resp.json()["public_id"]

        # Create a second user
        other_user = User(
            public_id="other-user-id",
            email="other@test.io",
            username="other",
            password_hash=hash_password("otherpass123"),
            admin=False,
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)
        other_token = create_access_token(other_user.id)
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"title": "Hijacked"},
            headers=other_headers,
        )
        assert resp.status_code == 403

    # ── P1: Nonexistent resources & schema boundaries ─────────────────────

    async def test_update_widget_nonexistent_dashboard(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Updating a widget on a dashboard that doesn't exist → 404."""
        resp = await client.put(
            "/api/v1/dashboards/no-such-dashboard/widgets/no-such-widget",
            json={"title": "Anything"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_widget_nonexistent_widget(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Dashboard exists but widget doesn't → 404."""
        dash_id = await self._create_dashboard(client, auth_headers)
        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/no-such-widget",
            json={"title": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_widget_w_h_boundary(
        self, client: AsyncClient, auth_headers: dict, sample_event
    ) -> None:
        """w and h must satisfy ge=1, le=12 — out-of-range values → 422."""
        dash_id = await self._create_dashboard(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "stat_card",
                "title": "Card",
                "event_public_id": sample_event.public_id,
                "x": 0, "y": 0, "w": 4, "h": 3,
            },
            headers=auth_headers,
        )
        widget_id = create_resp.json()["public_id"]

        # w = 0 (below ge=1)
        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"w": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

        # w = 13 (above le=12)
        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"w": 13},
            headers=auth_headers,
        )
        assert resp.status_code == 422

        # h = 0 (below ge=1)
        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"h": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    # ── P2: Regression guards ─────────────────────────────────────────────

    async def test_update_widget_position_only(
        self, client: AsyncClient, auth_headers: dict, sample_event
    ) -> None:
        """Updating only x/y leaves title, w, h, event unchanged."""
        dash_id = await self._create_dashboard(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "line_chart",
                "title": "Stable Title",
                "event_public_id": sample_event.public_id,
                "x": 0, "y": 0, "w": 6, "h": 4,
            },
            headers=auth_headers,
        )
        widget_id = create_resp.json()["public_id"]

        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"x": 3, "y": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        dash_resp = await client.get(f"/api/v1/dashboards/{dash_id}", headers=auth_headers)
        widget = dash_resp.json()["widgets"][0]
        assert widget["x"] == 3
        assert widget["y"] == 5
        # Unchanged fields preserved
        assert widget["title"] == "Stable Title"
        assert widget["w"] == 6
        assert widget["h"] == 4
        assert widget["event_public_id"] == sample_event.public_id

    async def test_update_widget_config_json(
        self, client: AsyncClient, auth_headers: dict, sample_event
    ) -> None:
        """Updating config_json persists the JSON string."""
        dash_id = await self._create_dashboard(client, auth_headers)
        create_resp = await client.post(
            f"/api/v1/dashboards/{dash_id}/widgets",
            json={
                "widget_type": "gauge",
                "title": "Configurable",
                "event_public_id": sample_event.public_id,
                "x": 0, "y": 0, "w": 4, "h": 3,
            },
            headers=auth_headers,
        )
        widget_id = create_resp.json()["public_id"]

        config = '{"color": "red", "thresholds": [50, 80]}'
        resp = await client.put(
            f"/api/v1/dashboards/{dash_id}/widgets/{widget_id}",
            json={"config_json": config},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        dash_resp = await client.get(f"/api/v1/dashboards/{dash_id}", headers=auth_headers)
        assert dash_resp.json()["widgets"][0]["config_json"] == config
