#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# WebMACS — First-Time Installation Script
# Run this on a fresh Revolution Pi (or any Debian/Ubuntu with Docker).
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/stefanposs/webmacs/main/scripts/install.sh | bash
#   — or —
#   ./scripts/install.sh [update-bundle.tar.gz]
#
# What it does:
#   1. Installs Docker + Docker Compose (if missing)
#   2. Creates /opt/webmacs directory structure
#   3. Generates secure .env file
#   4. Loads images from bundle (if provided) or pulls from build
#   5. Starts the WebMACS stack
#   6. Creates systemd service for auto-start on boot
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="/opt/webmacs"
BUNDLE_PATH="${1:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}▶${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠️${NC}  $*"; }
err()   { echo -e "${RED}❌${NC} $*"; exit 1; }

echo ""
echo "═══════════════════════════════════════════════════════"
echo "   WebMACS Installation"
echo "   Web-based Monitoring and Control System"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Check prerequisites ──────────────────────────────────────────────
info "Checking prerequisites..."

if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root (sudo)."
fi

ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" && "$ARCH" != "x86_64" ]]; then
    warn "Unsupported architecture: $ARCH (expected aarch64, armv7l, or x86_64)"
fi

# ── 2. Install Docker ───────────────────────────────────────────────────
if ! command -v docker &> /dev/null; then
    info "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    ok "Docker installed"
else
    ok "Docker already installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
fi

# Ensure Docker Compose plugin is available
if ! docker compose version &> /dev/null; then
    info "Installing Docker Compose plugin..."
    apt-get update -qq
    apt-get install -y -qq docker-compose-plugin
    ok "Docker Compose installed"
else
    ok "Docker Compose available"
fi

# ── 3. Create directory structure ────────────────────────────────────────
info "Creating directory structure at ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"/{updates,updates/applied,updates/backups,updates/failed,plugins}
ok "Directories created"

# ── 4. Generate .env file ───────────────────────────────────────────────
ENV_FILE="${INSTALL_DIR}/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    info "Generating secure .env configuration..."

    # Generate secure random values
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)

    cat > "$ENV_FILE" <<EOF
# WebMACS Configuration — generated on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# ─────────────────────────────────────────────────────────────────

# Database password (auto-generated — do not change after first start)
DB_PASSWORD=${DB_PASSWORD}

# JWT secret key (auto-generated)
SECRET_KEY=${SECRET_KEY}

# Admin credentials (change the password after first login!)
ADMIN_EMAIL=admin@webmacs.local
ADMIN_USERNAME=admin
ADMIN_PASSWORD=WebMACS-$(openssl rand -hex 4)

# WebMACS version (managed by updater — do not edit manually)
WEBMACS_VERSION=latest

# Controller settings
POLL_INTERVAL=1.0
TELEMETRY_MODE=http
WEBMACS_AUTO_SEED=true
EOF

    chmod 600 "$ENV_FILE"
    ok ".env created at ${ENV_FILE}"
    echo ""
    warn "SAVE THESE CREDENTIALS (shown only once):"
    echo "   Admin email:    $(grep ADMIN_EMAIL "$ENV_FILE" | cut -d= -f2)"
    echo "   Admin password: $(grep ADMIN_PASSWORD "$ENV_FILE" | cut -d= -f2)"
    echo ""
else
    ok ".env already exists — keeping existing configuration"
fi

