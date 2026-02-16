# Database Migrations

WebMACS uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations with full async support.

---

## Overview

| Component | Details |
|---|---|
| **Migration tool** | Alembic |
| **ORM** | SQLAlchemy 2 (async) |
| **Driver** | `asyncpg` (runtime) / `psycopg2` (migrations) |
| **Config** | `backend/alembic.ini` + `backend/alembic/env.py` |
| **Migrations** | `backend/alembic/versions/` |

!!! warning "Driver Swap"
    Alembic runs migrations synchronously. The `env.py` automatically swaps `+asyncpg` → `+psycopg2` in the database URL.
    Make sure **both** drivers are installed (`asyncpg` for the app, `psycopg2-binary` for migrations).

---

## Current Migrations

| Migration | Description |
|---|---|
| `001_plugins.py` | Plugin instances, channel mappings tables |
| `002_plugin_packages.py` | Plugin packages table (OTA uploads) |
| `003_fk_ondelete.py` | Add `ON DELETE CASCADE/SET NULL` to all foreign keys |

---

## Running Migrations

### Apply All Pending Migrations

```bash
cd backend
alembic upgrade head
```

### Check Current Revision

```bash
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

### Downgrade (Rollback Last Migration)

```bash
alembic downgrade -1
```

---

## Creating a New Migration

### Step 1 — Modify the Model

Edit `backend/src/webmacs_backend/models.py`:

```python
class MyNewTable(Base):
    __tablename__ = "my_new_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String(100), unique=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### Step 2 — Auto-generate the Migration

```bash
cd backend
alembic revision --autogenerate -m "add_my_new_table"
```

This creates a file in `alembic/versions/` with `upgrade()` and `downgrade()` functions.

### Step 3 — Review the Generated Migration

Always review the generated file. Alembic autogenerate is not perfect — check for:

- [ ] Correct column types and constraints
- [ ] Missing indexes
- [ ] Proper `ondelete` on foreign keys
- [ ] Data migrations (Alembic can't auto-detect these)

Example migration:

```python
"""add_my_new_table

Revision ID: abc123
Revises: 003_fk_ondelete
"""

from alembic import op
import sqlalchemy as sa

revision = "004_my_new_table"
down_revision = "003_fk_ondelete"


def upgrade() -> None:
    op.create_table(
        "my_new_table",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )


def downgrade() -> None:
    op.drop_table("my_new_table")
```

### Step 4 — Apply

```bash
alembic upgrade head
```

### Step 5 — Verify

```bash
# Check the migration was applied
alembic current

# Or connect to the database
just db-shell
\dt  -- list tables
```

---

## Data Migrations

For data migrations (transforming existing data, not just schema), use `op.execute()`:

```python
def upgrade() -> None:
    # Add column
    op.add_column("events", sa.Column("category", sa.String(50), nullable=True))

    # Backfill data
    op.execute("UPDATE events SET category = 'sensor' WHERE event_type = 'numerical'")

    # Now make it non-nullable
    op.alter_column("events", "category", nullable=False)
```

---

## Async Considerations

The `env.py` handles async engines transparently:

```python
async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()
```

You don't need to do anything special — just run `alembic upgrade head` as normal.

---

## Docker / Production

In production, migrations run automatically on startup via the Docker entrypoint:

```bash
# In the backend Dockerfile entrypoint
alembic upgrade head && uvicorn webmacs_backend.main:app
```

For manual production migrations:

```bash
docker compose exec backend alembic upgrade head
```

---

## Troubleshooting

### "Can't locate revision"

```bash
# Reset Alembic version tracking
alembic stamp head
```

### "Target database is not up to date"

```bash
# Apply pending migrations first
alembic upgrade head
```

### psycopg2 Not Installed

```
ModuleNotFoundError: No module named 'psycopg2'
```

Install it:

```bash
uv add psycopg2-binary --dev
```

---

## Next Steps

- [Database Architecture](../architecture/database.md) — table schemas and relationships
- [Testing](testing.md) — writing tests with database fixtures
- [Contributing](contributing.md) — development workflow
