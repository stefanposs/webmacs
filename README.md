# WebMACS — Web-based Monitoring and Control System

Enterprise-grade IoT platform for monitoring and controlling fluidized bed (*Wirbelschicht*) experiments.  
Built with **FastAPI**, **Vue 3**, and **Python 3.13**.

---

## Architecture

```
├── backend/          # FastAPI REST API (Python 3.13)
├── controller/       # Async IoT Controller (Python 3.13)
├── frontend/         # Vue 3 + TypeScript SPA
├── docker/           # Dockerfiles
├── docker-compose.yml
└── pyproject.toml    # UV workspace root
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend API** | FastAPI 0.115+ | REST API + OpenAPI docs |
| **Database** | PostgreSQL 17 + SQLAlchemy 2.x async | Persistent storage with asyncpg |
| **Migrations** | Alembic | Database schema migrations |
| **Auth** | JWT (python-jose) + bcrypt | Authentication & Authorization |
| **Frontend** | Vue 3 + TypeScript + Vite | Single Page Application |
| **UI Framework** | PrimeVue 4 | Enterprise UI components |
| **Charts** | Chart.js 4 + vue-chartjs | Real-time data visualization |
| **State** | Pinia | Frontend state management |
| **IoT Controller** | Python asyncio + httpx | Hardware communication |
| **Hardware** | revpimodio2 | Revolution Pi GPIO |
| **Containerization** | Docker + Docker Compose | Deployment |
| **Package Manager** | UV (Astral) | Fast Python dependency management |
| **Linting** | Ruff + mypy | Code quality |
| **Testing** | pytest + pytest-asyncio + respx | Backend & controller tests |
| **CI/CD** | GitHub Actions | Continuous Integration |

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) (recommended)
- [UV](https://docs.astral.sh/uv/) (for local Python development)
- [Node.js 22+](https://nodejs.org/) (for local frontend development)

### Development (Docker) — Recommended

```bash
# Copy and configure environment
cp .env.example .env

# Start all 4 services
docker compose up --build -d

# Services available at:
# Frontend:   http://localhost        (port 80)
# Backend:    http://localhost:8000
# API Docs:   http://localhost:8000/docs
# PostgreSQL: localhost:5432
```

Default admin credentials: `admin@webmacs.io` / `admin123`

### Development (Local)

```bash
# Backend
cd backend
uv sync --all-extras
uv run uvicorn webmacs_backend.main:app --reload --port 8000

# Controller
cd controller
uv sync --all-extras
uv run python -m webmacs_controller

# Frontend
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# All Python tests
uv run pytest

# Backend only
uv run pytest backend/tests/ -v

# Controller only
uv run pytest controller/tests/ -v

# Frontend
cd frontend && npm run test

# With coverage
uv run pytest --cov --cov-report=html
```

### Linting & Formatting

```bash
uv run ruff check .
uv run ruff format .
uv run mypy backend/src controller/src
```

---

## Project Structure

### Backend (`backend/src/webmacs_backend/`)

```
├── main.py              # FastAPI app with lifespan (admin seeding)
├── config.py            # Pydantic Settings (env vars)
├── database.py          # Async engine + session (conditional commit)
├── enums.py             # StrEnum — single source of truth for all enums
├── models.py            # SQLAlchemy 2.0 ORM models
├── schemas.py           # Pydantic v2 request/response schemas
├── repository.py        # Generic CRUD (paginate, get_or_404, delete, update)
├── security.py          # JWT create/decode, bcrypt hash/verify
├── dependencies.py      # DI: CurrentUser, AdminUser, DbSession
├── middleware/
│   ├── rate_limit.py    # Request rate limiting
│   └── request_id.py    # X-Request-ID header injection
├── services/
│   ├── __init__.py         # build_payload, dispatch_event
│   ├── webhook_dispatcher.py  # Async webhook delivery + HMAC signing
│   ├── rule_evaluator.py      # Rule evaluation on datapoint insert
│   ├── ota_service.py         # Firmware update state machine
│   ├── updater.py             # System update application
│   └── log_service.py         # Logging service
├── ws/
│   ├── connection_manager.py  # Pub/sub hub for WS groups
│   └── endpoints.py           # /ws/controller/telemetry, /ws/datapoints/stream
└── api/v1/
    ├── auth.py          # POST /login, /logout — GET /me
    ├── users.py         # CRUD /users (admin-only create, list & delete)
    ├── events.py        # CRUD /events (sensor, actuator, range, …)
    ├── experiments.py   # CRUD /experiments + POST /stop + GET /export/csv
    ├── datapoints.py    # CRUD + POST /batch, /series + GET /latest
    ├── logging.py       # CRUD /logging (no delete)
    ├── webhooks.py      # CRUD /webhooks + GET /deliveries
    ├── rules.py         # CRUD /rules (admin-only)
    ├── ota.py           # CRUD /ota + POST /apply, /rollback + GET /check
    ├── dashboards.py    # CRUD /dashboards + widget CRUD
    └── health.py        # GET /health
