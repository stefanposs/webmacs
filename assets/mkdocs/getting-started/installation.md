# Installation

## Two Deployment Paths

| Path | Target Audience | Method |
|---|---|---|
| **Production (RevPi / Server)** | Operators, customers | `scripts/install.sh` — fully automated |
| **Development (local)** | Developers | `docker compose up` or local services |

!!! tip "For most users"
    The **easiest way** to install and run WebMACS is the `install.sh` script in the `scripts/` directory.
    It handles Docker installation, credential generation, and service startup — no manual setup required.

---

## Production Installation (Recommended)

### Using `scripts/install.sh`

The install script is designed for **Revolution Pi, Raspberry Pi, or any Debian/Ubuntu server**.
It performs a complete, hands-free installation:

```bash
# On the target device:
sudo bash scripts/install.sh webmacs-update-2.0.0.tar.gz
```

**What the script does (in order):**

1. Installs Docker + Docker Compose (if missing)
2. Creates `/opt/webmacs` with an `updates/` directory structure
3. Generates a secure `.env` file with random `SECRET_KEY`, `DB_PASSWORD`, and admin password
4. Extracts and loads Docker images from the bundle (SHA-256 verified)
5. Starts all 4 containers via `docker-compose.prod.yml`
6. Creates a **systemd service** (`webmacs.service`) for auto-start on boot

!!! danger "Save Your Credentials"
    The admin password is shown **only once** during installation.
    It is also stored in `/opt/webmacs/.env`.

After installation, open `http://<device-ip>` in a browser and log in.

### Using `scripts/build-update-bundle.sh`

Developers use this script to **create the `.tar.gz` update bundle** that `install.sh` consumes:

```bash
./scripts/build-update-bundle.sh 2.1.0
# Output: dist/webmacs-update-2.1.0.tar.gz
```

**What the script does:**

1. Builds all Docker images via `docker compose build --no-cache`
2. Tags images with the version number
3. Exports images to a single `images.tar`
4. Computes SHA-256 checksum
5. Creates `manifest.json` with version, checksum, and image list
6. Packages everything into a `.tar.gz` bundle

The resulting bundle is fully self-contained — it can be deployed to an airgapped device via USB stick.

!!! info "CI/CD Alternative"
    Instead of building locally, push a git tag (`v2.1.0`) and GitHub Actions builds a multi-arch bundle automatically.
    See [OTA Updates](../guide/ota.md) for details.

---

## Development Setup

!!! note "Docker Compose for Development Only"
    The `docker-compose.yml` in the project root is intended for **local development**.
    For production deployments, always use `scripts/install.sh` with the production compose file.

### Docker (Full Stack)

The fastest way to spin up the entire stack locally:

```bash
cp .env.example .env
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

### Local Services (Without Docker)

For faster iteration without rebuilding containers:

### Prerequisites (Development)

| Tool | Version | Purpose |
|---|---|---|
| **Python** | 3.13+ | Backend & Controller |
| **Node.js** | 22+ | Frontend build |
| **PostgreSQL** | 17+ | Database |
| **just** | 1.x | Task runner *(optional, recommended)* |

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
