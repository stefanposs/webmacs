#!/bin/sh
set -e

echo "▶ Ensuring base database tables exist..."
cd /app
python - <<'PYEOF'
import asyncio, sys, os

# Ensure the app package is importable (fallback for editable / src-layout installs)
sys.path.insert(0, os.path.join(os.path.dirname(__file__) or ".", "src"))

from webmacs_backend.models import Base
from webmacs_backend.database import engine

async def _create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(_create())
print("  ✓ Base tables ensured")
PYEOF

echo "▶ Running database migrations..."
alembic upgrade head

echo "▶ Starting WebMACS Backend..."
exec "$@"
