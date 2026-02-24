# Installation

## Two Deployment Paths

| Path | Target Audience | Method |
|---|---|---|
| **Revolution Pi** | Industrial operators | `scripts/install-revpi.sh` — fully automated |
| **Raspberry Pi 3/4/5** | Makers, home automation | `scripts/install-rpi.sh` — fully automated, RPi-optimised |
| **Development (local)** | Developers | `docker compose up` or local services |

!!! tip "For most users"
    The **easiest way** to install WebMACS is the appropriate install script in `scripts/`.
    It handles Docker installation, credential generation, cgroup configuration, and service startup — no manual setup required.

---

## Production Installation (Recommended)

### Revolution Pi — `scripts/install-revpi.sh`

Designed for **KUNBUS Revolution Pi** (Connect, Connect 4, Connect S) and any Debian/Ubuntu ARM server:

```bash
# On the RevPi:
sudo bash scripts/install-revpi.sh webmacs-update-2.0.0.tar.gz
```

Or via one-liner (fresh device):

```bash
curl -sSL https://raw.githubusercontent.com/stefanposs/webmacs/main/scripts/install-revpi.sh | sudo bash
```

### Raspberry Pi 3/4/5 — `scripts/install-rpi.sh`

Designed for **consumer Raspberry Pi** hardware (Pi 3B/3B+, Pi 4, Pi 5). Extends the RevPi
script with additional RPi-specific setup:

- Enables **cgroup memory** in `cmdline.txt` (required for Docker on RPi)
- Configures **swap** automatically based on available RAM
- Sets optimal **Docker storage driver** (`overlay2` + journald)
- Supports **Raspberry Pi 3** with 1 GB RAM (minimum 750 MB)

```bash
# On the Raspberry Pi:
sudo bash scripts/install-rpi.sh webmacs-update-2.0.0.tar.gz
```

Or via one-liner:

```bash
curl -sSL https://raw.githubusercontent.com/stefanposs/webmacs/main/scripts/install-rpi.sh | sudo bash
```

!!! warning "Reboot may be required (RPi only)"
    On a fresh Raspberry Pi OS installation, the script enables cgroup memory in `cmdline.txt`.
    A **reboot is required** before Docker works correctly. The script will display a clear notice
    if a reboot is needed.

**What both scripts do (in order):**

1. Detects hardware and verifies compatibility
2. Installs Docker + Docker Compose (if missing)
3. Creates `/opt/webmacs` with an `updates/` directory structure
4. Generates a secure `.env` file with random `SECRET_KEY`, `DB_PASSWORD`, and admin password
5. Extracts and loads Docker images from the bundle (SHA-256 verified)
6. Starts all 4 containers via `docker-compose.prod.yml`
7. Creates a **systemd service** (`webmacs.service`) for auto-start on boot

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
