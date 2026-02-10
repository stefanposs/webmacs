# Installation

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| **Docker** | 24+ | Container runtime |
| **Docker Compose** | v2+ | Multi-container orchestration |
| **Git** | 2.x | Source control |
| **just** | 1.x | Task runner *(optional, recommended)* |

For local development without Docker you also need:

| Tool | Version | Purpose |
|---|---|---|
| **Python** | 3.14+ | Backend & Controller |
| **Node.js** | 22+ | Frontend build |
| **PostgreSQL** | 17+ | Database |

---

## Clone the Repository

```bash
git clone https://github.com/stefanposs/webmacs.git
cd webmacs
```

---

## Docker (Recommended)

The fastest way to run WebMACS:

```bash
# Copy environment defaults
cp .env.example .env

# Build & start all four services
docker compose up --build -d
```

This spins up:

| Service | Port | Description |
|---|---|---|
| `db` | 5432 | PostgreSQL 17-alpine |
| `backend` | 8000 | FastAPI (Uvicorn) |
| `frontend` | 80 | Vue 3 SPA (Nginx) |
| `controller` | — | IoT telemetry agent |

Verify everything is healthy:

```bash
docker compose ps
```

---

## Local Development Setup

### Backend

```bash
cd backend
uv sync --all-extras
uv run uvicorn webmacs_backend.main:create_app --factory --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # → http://localhost:5173
```

### Controller

```bash
cd controller
uv sync --all-extras
uv run python -m webmacs_controller
```

---

## Install `just` (Task Runner)

```bash
# macOS
brew install just

# Linux
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# Windows (scoop)
scoop install just
```

Then run `just` from the project root to see all available commands:

```bash
just          # lists all recipes
just dev      # start full dev stack
just test     # run all tests
```

---

## Next Steps

- [Quick Start](quick-start.md) — first login and experiment
- [Configuration](configuration.md) — environment variables reference
