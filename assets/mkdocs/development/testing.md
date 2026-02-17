# Testing

WebMACS has three test suites: **backend** (Python), **controller** (Python), and **frontend** (TypeScript).

---

## Test Structure

```
├── backend/tests/
│   ├── conftest.py               # Fixtures (async session, test client, auth)
│   ├── test_auth.py              # Login, JWT validation, logout
│   ├── test_datapoints.py        # Datapoints batch, latest, CRUD
│   ├── test_events.py            # Events CRUD + duplicates
│   ├── test_hardening.py         # OTA download, returning(), subprocess retry
│   ├── test_polling_safeguards.py # Batch cap, rule-eval opt, broadcast throttle
│   └── test_webhook_safeguards.py # Webhook throttle, concurrency, rate limiter
├── controller/tests/
│   ├── conftest.py               # Fixtures (mock API client)
│   ├── test_api_client.py        # HTTP client + retry logic (incl. 429)
│   ├── test_hardware.py          # Hardware abstraction tests
│   └── test_polling_safeguards.py # Per-sensor throttle, dedup, chunking
└── frontend/src/
    ├── composables/__tests__/    # useFormatters, useNotification
    ├── stores/__tests__/         # auth, events, experiments, datapoints
    ├── services/__tests__/       # api, websocket
    └── types/__tests__/          # TypeScript enum validation
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
| `python` | 3.13 | ubuntu-latest | PostgreSQL 17 |
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

## Load Testing

WebMACS includes a built-in sensor scaling load test to determine system capacity.

### Running the Load Test

```bash
python3 scripts/load_test.py
```

The script authenticates against the API, creates test sensors linked to the active plugin instance, sends batch datapoints at 2 Hz (matching the real controller), and measures latency, throughput, and error rates per stage.

### Options

| Flag | Default | Description |
|---|---|---|
| `--stages` | `10,50,100,250,500` | Comma-separated sensor counts per stage |
| `--duration` | `30` | Seconds per stage |
| `--frequency` | `2.0` | Batches per second (Hz) |
| `--base-url` | `http://localhost:8000` | Backend URL |

**Examples:**

```bash
# Quick smoke test
python3 scripts/load_test.py --stages 10,50 --duration 10

# Extended stress test
python3 scripts/load_test.py --stages 10,50,100,250,500,1000 --duration 60

# Against a remote server
python3 scripts/load_test.py --base-url http://192.168.1.50:8000
```

### Metrics Collected

Per stage, the script reports:

- **Throughput** — actual datapoints/second accepted by the backend
- **Batch Latency** — P50, P95, P99 of `POST /datapoints/batch` response time
- **Dashboard Latency** — P95 of `GET /datapoints/latest` (simulates frontend polling)
- **Error Rate** — percentage of failed batch requests

### Stage Status Icons

| Icon | Meaning |
|---|---|
| ✅ | P95 < 200 ms, 0% errors |
| ⚠️ | P95 200–1000 ms or < 2% errors |
| ❌ | P95 > 1 s or > 2% errors |

### Reference Results (Single Worker, Docker on Mac)

| Sensors | dp/s | P50 | P95 | P99 | Dashboard P95 | Errors |
|---------|------|-----|-----|-----|---------------|--------|
| 10 | 20 | 12 ms | 17 ms | 20 ms | 43 ms | 0% |
| 50 | 100 | 27 ms | 228 ms | 247 ms | 44 ms | 0% |
| 100 | 199 | 43 ms | 243 ms | 248 ms | 46 ms | 0% |
| 250 | 498 | 92 ms | 353 ms | 362 ms | 52 ms | 0% |
| 500 | 990 | 186 ms | 532 ms | 552 ms | 83 ms | 0% |

!!! note "Sweet Spot"
    With the default single-worker configuration, **10 sensors** provide the best experience with P95 < 20 ms. The system remains stable and error-free up to **500+ sensors** (~1000 dp/s), though latency increases.

!!! tip "Scaling Beyond 500 Sensors"
    To improve high-sensor performance, consider:

    - Adding uvicorn workers: `--workers 4`
    - PostgreSQL connection pooling (PgBouncer)
    - Database partitioning for the datapoints table
    - Reducing the controller poll interval

---

## Next Steps

- [Contributing](contributing.md) — development workflow
- [Code Style](code-style.md) — formatting and linting rules