```

**Key patterns:**

- **`enums.py`** — Single `StrEnum` source eliminates triple-duplication across models/schemas/frontend.
- **`repository.py`** — Generic CRUD functions using PEP 695 type parameters (`[M: Base, S: BaseModel]`),
  removing ~200 lines of repeated boilerplate across routers.
- **`database.py`** — Conditional commit: only commits when `session.new`, `dirty`, or `deleted` exist.
- **`security.py`** — `create_access_token()`, `decode_access_token()`, `hash_password()`, `verify_password()`,
  `TokenPayload` frozen dataclass, `InvalidTokenError`.

### Controller (`controller/src/webmacs_controller/`)

```
├── __main__.py          # Entry point (asyncio.run)
├── app.py               # Orchestrator (TaskGroup: sensors, actuators, rules)
├── config.py            # Pydantic Settings
├── schemas.py           # Pydantic v2 models
└── services/
    ├── api_client.py    # Resilient httpx client (retry + auto re-auth)
    ├── sensor_manager.py
    ├── actuator_manager.py
    ├── rule_engine.py   # Valve interval cycling
    └── hardware.py      # RevPi ABC + SimulatedHardware + DemoSeeder
```

**Key patterns:**

- **`api_client.py`** — Central `_request()` method with exponential backoff (max 3 retries),
  auto re-authentication on 401, handles `TimeoutException`, 5xx, `TransportError`.
  Raises `APIClientError` when all retries exhausted.
- **`hardware.py`** — Protocol-based abstraction: `HardwareInterface` with `RevPiHardware`
  (production) and `SimulatedHardware` + `DemoSeeder` (development).

### Frontend (`frontend/src/`)

```
├── main.ts
├── App.vue              # Layout shell + page transitions
├── router/index.ts      # Vue Router with auth guards
├── services/api.ts      # Axios instance with error extraction
├── types/index.ts       # TypeScript interfaces + enums
├── stores/              # Pinia state management (8 stores)
│   ├── auth.ts
│   ├── events.ts
│   ├── experiments.ts
│   ├── datapoints.ts
│   ├── dashboards.ts    # Dashboard + widget CRUD
│   ├── webhooks.ts      # Webhook CRUD + deliveries
│   ├── rules.ts         # Rule CRUD store
│   └── ota.ts           # OTA update store
├── composables/         # Reusable composition functions
│   ├── useRealtimeDatapoints.ts  # WS-first with HTTP polling fallback
│   ├── useNotification.ts   # PrimeVue Toast wrapper
│   ├── usePolling.ts        # Interval polling with auto cleanup
│   └── useFormatters.ts     # Date, number, relative time formatters
├── components/
│   ├── AppSidebar.vue   # Gradient nav with sections + avatar
│   └── AppTopbar.vue    # Live clock + environment badge
├── views/
│   ├── LoginView.vue    # Gradient login with icons
│   ├── DashboardView.vue     # Default overview dashboard
│   ├── DashboardsView.vue   # Dashboard list (CRUD)
│   ├── DashboardCustomView.vue  # User-built widget dashboard
│   ├── EventsView.vue
│   ├── ExperimentsView.vue
│   ├── DatapointsView.vue
│   ├── LogsView.vue
│   ├── UsersView.vue    # User CRUD with add user dialog
│   ├── WebhooksView.vue # Webhook subscriptions + delivery log
│   ├── RulesView.vue    # Automation rules management
│   ├── OtaView.vue      # Firmware update management
│   └── NotFoundView.vue # 404 page
└── assets/
    └── main.css         # Global styles + CSS custom properties design system
