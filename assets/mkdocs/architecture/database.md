# Database Layer

WebMACS uses **PostgreSQL 17** with **SQLAlchemy 2.0** async ORM and the **asyncpg** driver for high-throughput time-series storage.

---

## Connection Setup

```python
# database.py
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

Sessions are injected via `Depends(get_db)` in every route.

---

## Tables (15)

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | Admin and operator accounts | `username`, `hashed_password`, `admin` |
| `events` | Sensor/channel definitions | `name`, `unit`, `min_value`, `max_value`, `event_type` |
| `experiments` | Time-bounded data campaigns | `name`, `started_on`, `stopped_on` |
| `datapoints` | Time-series sensor readings | `value`, `event_public_id`, `experiment_public_id`, `timestamp` |
| `log_entries` | System and user logs | `content`, `logging_type`, `status_type` |
| `blacklist_tokens` | Revoked JWTs (logout) | `token`, `blacklisted_on` |
| `rules` | Automation threshold triggers | `event_public_id`, `operator`, `threshold`, `action_type` |
| `webhooks` | HTTP callback subscriptions | `url`, `secret`, `events` (JSON list), `enabled` |
| `webhook_deliveries` | Delivery audit trail | `webhook_id`, `status`, `response_code`, `payload` |
| `firmware_updates` | OTA firmware records | `version`, `release_notes`, `file_path`, `status` |
| `dashboards` | Custom dashboard layouts | `name`, `is_global`, `user_public_id` |
| `dashboard_widgets` | Widget positioning & config | `dashboard_id`, `widget_type`, `config_json`, `x`, `y`, `w`, `h` |
| `plugin_packages` | Uploaded plugin `.whl` files | `package_name`, `version`, `source`, `file_hash_sha256` |
| `plugin_instances` | Running plugin configurations | `plugin_id`, `instance_name`, `demo_mode`, `config_json` |
| `channel_mappings` | Plugin channel → event links | `instance_id`, `channel_id`, `event_public_id` |

All tables use `public_id` (UUID) as the external-facing identifier and an integer `id` as the internal primary key.

---

## Model Conventions

All models inherit from a shared `DeclarativeBase`. Each model defines its own columns — there is no shared mixin. Common patterns across most models:

- `id` — auto-incrementing integer primary key
- `public_id` — UUID string exposed to the API (external identifier)
- `created_on` — server-side timestamp via `server_default=func.now()`

```python
class Base(DeclarativeBase):
    pass

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(100), unique=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    # ...
```

### Key Indexes

```python
# Composite index for time-series queries (datapoints filtered by event + time)
__table_args__ = (
    Index("ix_datapoints_event_ts", "event_public_id", "timestamp"),
)
```

This composite index dramatically accelerates the most common query pattern: "give me datapoints for event X between time A and time B."

---

## Generic Repository

Instead of per-model repositories, WebMACS uses a **single `repository.py`** with generic async helpers:

### `paginate[M, S]`

```python
async def paginate(
    db: AsyncSession,
    model: type[M],
    schema: type[S],
    page: int,
    page_size: int,
    base_query: Select | None = None,
) -> PaginatedResponse[S]:
```

Returns a `PaginatedResponse` with `items`, `total`, `page`, `page_size`, and `pages`. Used by every list endpoint.

### `get_or_404`

```python
async def get_or_404(
    db: AsyncSession,
    model: type[M],
    public_id: str,
    entity_name: str = "Entity",
) -> M:
```

Loads by `public_id` or raises `HTTPException(404)`.

### `delete_by_public_id`

```python
async def delete_by_public_id(
    db: AsyncSession,
    model: type[M],
    public_id: str,
    entity_name: str = "Entity",
) -> StatusResponse:
```

Deletes by `public_id` or raises `HTTPException(404)`. Returns a `StatusResponse` confirmation.

### `ConflictError`

Raised when a uniqueness constraint is violated (e.g., duplicate username).

---

## Migrations

WebMACS uses **Alembic** for schema migrations:

```bash
# Generate a migration after changing models
cd backend
alembic revision --autogenerate -m "add dashboard tables"

# Apply migrations
alembic upgrade head
```

The migration environment is configured in [alembic/env.py](https://github.com/stefanposs/webmacs) for async support.

---

## Relationships

```
users ─────┬── log_entries (user_public_id)
           ├── experiments (implicit, via auth)
           ├── dashboards (user_public_id)
           ├── rules (user_public_id)
           ├── firmware_updates (user_public_id, SET NULL)
           └── plugin_packages (user_public_id, SET NULL)

events ────┬── datapoints (event_public_id)
           ├── rules (event_public_id, CASCADE)
           └── dashboard_widgets (event_public_id, SET NULL)

experiments ── datapoints (experiment_public_id, SET NULL)

webhooks ── webhook_deliveries (webhook_id, CASCADE)

dashboards ── dashboard_widgets (dashboard_id, CASCADE)

plugin_instances ── channel_mappings (instance_id, CASCADE)
```

All foreign keys have explicit `ondelete` directives (`CASCADE` or `SET NULL`) to prevent orphaned records.

---

## Next Steps

- [Backend Architecture](backend.md) — where the repository is consumed
- [Schema Reference](../api/schemas.md) — Pydantic models for all tables
- [REST API](../api/rest.md) — endpoint documentation