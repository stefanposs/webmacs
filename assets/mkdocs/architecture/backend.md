# Backend Architecture

The backend is a **FastAPI** application with async SQLAlchemy, structured as a Python package: `webmacs_backend`.

---

## Package Structure

```
backend/src/webmacs_backend/
├── __init__.py
├── main.py              # Application factory + lifespan
├── config.py            # pydantic-settings Settings
├── database.py          # Engine, session, init_db
├── models.py            # SQLAlchemy ORM models
├── schemas.py           # Pydantic v2 request/response schemas
├── enums.py             # StrEnum definitions (EventType, StatusType, LoggingType)
├── security.py          # JWT + bcrypt helpers
├── dependencies.py      # FastAPI Depends() factories
├── repository.py        # ORM-level query helpers
├── api/
│   └── v1/
│       ├── auth.py          # POST /auth/login
│       ├── users.py         # CRUD /users
│       ├── experiments.py   # CRUD /experiments + CSV export
│       ├── events.py        # CRUD /events
│       ├── datapoints.py    # CRUD /datapoints
│       └── logging.py       # CRUD /logs
├── repositories/
│   ├── protocols.py         # DatapointRepository + ExperimentRepository
│   ├── dependencies.py      # DI wiring (STORAGE_BACKEND → impl)
│   ├── sqlalchemy_repo.py   # PostgreSQL implementation
│   └── timescale_repo.py    # TimescaleDB stub
└── ws/
    ├── connection_manager.py  # Pub/sub hub
    └── endpoints.py           # /ws/controller/telemetry, /ws/datapoints/stream
```

---

## Application Lifecycle

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await init_db()          # Create tables
    await _seed_admin()      # Seed admin if no users exist
    yield
    await engine.dispose()   # Clean shutdown
```

The `lifespan` context manager runs once at startup and shutdown. It replaces the deprecated `on_event` hooks.

---

## Configuration

All settings are loaded from environment variables via **pydantic-settings**:

```python
class Settings(BaseSettings):
    database_url: str
    secret_key: str
    storage_backend: str = "postgresql"
    ws_heartbeat_interval: int = 30
    # ...
```

---

## API Routers

All six routers are mounted under `/api/v1/`:

| Router | Prefix | Auth | Key Endpoints |
|---|---|---|---|
| `auth` | `/auth` | Public | `POST /login` |
| `users` | `/users` | Admin | CRUD |
| `experiments` | `/experiments` | JWT | CRUD, `GET /{id}/export/csv` |
| `events` | `/events` | JWT | CRUD |
| `datapoints` | `/datapoints` | JWT | CRUD, bulk create |
| `logging` | `/logs` | JWT | CRUD, mark read |

---

## Repository Protocol Layer

The backend uses **PEP 544 Protocols** to abstract the database:

```python
class DatapointRepository(Protocol):
    async def create(self, ...) -> DatapointRecord: ...
    async def get_by_experiment(self, ...) -> Sequence[DatapointRecord]: ...
```

Switch between implementations via `STORAGE_BACKEND`:

- `postgresql` → `SQLAlchemyDatapointRepo`
- `timescale` → `TimescaleDatapointRepo` (stub)

---

## Security

- **bcrypt** for password hashing (via `bcrypt` package directly)
- **JWT** tokens with `python-jose` (HS256)
- `get_current_user` dependency validates token on every protected route
- Admin-only routes check `user.admin == True`

---

## Next Steps

- [WebSocket Design](websocket.md) — real-time data streaming
- [Database Abstraction](database.md) — Protocol details
- [REST API Reference](../api/rest.md) — endpoint documentation