```

**Key patterns:**

- **Composables** — `useNotification` (Toast), `usePolling` (auto-cleanup intervals),
  `useFormatters` (date/number/relative time) keep views thin.
- **Design tokens** — CSS custom properties (`--wm-primary`, `--wm-bg`, `--wm-surface`, etc.)
  for consistent theming.
- **Stores** — Events store re-fetches after mutations (no StatusResponse corruption).

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/login` | — | Authenticate, returns JWT |
| `POST` | `/api/v1/auth/logout` | Bearer | Blacklist current token |
| `GET` | `/api/v1/auth/me` | Bearer | Current user profile |
| **Users** | | | |
| `GET` | `/api/v1/users` | Admin | List users (paginated) |
| `POST` | `/api/v1/users` | Admin | Create user |
| `GET` | `/api/v1/users/{id}` | Bearer | Get user by public ID |
| `PUT` | `/api/v1/users/{id}` | Bearer | Update user (own profile or admin) |
| `DELETE` | `/api/v1/users/{id}` | Admin | Delete user |
| **Events** | | | |
| `GET` | `/api/v1/events` | Bearer | List events (paginated) |
| `POST` | `/api/v1/events` | Bearer | Create event |
| `GET` | `/api/v1/events/{id}` | Bearer | Get event by public ID |
| `PUT` | `/api/v1/events/{id}` | Bearer | Update event |
| `DELETE` | `/api/v1/events/{id}` | Bearer | Delete event |
| **Experiments** | | | |
| `GET` | `/api/v1/experiments` | Bearer | List experiments (paginated) |
| `POST` | `/api/v1/experiments` | Bearer | Create / start experiment |
| `PUT` | `/api/v1/experiments/{id}/stop` | Bearer | Stop experiment |
| `GET` | `/api/v1/experiments/{id}/export/csv` | Bearer | Export experiment data as CSV |
| `DELETE` | `/api/v1/experiments/{id}` | Bearer | Delete experiment |
| **Datapoints** | | | |
| `GET` | `/api/v1/datapoints` | Bearer | List datapoints (paginated) |
| `POST` | `/api/v1/datapoints` | Bearer | Create single datapoint |
| `POST` | `/api/v1/datapoints/batch` | Bearer | Bulk insert datapoints |
| `POST` | `/api/v1/datapoints/series` | Bearer | Time-series data (for charts) |
| `GET` | `/api/v1/datapoints/latest` | Bearer | Latest value per event |
| `DELETE` | `/api/v1/datapoints/{id}` | Bearer | Delete datapoint |
| **Logging** | | | |
| `GET` | `/api/v1/logging` | Bearer | List log entries (paginated) |
| `POST` | `/api/v1/logging` | Bearer | Create log entry |
| `PUT` | `/api/v1/logging/{id}` | Bearer | Update log entry (mark read) |
| **Webhooks** | | | |
| `GET` | `/api/v1/webhooks` | Admin | List webhook subscriptions |
| `POST` | `/api/v1/webhooks` | Admin | Create webhook |
| `GET` | `/api/v1/webhooks/{id}` | Admin | Get webhook by public ID |
| `PUT` | `/api/v1/webhooks/{id}` | Admin | Update webhook |
| `DELETE` | `/api/v1/webhooks/{id}` | Admin | Delete webhook |
| `GET` | `/api/v1/webhooks/{id}/deliveries` | Admin | List webhook delivery log |
| **Rules** | | | |
| `GET` | `/api/v1/rules` | Admin | List automation rules |
| `POST` | `/api/v1/rules` | Admin | Create rule |
| `GET` | `/api/v1/rules/{id}` | Admin | Get rule by public ID |
| `PUT` | `/api/v1/rules/{id}` | Admin | Update rule |
| `DELETE` | `/api/v1/rules/{id}` | Admin | Delete rule |
| **OTA Updates** | | | |
| `GET` | `/api/v1/ota` | Admin | List firmware updates |
| `POST` | `/api/v1/ota` | Admin | Create firmware update |
| `GET` | `/api/v1/ota/{id}` | Admin | Get update by public ID |
| `DELETE` | `/api/v1/ota/{id}` | Admin | Delete firmware update |
| `POST` | `/api/v1/ota/{id}/apply` | Admin | Apply firmware update |
| `POST` | `/api/v1/ota/{id}/rollback` | Admin | Rollback firmware update |
| `GET` | `/api/v1/ota/check` | Admin | Check for available updates |
| **Dashboards** | | | |
| `GET` | `/api/v1/dashboards` | Bearer | List dashboards |
| `POST` | `/api/v1/dashboards` | Bearer | Create dashboard |
| `GET` | `/api/v1/dashboards/{id}` | Bearer | Get dashboard with widgets |
| `PUT` | `/api/v1/dashboards/{id}` | Bearer | Update dashboard |
| `DELETE` | `/api/v1/dashboards/{id}` | Bearer | Delete dashboard |
| `POST` | `/api/v1/dashboards/{id}/widgets` | Bearer | Add widget |
| `PUT` | `/api/v1/dashboards/{id}/widgets/{wid}` | Bearer | Update widget |
| `DELETE` | `/api/v1/dashboards/{id}/widgets/{wid}` | Bearer | Delete widget |
| **System** | | | |
| `GET` | `/health` | — | Health check |
| `WS` | `/ws/controller/telemetry` | Bearer | Controller → backend sensor data |\n| `WS` | `/ws/datapoints/stream` | Bearer | Backend → browser live updates |

Interactive docs: **http://localhost:8000/docs** (Swagger UI) or **/redoc** (ReDoc)

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Database
DB_PASSWORD=webmacs_dev_password

# Security — generate with: openssl rand -hex 32
SECRET_KEY=change-me-in-production

# Initial admin (seeded on first start)
INITIAL_ADMIN_EMAIL=admin@webmacs.io
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=admin123

# Environment (development | production)
ENV=development

# Controller
WEBMACS_ENV=development
WEBMACS_POLL_INTERVAL=1.0
```

See [.env.example](.env.example) for the full list.

## License

MIT
