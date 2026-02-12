# System Architecture

WebMACS is a **four-component system** for real-time sensor monitoring, data acquisition, and process automation.

---

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx Reverse Proxy                     │
│                  (TLS termination, WebSocket upgrade)            │
├─────────────────────┬──────────────────┬────────────────────────┤
│                     │                  │                        │
│   ┌─────────────┐   │  ┌────────────┐  │  ┌──────────────────┐ │
│   │  Frontend    │   │  │  Backend   │  │  │  PostgreSQL 17   │ │
│   │  Vue 3 SPA   │◄─┼─►│  FastAPI   │◄─┼─►│  12 tables       │ │
│   │  PrimeVue 4  │   │  │  10 routes │  │  │  async (asyncpg) │ │
│   └─────────────┘   │  └─────┬──────┘  │  └──────────────────┘ │
│                     │        │ WS      │                        │
│                     │  ┌─────▼──────┐  │                        │
│                     │  │ Controller │  │                        │
│                     │  │ RevPi HW   │  │                        │
│                     │  │ Python 3.13│  │                        │
│                     │  └────────────┘  │                        │
└─────────────────────┴──────────────────┴────────────────────────┘
                              │
                     ┌────────▼────────┐
                     │  External APIs  │
                     │  • Webhooks     │
                     │  • GitHub OTA   │
                     └─────────────────┘
```

---

## Four Components

### 1. Frontend — Vue 3 Single Page Application

| Aspect | Detail |
|---|---|
| Framework | Vue 3 (Composition API) + TypeScript 5.7 |
| UI Library | PrimeVue 4 (Aura Dark theme) |
| State | Pinia — 8 stores |
| Views | 12 views + 404 page |
| Real-time | Native WebSocket with automatic reconnection |
| Build | Vite 6, served as static files via Nginx |

See [Frontend Architecture](frontend.md).

### 2. Backend — FastAPI REST + WebSocket Server

| Aspect | Detail |
|---|---|
| Framework | FastAPI + Uvicorn (async) |
| Language | Python 3.13 |
| ORM | SQLAlchemy 2.0 (async) |
| Schemas | Pydantic v2 |
| Auth | JWT (HS256, 24h) + bcrypt |
| API Routers | 10 (auth, users, experiments, events, datapoints, logging, rules, webhooks, ota, dashboards) |
| Services | Webhook dispatcher, Rule evaluator, OTA manager |

See [Backend Architecture](backend.md).

### 3. Controller — RevPi Hardware Bridge

| Aspect | Detail |
|---|---|
| Role | Reads sensors, pushes data to backend via WebSocket |
| Language | Python 3.13 (async) |
| Protocol | WebSocket client → backend `/ws/controller/telemetry` |
| Hardware | RevPi Connect / DIO / AIO via `revpimodio2` |

See [Controller Architecture](controller.md).

### 4. PostgreSQL Database

| Aspect | Detail |
|---|---|
| Version | PostgreSQL 17 |
| Driver | `asyncpg` (fully async) |
| Tables | 12 (users, events, experiments, datapoints, log_entries, blacklist_tokens, rules, webhooks, webhook_deliveries, firmware_updates, dashboards, dashboard_widgets) |
| Key | composite index on `(event_public_id, created_on)` for time-series queries |

See [Database Layer](database.md).

---

## Data Flow

```
Sensor → Controller → WS (batch JSON) → Backend → DB (INSERT)
                                            │
                                            ├──► WS broadcast → Frontend (live chart)
                                            ├──► Rule evaluator → trigger actions
                                            └──► Webhook dispatcher → external APIs
```

### Step-by-step

1. **Controller** reads sensor values from RevPi hardware at a configured poll interval.
2. Controller sends a **batch** of datapoints over WebSocket to the backend:
   ```json
   {"datapoints": [{"value": 23.5, "event_public_id": "abc-123"}, ...]}
   ```
3. **Backend** validates, persists to PostgreSQL, and triggers three side-effects:
     - **Broadcast** to all connected dashboards via WebSocket.
     - **Rule evaluation** against threshold-based rules (e.g., "if temperature > 80°C, send alert").
     - **Webhook dispatch** if subscribed events match.
4. **Frontend** receives the broadcast and updates live charts in real-time with no page reload.

---

## Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Python 3.13 | Backend + Controller | Native async, type-hinting, modern stdlib |
| FastAPI | Web framework | Best-in-class async Python, auto-generated OpenAPI |
| SQLAlchemy 2.0 | ORM | Async-first, 2.0 style uses `select()` instead of legacy query |
| asyncpg | DB driver | Fastest PostgreSQL driver for Python async |
| Vue 3 + TS | Frontend | Composition API for clean composable logic |
| PrimeVue 4 | UI | Rich component library with accessible dark theme |
| WebSocket | Real-time | Low latency bidirectional, native browser support |
| Docker Compose | Deployment | One-command production deployment |
| Alembic | Migrations | De-facto standard for SQLAlchemy schema migrations |

---

## Deployment Model

WebMACS ships as a **Docker Compose** stack:

```yaml
services:
  backend:    # FastAPI + Uvicorn
  frontend:   # Nginx serving built Vue SPA
  db:         # PostgreSQL 17
  # controller runs on RevPi hardware (optional)
```

See [Docker Deployment](../deployment/docker.md) for full setup.