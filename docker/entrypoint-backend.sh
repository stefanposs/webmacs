#!/bin/sh
set -e

echo "▶ Ensuring base database tables exist..."
cd /app
python - <<'PYEOF'
import asyncio, sys, os

# Ensure the app package is importable (fallback for src-layout installs)
sys.path.insert(0, os.path.join(os.path.dirname(__file__) or ".", "src"))

from webmacs_backend.models import Base
from webmacs_backend.database import engine

async def _create():
    async with engine.begin() as conn:
        # Check if this is a fresh DB (no alembic_version table yet)
        result = await conn.run_sync(
            lambda sync_conn: sync_conn.dialect.has_table(sync_conn, "alembic_version")
        )
        fresh_db = not result

        # create_all is idempotent for tables, but PG ENUM types may
        # raise DuplicateObject on repeated runs, so only create on
        # a truly fresh database.
        if fresh_db:
            await conn.run_sync(Base.metadata.create_all)
            print("  ✓ Base tables created (fresh database)")
        else:
            print("  ✓ Database already initialised — skipping create_all")

    await engine.dispose()
    return fresh_db

fresh = asyncio.run(_create())

# If we just created all tables, stamp alembic to head so it does not
# try to re-create tables/enums that create_all() already made.
if fresh:
    import subprocess
    subprocess.run(["alembic", "stamp", "head"], check=True)
    print("  ✓ Alembic stamped to head")
PYEOF

echo "▶ Running database migrations..."
alembic upgrade head

echo "▶ Starting WebMACS Backend..."
exec "$@"