# ── 5. Extract and load update bundle ────────────────────────────────────
if [[ -n "$BUNDLE_PATH" && -f "$BUNDLE_PATH" ]]; then
    info "Loading images from update bundle: ${BUNDLE_PATH}..."

    WORK_DIR=$(mktemp -d)
    trap 'rm -rf "$WORK_DIR"' EXIT

    tar -xzf "$BUNDLE_PATH" -C "$WORK_DIR"

    # Validate manifest
    if [[ ! -f "$WORK_DIR/manifest.json" ]]; then
        err "Invalid bundle: manifest.json not found"
    fi

    VERSION=$(python3 -c "import json; print(json.load(open('$WORK_DIR/manifest.json'))['version'])" 2>/dev/null || echo "unknown")
    info "Bundle version: ${VERSION}"

    # Verify checksum
    EXPECTED_SHA=$(python3 -c "import json; print(json.load(open('$WORK_DIR/manifest.json'))['images_sha256'])" 2>/dev/null || echo "")
    if [[ -n "$EXPECTED_SHA" ]]; then
        ACTUAL_SHA=$(sha256sum "$WORK_DIR/images.tar" | cut -d' ' -f1)
        if [[ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]]; then
            err "Checksum mismatch! Bundle may be corrupted."
        fi
        ok "Checksum verified"
    fi

    # Load Docker images
    info "Loading Docker images (this may take several minutes on RevPi)..."
    docker load -i "$WORK_DIR/images.tar"
    ok "Images loaded"

    # Copy compose file
    if [[ -f "$WORK_DIR/docker-compose.prod.yml" ]]; then
        cp "$WORK_DIR/docker-compose.prod.yml" "${INSTALL_DIR}/docker-compose.prod.yml"
    fi

    # Update version in .env
    sed -i "s/^WEBMACS_VERSION=.*/WEBMACS_VERSION=${VERSION}/" "$ENV_FILE"

elif [[ -f "${INSTALL_DIR}/docker-compose.prod.yml" ]]; then
    ok "Using existing images"
else
    err "No update bundle provided and no existing installation found.\n   Usage: $0 <path-to-webmacs-update-bundle.tar.gz>"
fi

# Ensure compose file exists
if [[ ! -f "${INSTALL_DIR}/docker-compose.prod.yml" ]]; then
    err "docker-compose.prod.yml not found in ${INSTALL_DIR}/"
fi

# ── 6. Start WebMACS ────────────────────────────────────────────────────
info "Starting WebMACS..."
cd "${INSTALL_DIR}"
docker compose -f docker-compose.prod.yml --env-file .env up -d

# Wait for backend health
info "Waiting for backend to become healthy..."
RETRIES=30
for i in $(seq 1 $RETRIES); do
    if docker compose -f docker-compose.prod.yml exec -T backend \
        python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
        ok "Backend is healthy"
        break
    fi
    if [[ $i -eq $RETRIES ]]; then
        warn "Backend not yet healthy — check logs with: docker compose -f docker-compose.prod.yml logs backend"
    fi
    sleep 2
done

# ── 7. Create systemd service ───────────────────────────────────────────
SYSTEMD_FILE="/etc/systemd/system/webmacs.service"
if [[ ! -f "$SYSTEMD_FILE" ]]; then
    info "Creating systemd service for auto-start on boot..."
    cat > "$SYSTEMD_FILE" <<EOF
[Unit]
Description=WebMACS - Web-based Monitoring and Control System
Documentation=https://github.com/stefanposs/webmacs
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable webmacs.service
    ok "systemd service created and enabled"
else
    ok "systemd service already exists"
fi

# ── 8. Done ─────────────────────────────────────────────────────────────
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "═══════════════════════════════════════════════════════"
echo ""
echo "   ✅ WebMACS installed successfully!"
echo ""
echo "   Open in browser:"
echo "      http://${IP_ADDR}"
echo ""
echo "   Admin credentials are in: ${ENV_FILE}"
echo ""
echo "   Useful commands:"
echo "      Status:   cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml ps"
echo "      Logs:     cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml logs -f"
echo "      Restart:  sudo systemctl restart webmacs"
echo "      Backup:   cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U webmacs webmacs > backup.sql"
echo ""
echo "   To update:"
echo "      Upload a .tar.gz bundle via the WebMACS UI (OTA Updates → Upload)"
echo "      — or —"
echo "      Copy a bundle to ${INSTALL_DIR}/updates/"
echo ""
echo "═══════════════════════════════════════════════════════"
