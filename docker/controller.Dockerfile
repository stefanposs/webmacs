# Controller Dockerfile
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy and install all plugin packages
COPY plugins/core/ /tmp/plugins-core/
COPY plugins/simulated/ /tmp/plugins-simulated/
COPY plugins/system/ /tmp/plugins-system/
COPY plugins/revpi/ /tmp/plugins-revpi/
RUN uv pip install --system --no-cache \
    /tmp/plugins-core/ \
    /tmp/plugins-simulated/ \
    /tmp/plugins-system/ \
    "/tmp/plugins-revpi/[hardware]" \
    && rm -rf /tmp/plugins-core/ /tmp/plugins-simulated/ /tmp/plugins-system/ /tmp/plugins-revpi/

COPY controller/pyproject.toml ./pyproject.toml
COPY controller/src/ ./src/
RUN uv pip install --system --no-cache .

CMD ["python", "-m", "webmacs_controller"]
