"""Tests for the controller's APIClient — the critical bridge to the backend.

Covers:
- Happy-path login, GET, POST
- Retry on transient 500 errors  (resilience)
- Re-authentication on 401       (token expiry recovery)
- Timeout handling

Uses `respx` to mock httpx at the transport level — no real HTTP calls.
"""

import httpx
import pytest
import respx
from httpx import Response

from webmacs_controller.services.api_client import APIClient, APIClientError

BASE = "http://test:8000/api/v1"


# ---------------------------------------------------------------------------
# Happy-path basics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_login_stores_token() -> None:
    """Successful login stores the JWT for subsequent requests."""
    respx.post(f"{BASE}/auth/login").mock(
        return_value=Response(200, json={"access_token": "jwt-abc"})
    )
    async with APIClient(base_url=BASE) as client:
        token = await client.login("admin@test.io", "pass")
        assert token == "jwt-abc"
        assert client._token == "jwt-abc"
        assert client._credentials == ("admin@test.io", "pass")


@pytest.mark.asyncio
@respx.mock
async def test_get_sends_auth_header() -> None:
    """GET requests include the Bearer token."""
    route = respx.get(f"{BASE}/events").mock(
        return_value=Response(200, json={"data": []})
    )
    async with APIClient(base_url=BASE) as client:
        client._token = "my-token"
        await client.get("/events")
    assert route.called
    sent_auth = route.calls[0].request.headers.get("authorization")
    assert sent_auth == "Bearer my-token"


@pytest.mark.asyncio
@respx.mock
async def test_post_sends_json_body() -> None:
    """POST forwards the JSON payload correctly."""
    route = respx.post(f"{BASE}/datapoints/batch").mock(
        return_value=Response(201, json={"status": "success"})
    )
    payload = {"datapoints": [{"value": 1.0, "event_public_id": "e1"}]}
    async with APIClient(base_url=BASE) as client:
        client._token = "tok"
        result = await client.post("/datapoints/batch", json=payload)
    assert result["status"] == "success"
    import json
    assert json.loads(route.calls[0].request.content) == payload


@pytest.mark.asyncio
@respx.mock
async def test_login_failure_raises_http_error() -> None:
    """Invalid credentials → httpx.HTTPStatusError."""
    respx.post(f"{BASE}/auth/login").mock(
        return_value=Response(401, json={"detail": "Invalid email or password."})
    )
    async with APIClient(base_url=BASE) as client:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client.login("bad@test.io", "wrong")
        assert exc_info.value.response.status_code == 401


# ---------------------------------------------------------------------------
# Retry on transient 500 errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_retries_on_500() -> None:
    """GET should retry up to 3 times on 5xx, then succeed."""
    route = respx.get(f"{BASE}/events").mock(
        side_effect=[
            Response(500, json={"detail": "Internal Server Error"}),
            Response(500, json={"detail": "Internal Server Error"}),
            Response(200, json={"data": [{"id": 1}]}),
        ]
    )
    async with APIClient(base_url=BASE, max_retries=3, backoff_base=0) as client:
        client._token = "tok"
        result = await client.get("/events")
    assert result == {"data": [{"id": 1}]}
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_get_raises_after_max_retries() -> None:
    """After exhausting retries, APIClientError is raised."""
    respx.get(f"{BASE}/events").mock(
        return_value=Response(502, json={"detail": "Bad Gateway"})
    )
    async with APIClient(base_url=BASE, max_retries=2, backoff_base=0) as client:
        client._token = "tok"
        with pytest.raises(APIClientError, match="2 attempts"):
            await client.get("/events")


# ---------------------------------------------------------------------------
# Re-authentication on 401 (token expired)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_reauths_on_401_then_retries() -> None:
    """When a request returns 401, the client should re-login and retry."""
    events_route = respx.get(f"{BASE}/events")
    events_route.side_effect = [
        Response(401, json={"detail": "Invalid or expired token."}),
        Response(200, json={"data": [{"id": 1}]}),
    ]

    # Re-auth call
    respx.post(f"{BASE}/auth/login").mock(
        return_value=Response(200, json={"access_token": "new-jwt"})
    )

    async with APIClient(base_url=BASE) as client:
        client._token = "expired-token"
        client._credentials = ("admin@test.io", "pass")
        result = await client.get("/events")

    assert result == {"data": [{"id": 1}]}
    assert client._token == "new-jwt"
    assert events_route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_reauth_failure_propagates() -> None:
    """If re-auth itself fails, APIClientError is raised."""
    respx.get(f"{BASE}/events").mock(
        return_value=Response(401, json={"detail": "Invalid or expired token."})
    )
    respx.post(f"{BASE}/auth/login").mock(
        return_value=Response(401, json={"detail": "Invalid email or password."})
    )

    async with APIClient(base_url=BASE, max_retries=2, backoff_base=0) as client:
        client._token = "expired"
        client._credentials = ("admin@test.io", "wrong")
        with pytest.raises((httpx.HTTPStatusError, APIClientError)):
            await client.get("/events")


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_timeout_raises_after_retries() -> None:
    """Network timeouts are retried, then raise APIClientError."""
    respx.get(f"{BASE}/events").mock(side_effect=httpx.ReadTimeout("timed out"))
    async with APIClient(base_url=BASE, timeout=0.1, max_retries=2, backoff_base=0) as client:
        client._token = "tok"
        with pytest.raises(APIClientError, match="2 attempts"):
            await client.get("/events")


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_closes_client() -> None:
    """Exiting the context manager should close the underlying httpx client."""
    async with APIClient(base_url=BASE) as client:
        assert not client._client.is_closed
    assert client._client.is_closed
