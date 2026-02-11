"""HTTP API client for backend communication with retry and auto-reauthentication."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


class APIClientError(Exception):
    """Raised when all retries are exhausted."""


class APIClient:
    """Async HTTP client for WebMACS Backend API.

    Features:
    - Automatic retry with exponential back-off on transient errors (5xx, timeouts).
    - Transparent re-authentication when a 401 is received.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/api/v1",
        timeout: float = 30.0,
        max_retries: int = _MAX_RETRIES,
        backoff_base: float = _BACKOFF_BASE,
    ) -> None:
        self._token: str | None = None
        self._base_url = base_url
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._credentials: tuple[str, str] | None = None
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, follow_redirects=True)

    async def __aenter__(self) -> APIClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    @property
    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> str:
        """Authenticate with the backend and store JWT token."""
        self._credentials = (email, password)
        logger.info("authenticating_with_backend", email=email)
        response = await self._client.post("/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        self._token = response.json()["access_token"]
        logger.info("authentication_successful")
        return self._token

    async def _reauthenticate(self) -> None:
        """Re-login using stored credentials."""
        if not self._credentials:
            raise APIClientError("Cannot re-authenticate: no credentials stored.")
        email, password = self._credentials
        logger.warning("token_expired_reauthenticating", email=email)
        await self.login(email, password)

    # ------------------------------------------------------------------
    # Resilient request helpers
    # ------------------------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Execute an HTTP request with retry, back-off and auto re-auth."""
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.request(method, path, headers=self._auth_headers, **kwargs)

                if response.status_code == 401 and attempt < self._max_retries:
                    await self._reauthenticate()
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("request_timeout", path=path, attempt=attempt)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise  # client errors are not retryable (except 401 handled above)
                last_error = exc
                logger.warning("server_error", path=path, status=exc.response.status_code, attempt=attempt)
            except httpx.TransportError as exc:
                last_error = exc
                logger.warning("transport_error", path=path, error=str(exc), attempt=attempt)

            if attempt < self._max_retries:
                delay = self._backoff_base * (2 ** (attempt - 1))
                logger.info("retrying_after_backoff", delay=delay, attempt=attempt)
                await asyncio.sleep(delay)

        raise APIClientError(f"Request failed after {self._max_retries} attempts: {last_error}")

    async def get(self, path: str) -> Any:
        """Make an authenticated GET request."""
        return await self._request("GET", path)

    async def post(self, path: str, json: Any = None, data: Any = None) -> Any:
        """Make an authenticated POST request."""
        return await self._request("POST", path, json=json or data)

    async def put(self, path: str, json: Any = None) -> Any:
        """Make an authenticated PUT request."""
        return await self._request("PUT", path, json=json)

    async def delete(self, path: str) -> Any:
        """Make an authenticated DELETE request."""
        return await self._request("DELETE", path)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
