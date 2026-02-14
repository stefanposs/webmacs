# Backend Dockerfile - multi-stage build
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy and install all plugin packages (metadata only — no [hardware] extras)
COPY plugins/core/ /tmp/plugins-core/
COPY plugins/simulated/ /tmp/plugins-simulated/
COPY plugins/system/ /tmp/plugins-system/
COPY plugins/revpi/ /tmp/plugins-revpi/
RUN uv pip install --system --no-cache \
    /tmp/plugins-core/ \
    /tmp/plugins-simulated/ \
    /tmp/plugins-system/ \
    /tmp/plugins-revpi/ \
    && rm -rf /tmp/plugins-core/ /tmp/plugins-simulated/ /tmp/plugins-system/ /tmp/plugins-revpi/

# Ensure pip is available for runtime plugin installs (upload via UI)
RUN uv pip install --system pip

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/src/ ./src/
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic/ ./alembic/
RUN uv pip install --system --no-cache .

EXPOSE 8000

CMD ["uvicorn", "webmacs_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
