# Backend Dockerfile - multi-stage build
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files and install
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/src/ ./src/
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic/ ./alembic/
RUN uv pip install --system --no-cache .

EXPOSE 8000

CMD ["uvicorn", "webmacs_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
