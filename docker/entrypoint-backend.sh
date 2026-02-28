#!/bin/sh
set -e

echo "▶ Ensuring base database tables exist..."
python -c "
import asyncio
from webmacs_backend.database import Base, engine

async def _create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

# Import models so Base.metadata knows about all tables
import webmacs_backend.models  # noqa: F401
asyncio.run(_create())
"

echo "▶ Running database migrations..."
alembic upgrade head

echo "▶ Starting WebMACS Backend..."
exec "$@"
