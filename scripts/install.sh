#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# WebMACS — Universal Installation Script
# Works on: Revolution Pi, Raspberry Pi, Ubuntu/Debian x86_64
#
# This script is bundled inside OTA update packages and referenced by GitHub
# Releases for first-time installation.
#
# Usage:
#   sudo bash install.sh <webmacs-update-VERSION.tar.gz>
#   — or (pull from Docker Hub, no bundle) —
#   sudo bash install.sh
#
# What it does:
#   1. Detects hardware (RevPi / Raspberry Pi / x86)
#   2. Installs Docker + Docker Compose (if missing)
#   3. Creates /opt/webmacs directory structure
#   4. Generates secure .env file (first install only)
#   5. Loads images from bundle or pulls from Docker Hub
#   6. Runs database migrations
#   7. Starts the WebMACS stack
#   8. Creates systemd service for auto-start on boot
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="/opt/webmacs"
BUNDLE_PATH="${1:-}"

# ── Colors ───────────────────────────────────────────────────────────────
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
echo "   WebMACS — Installation"
echo "   Web-based Monitoring and Control System"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Check prerequisites ──────────────────────────────────────────────
info "Checking prerequisites..."

if [[ $EUID -ne 0 ]]; then
    err "Run with sudo: sudo bash $0 ${*:-}"
fi

ARCH=$(uname -m)
case "$ARCH" in
    aarch64) ok "Architecture: 64-bit ARM (aarch64)" ;;
    armv7l)  ok "Architecture: 32-bit ARM (armv7l)" ;;
    x86_64)  ok "Architecture: x86_64" ;;
    *)       err "Unsupported architecture: ${ARCH}" ;;
esac

# Detect hardware model
HW_MODEL=""
for model_file in /proc/device-tree/model /sys/firmware/devicetree/base/model; do
    if [[ -f "$model_file" ]]; then
        HW_MODEL=$(tr -d '\0' < "$model_file" 2>/dev/null || true)
        break
    fi
done
if [[ -z "$HW_MODEL" ]]; then
    HW_MODEL=$(grep -i "Model" /proc/cpuinfo 2>/dev/null | head -1 | cut -d':' -f2 | xargs || true)
fi

if [[ -n "$HW_MODEL" ]]; then
    ok "Hardware: ${HW_MODEL}"
else
    ok "Hardware: generic ${ARCH}"
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

    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    ADMIN_PW="WebMACS-$(openssl rand -hex 4)"

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
ADMIN_PASSWORD=${ADMIN_PW}

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
    echo "   Admin email:    admin@webmacs.local"
    echo "   Admin password: ${ADMIN_PW}"
    echo ""
else
    ok ".env already exists — keeping existing configuration"
fi

# ── 5. Load images ──────────────────────────────────────────────────────
if [[ -n "$BUNDLE_PATH" && -f "$BUNDLE_PATH" ]]; then
    info "Loading images from bundle: ${BUNDLE_PATH}..."

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
    info "Loading Docker images (this may take several minutes)..."
    docker load -i "$WORK_DIR/images.tar"
    ok "Images loaded"

    # Copy compose file from bundle
    if [[ -f "$WORK_DIR/docker-compose.prod.yml" ]]; then
        cp "$WORK_DIR/docker-compose.prod.yml" "${INSTALL_DIR}/docker-compose.prod.yml"
    fi

    # Update version in .env
    sed -i "s/^WEBMACS_VERSION=.*/WEBMACS_VERSION=${VERSION}/" "$ENV_FILE"

elif [[ -f "${INSTALL_DIR}/docker-compose.prod.yml" ]]; then
    info "No bundle — pulling latest images from Docker Hub..."
    cd "${INSTALL_DIR}"
    if docker compose -f docker-compose.prod.yml --env-file .env pull; then
        ok "Images pulled"
    else
        warn "Pull failed — using existing local images"
    fi
else
    info "No bundle — downloading compose file and pulling images..."

    COMPOSE_URL="https://raw.githubusercontent.com/stefanposs/webmacs/main/docker-compose.prod.yml"
    if curl -fsSL "$COMPOSE_URL" -o "${INSTALL_DIR}/docker-compose.prod.yml"; then
        ok "Downloaded docker-compose.prod.yml"
        cd "${INSTALL_DIR}"
        if ! docker compose -f docker-compose.prod.yml --env-file .env pull; then
            err "Failed to pull images. Check your internet connection."
        fi
        ok "Images pulled"
    else
        err "Failed to download docker-compose.prod.yml.\nUsage: sudo bash $0 <path-to-bundle.tar.gz>"
    fi
fi

# Ensure compose file exists
if [[ ! -f "${INSTALL_DIR}/docker-compose.prod.yml" ]]; then
    err "docker-compose.prod.yml not found in ${INSTALL_DIR}/"
fi

# ── 6. Start WebMACS ────────────────────────────────────────────────────
info "Starting WebMACS..."
cd "${INSTALL_DIR}"
docker compose -f docker-compose.prod.yml --env-file .env up -d

info "Waiting for backend to become healthy (may take 2–3 min on first start)..."
RETRIES=60
for i in $(seq 1 $RETRIES); do
    if docker compose -f docker-compose.prod.yml exec -T backend \
        python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
        ok "Backend is healthy"
        break
    fi
    if [[ $i -eq $RETRIES ]]; then
        warn "Backend not yet healthy after $((RETRIES * 3))s — check logs:"
        warn "  cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml logs backend"
    fi
    sleep 3
done

# ── 7. Create systemd service ───────────────────────────────────────────
SYSTEMD_FILE="/etc/systemd/system/webmacs.service"
if [[ ! -f "$SYSTEMD_FILE" ]]; then
    info "Creating systemd service for auto-start on boot..."
    cat > "$SYSTEMD_FILE" <<EOF
[Unit]
Description=WebMACS - Web-based Monitoring and Control System
Documentation=https://github.com/stefanposs/webmacs
After=docker.service network-online.target
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=300

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
echo ""
echo "═══════════════════════════════════════════════════════"
