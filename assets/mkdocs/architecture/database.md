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

## Tables (12)

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | Admin and operator accounts | `username`, `hashed_password`, `admin` |
| `events` | Sensor/channel definitions | `name`, `unit`, `min_value`, `max_value`, `event_type` |
| `experiments` | Time-bounded data campaigns | `name`, `started_on`, `stopped_on` |
| `datapoints` | Time-series sensor readings | `value`, `event_public_id`, `experiment_public_id`, `created_on` |
| `log_entries` | System and user logs | `content`, `logging_type`, `status_type`, `read` |
| `blacklist_tokens` | Revoked JWTs (logout) | `token`, `blacklisted_on` |
| `rules` | Automation threshold triggers | `event_public_id`, `operator`, `threshold`, `action_type`, `action_target` |
| `webhooks` | HTTP callback subscriptions | `url`, `secret`, `events` (JSON list), `active` |
| `webhook_deliveries` | Delivery audit trail | `webhook_public_id`, `status`, `response_code`, `payload` |
| `firmware_updates` | OTA firmware records | `version`, `filename`, `file_path`, `status` |
| `dashboards` | Custom dashboard layouts | `name`, `description` |
| `dashboard_widgets` | Widget positioning & config | `dashboard_public_id`, `widget_type`, `config` (JSON), `x`, `y`, `w`, `h` |

All tables use `public_id` (UUID) as the external-facing identifier and an integer `id` as the internal primary key.

---

## Model Conventions

Every model inherits from a common `Base` with shared columns:

```python
class Base(DeclarativeBase):
    pass

class CommonMixin:
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(unique=True, default=lambda: str(uuid4()))
    created_on: Mapped[datetime] = mapped_column(default=func.now())
    updated_on: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
```

### Key Indexes

```python
# Composite index for time-series queries (datapoints filtered by event + time)
__table_args__ = (
    Index("ix_datapoint_event_created", "event_public_id", "created_on"),
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
users ──────────────────────────────────────────────
events ──┬── datapoints (event_public_id)
         └── rules (event_public_id)
experiments ── datapoints (experiment_public_id)
webhooks ── webhook_deliveries (webhook_public_id)
dashboards ── dashboard_widgets (dashboard_public_id)
```

---

## Next Steps

- [Backend Architecture](backend.md) — where the repository is consumed
- [Schema Reference](../api/schemas.md) — Pydantic models for all tables
- [REST API](../api/rest.md) — endpoint documentation