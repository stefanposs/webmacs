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

# ── Helper: wait for apt/dpkg lock ───────────────────────────────────────────
wait_for_apt_lock() {
    local max_wait=120  # seconds
    local waited=0
    while fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock /var/cache/apt/archives/lock >/dev/null 2>&1; do
        if [[ $waited -eq 0 ]]; then
            info "Waiting for other package manager to finish..."
        fi
        sleep 5
        waited=$((waited + 5))
        if [[ $waited -ge $max_wait ]]; then
            warn "Still waiting after ${waited}s — apt/dpkg lock held by another process."
            warn "Run 'ps aux | grep -E apt\|dpkg' to investigate."
            err "Timed out waiting for package manager lock after ${max_wait}s."
        fi
    done
    if [[ $waited -gt 0 ]]; then
        ok "Package manager lock released (waited ${waited}s)"
    fi
}

# ── Helper: install Docker with codename fallback ───────────────────────
install_docker() {
    local codename=""
    local os_id=""
    if [[ -f /etc/os-release ]]; then
        codename=$(. /etc/os-release && echo "${VERSION_CODENAME:-}")
        os_id=$(. /etc/os-release && echo "${ID:-}")
    fi

    # Clean up broken Docker apt sources from previous failed installs
    for f in /etc/apt/sources.list.d/docker*; do
        [[ -f "$f" ]] || continue
        if grep -qE "(raspbian|${codename:-NONE})" "$f" 2>/dev/null; then
            info "Removing stale Docker apt source: $f"
            rm -f "$f"
        fi
    done

    local supported="buster bullseye bookworm focal jammy noble"
    local fallback="bookworm"

    # Docker publishes packages under "debian" (not "raspbian") and "ubuntu"
    local repo_distro="debian"
    [[ "$os_id" == "ubuntu" ]] && repo_distro="ubuntu"

    if echo "$supported" | grep -qw "${codename:-}"; then
        info "Installing Docker via get.docker.com..."
        curl -fsSL https://get.docker.com | sh
    else
        warn "OS codename '${codename:-unknown}' not yet supported by Docker's install script."
        info "Installing Docker manually (using '${fallback}' packages for ${repo_distro})..."

        apt-get update -qq
        apt-get install -y -qq ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings

        local keyring="/etc/apt/keyrings/docker.gpg"
        rm -f "$keyring"
        curl -fsSL "https://download.docker.com/linux/${repo_distro}/gpg" \
            | gpg --dearmor -o "$keyring"
        chmod a+r "$keyring"

        local arch
        arch=$(dpkg --print-architecture)
        echo "deb [arch=${arch} signed-by=${keyring}] https://download.docker.com/linux/${repo_distro} ${fallback} stable" \
            > /etc/apt/sources.list.d/docker.list

        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    fi

    systemctl enable docker
    systemctl start docker
}

# ── 2. Install Docker ───────────────────────────────────────────────────────
if ! command -v docker &> /dev/null; then
    wait_for_apt_lock
    install_docker
    ok "Docker installed"
else
    ok "Docker already installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
fi

if ! docker compose version &> /dev/null; then
    wait_for_apt_lock
    info "Installing Docker Compose plugin..."
    apt-get update -qq
    apt-get install -y -qq docker-compose-plugin
    ok "Docker Compose installed"
else
    ok "Docker Compose available"
fi

# ── 3. Create directory structure ────────────────────────────────────────
info "Creating directory structure at ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"/{updates,updates/applied,updates/backups,updates/failed,plugins,certs}
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

    chmod 640 "$ENV_FILE"
    chgrp docker "$ENV_FILE" 2>/dev/null || true
    ok ".env created at ${ENV_FILE}"
    echo ""
    warn "SAVE THESE CREDENTIALS (shown only once):"
    echo "   Admin email:    admin@webmacs.local"
    echo "   Admin password: ${ADMIN_PW}"
    echo ""
else
    ok ".env already exists — keeping existing configuration"
fi

# ── 5. Generate TLS certificate (self-signed if none provided) ──────────
CERT_DIR="${INSTALL_DIR}/certs"
if [[ ! -f "${CERT_DIR}/cert.pem" || ! -f "${CERT_DIR}/key.pem" ]]; then
    info "No TLS certificate found — generating self-signed certificate..."
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout "${CERT_DIR}/key.pem" \
        -out "${CERT_DIR}/cert.pem" \
        -days 3650 \
        -subj "/CN=webmacs.local/O=WebMACS/OU=Self-Signed" \
        2>/dev/null
    chmod 600 "${CERT_DIR}/key.pem"
    chmod 644 "${CERT_DIR}/cert.pem"
    ok "Self-signed TLS certificate created (valid for 10 years)"
    warn "Replace with your own certificate for production:"
    warn "  ${CERT_DIR}/cert.pem  (certificate)"
    warn "  ${CERT_DIR}/key.pem   (private key)"
    echo ""
else
    ok "TLS certificate found in ${CERT_DIR}/"
fi

# ── 6. Load images ──────────────────────────────────────────────────────
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

    # Copy compose file and nginx config from bundle
    if [[ -f "$WORK_DIR/docker-compose.prod.yml" ]]; then
        cp "$WORK_DIR/docker-compose.prod.yml" "${INSTALL_DIR}/docker-compose.prod.yml"
    fi
    if [[ -f "$WORK_DIR/nginx.conf" ]]; then
        cp "$WORK_DIR/nginx.conf" "${INSTALL_DIR}/nginx.conf"
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

    GITHUB_BASE="https://raw.githubusercontent.com/stefanposs/webmacs/main"
    if curl -fsSL "${GITHUB_BASE}/docker-compose.prod.yml" -o "${INSTALL_DIR}/docker-compose.prod.yml" && \
       curl -fsSL "${GITHUB_BASE}/docker/nginx.conf" -o "${INSTALL_DIR}/nginx.conf"; then
        ok "Downloaded docker-compose.prod.yml + nginx.conf"
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

# ── 7. Start WebMACS ────────────────────────────────────────────────────
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

# ── 8. Create systemd service ───────────────────────────────────────────
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

# ── 9. Done ─────────────────────────────────────────────────────────────
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "═══════════════════════════════════════════════════════"
echo ""
echo "   ✅ WebMACS installed successfully!"
echo ""
echo "   Open in browser:"
echo "      https://${IP_ADDR}"
echo ""
echo "   Admin credentials are in: ${ENV_FILE}"
echo ""
echo "   TLS certificate:"
echo "      ${CERT_DIR}/cert.pem  (replace with your own for production)"
echo ""
echo "   Useful commands:"
echo "      Status:   cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml ps"
echo "      Logs:     cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml logs -f"
echo "      Restart:  sudo systemctl restart webmacs"
echo ""
echo "═══════════════════════════════════════════════════════"
