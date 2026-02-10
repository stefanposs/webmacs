# Testing

WebMACS has three test suites: **backend** (Python), **controller** (Python), and **frontend** (TypeScript).

---

## Test Structure

```
├── backend/tests/
│   ├── conftest.py           # Fixtures (async session, test client, auth)
│   ├── test_auth.py          # Login, JWT validation
│   ├── test_users.py         # User CRUD
│   ├── test_experiments.py   # Experiment lifecycle
│   ├── test_events.py        # Events CRUD
│   ├── test_datapoints.py    # Datapoints + bulk create
│   └── test_logging.py       # Logs CRUD
├── controller/tests/
│   ├── conftest.py           # Fixtures (mock API client)
│   ├── test_api_client.py    # HTTP client + retry logic
│   ├── test_sensor_manager.py # Sensor reading tests
│   └── test_telemetry.py     # Transport protocol tests
└── frontend/
    └── (vitest tests via npm run test)
```

---

## Running Tests

### All Tests

```bash
just test
```

### By Component

```bash
just test-backend       # Backend only
just test-controller    # Controller only
just test-frontend      # Frontend only
```

### With Coverage

```bash
cd backend && uv run pytest tests/ -v --cov --cov-report=html
```

Open `htmlcov/index.html` to view the coverage report.

---

## Backend Test Setup

Tests use an **in-memory SQLite** database by default (overridable via `DATABASE_URL` env var).

### Key Fixtures (`conftest.py`)

| Fixture | Scope | Description |
|---|---|---|
| `engine` | session | Async SQLAlchemy engine |
| `session` | function | Async session (auto-rolled-back) |
| `client` | function | `httpx.AsyncClient` against the test app |
| `auth_headers` | function | `{"Authorization": "Bearer ..."}` for authenticated requests |
| `admin_user` | function | Pre-seeded admin user |

### Example Test

```python
@pytest.mark.asyncio
async def test_create_experiment(client, auth_headers):
    response = await client.post(
        "/api/v1/experiments",
        json={"name": "Test Run"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Run"
    assert data["started_on"] is not None
```

---

## Controller Test Setup

Controller tests mock the HTTP client to avoid needing a running backend:

```python
@pytest.fixture
def mock_api_client(mocker):
    client = mocker.MagicMock(spec=APIClient)
    client.post = mocker.AsyncMock(return_value={"status": "ok"})
    return client
```

---

## Frontend Tests

```bash
cd frontend
npm run test -- --run     # Single run
npm run test -- --watch   # Watch mode
```

Uses **Vitest** with Vue Test Utils.

---

## CI Integration

GitHub Actions runs the full test matrix:

| Job | Python | OS | Services |
|---|---|---|---|
| `python` | 3.14 | ubuntu-latest | PostgreSQL 17 |
| `frontend` | — | ubuntu-latest | — |

Coverage reports are uploaded to [Codecov](https://codecov.io/).

---

## Test Markers

```python
@pytest.mark.unit          # Fast, no external deps
@pytest.mark.integration   # Needs database
@pytest.mark.e2e           # Full stack
```

Run specific markers:

```bash
uv run pytest -m unit
uv run pytest -m integration
```

---

## Next Steps

- [Contributing](contributing.md) — development workflow
- [Code Style](code-style.md) — formatting and linting rules
