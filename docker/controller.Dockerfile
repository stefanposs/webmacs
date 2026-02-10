# Controller Dockerfile
FROM python:3.14-rc-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files and install
COPY controller/pyproject.toml ./pyproject.toml
COPY controller/src/ ./src/
RUN uv pip install --system --no-cache .

CMD ["python", "-m", "webmacs_controller"]
