#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# WebMACS — Universal Installation Script
# Works on: Revolution Pi, Raspberry Pi (64-bit), Ubuntu/Debian x86_64
# Requires: 64-bit OS (aarch64 or x86_64)
#
# This script is bundled inside OTA update packages and referenced by GitHub
# Releases for first-time installation.
#
# Usage:
#   sudo bash install.sh <webmacs-update-VERSION.tar.gz>
#   — or (pull from Docker Hub, no bundle) —
#   sudo bash install.sh
#   — or (offline mode, use existing compose + images) —
#   sudo bash install.sh --offline
#
# What it does:
#   1. Detects hardware (RevPi / Raspberry Pi / x86)
#   2. Checks memory and configures swap (if needed)
#   3. Enables cgroup memory (required for Docker on ARM)
#   4. Installs Docker + Docker Compose (if missing)
#   5. Creates /opt/webmacs directory structure
#   6. Generates secure .env file (first install only)
#   7. Generates self-signed TLS certificate (if none provided)
#   8. Loads images from bundle or pulls from Docker Hub
#   9. Starts the WebMACS stack
#  10. Creates systemd service for auto-start on boot
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="/opt/webmacs"
# Argument parsing: support optional --offline flag or a bundle path
OFFLINE=false
BUNDLE_PATH=""
if [[ "${1:-}" == "--offline" ]]; then
    OFFLINE=true
else
    BUNDLE_PATH="${1:-}"
fi
REBOOT_REQUIRED=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${BLUE}▶${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
err()   { echo -e "${RED}✗${NC} $*"; exit 1; }
step()  { echo -e "\n${CYAN}── $* ──${NC}"; }

echo ""
echo "═══════════════════════════════════════════════════════"
echo "   WebMACS — Installation"
echo "   Web-based Monitoring and Control System"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Root check ────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    err "Run with sudo: sudo bash $0 ${*:-}"
fi

# ── 2. Hardware detection ────────────────────────────────────────────────────
step "Checking hardware"

ARCH=$(uname -m)

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

# Architecture check
case "$ARCH" in
    aarch64) ok "Architecture: 64-bit ARM (aarch64)" ;;
    armv7l)
        echo ""
        err "32-bit ARM (armv7l) detected — WebMACS Docker images require 64-bit.\n\n" \
            "  If running on a Raspberry Pi 3/4/5, please re-flash with\n" \
            "  'Raspberry Pi OS Lite (64-bit)' and run this installer again.\n" \
            "  RevPi: use the latest KUNBUS 64-bit image.\n"
        ;;
    x86_64)  ok "Architecture: x86_64" ;;
    *)       err "Unsupported architecture: ${ARCH}" ;;
esac

# ── 3. OS check ──────────────────────────────────────────────────────────────
step "Checking OS"

if [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    source /etc/os-release
    ok "OS: ${PRETTY_NAME:-unknown}"
    case "${ID:-}" in
        debian|raspbian|ubuntu) ;;
        *) warn "Untested OS '${ID:-unknown}'. Proceeding, but Debian/Ubuntu is recommended." ;;
    esac
else
    warn "Cannot read /etc/os-release. Proceeding anyway."
fi

# ── 4. Memory check + swap ──────────────────────────────────────────────────
step "Checking memory"

TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_MB=$((TOTAL_RAM_KB / 1024))
TOTAL_RAM_GB=$((TOTAL_RAM_MB / 1024))

if [[ $TOTAL_RAM_MB -lt 750 ]]; then
    err "Only ${TOTAL_RAM_MB} MB RAM detected. WebMACS requires at least 750 MB."
elif [[ $TOTAL_RAM_MB -lt 1024 ]]; then
    warn "${TOTAL_RAM_MB} MB RAM — minimum met, swap will be configured."
elif [[ $TOTAL_RAM_MB -lt 2048 ]]; then
    warn "${TOTAL_RAM_MB} MB RAM — sufficient, but 4 GB recommended for best performance."
else
    ok "${TOTAL_RAM_MB} MB RAM (≈ ${TOTAL_RAM_GB} GB)"
fi

# Configure swap if RAM < 4 GB
if [[ $TOTAL_RAM_MB -lt 4096 ]]; then
    SWAP_FILE="/var/swap"
    CURRENT_SWAP_KB=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    CURRENT_SWAP_MB=$((CURRENT_SWAP_KB / 1024))

    # < 1 GB RAM → 3 GB swap
    # 1–2 GB RAM → 2 GB swap
    # 2–4 GB RAM → 1 GB swap
    if [[ $TOTAL_RAM_MB -lt 1024 ]]; then
        TARGET_SWAP_MB=3072
    elif [[ $TOTAL_RAM_MB -lt 2048 ]]; then
        TARGET_SWAP_MB=2048
    else
        TARGET_SWAP_MB=1024
    fi

    if [[ $CURRENT_SWAP_MB -lt $((TARGET_SWAP_MB - 256)) ]]; then
        info "Configuring ${TARGET_SWAP_MB} MB swap (current: ${CURRENT_SWAP_MB} MB)..."

        # Disable existing dphys-swapfile if present
        if command -v dphys-swapfile &>/dev/null; then
            dphys-swapfile swapoff 2>/dev/null || true
        fi

        # Remove old swap
        swapoff "$SWAP_FILE" 2>/dev/null || true
        rm -f "$SWAP_FILE"

        # Create new swap
        fallocate -l "${TARGET_SWAP_MB}M" "$SWAP_FILE" || dd if=/dev/zero of="$SWAP_FILE" bs=1M count="$TARGET_SWAP_MB" status=none
        chmod 600 "$SWAP_FILE"
        mkswap "$SWAP_FILE" -q
        swapon "$SWAP_FILE"

        # Persist via fstab
        if ! grep -q "$SWAP_FILE" /etc/fstab; then
            echo "${SWAP_FILE} none swap sw 0 0" >> /etc/fstab
        fi

        ok "Swap configured: ${TARGET_SWAP_MB} MB"
    else
        ok "Swap already adequate (${CURRENT_SWAP_MB} MB)"
    fi
fi

# ── 5. cgroup memory (required for Docker on ARM) ───────────────────────────
step "Checking cgroup configuration"

CMDLINE_FILE=""
for f in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
    if [[ -f "$f" ]]; then
        CMDLINE_FILE="$f"
        break
    fi
done

if [[ -z "$CMDLINE_FILE" ]]; then
    if [[ "$ARCH" == "aarch64" ]]; then
        warn "Could not find cmdline.txt — skipping cgroup check."
    else
        ok "x86_64 — cgroup check not needed"
    fi
else
    CMDLINE=$(cat "$CMDLINE_FILE")
    CGROUP_NEEDED=false

    if ! echo "$CMDLINE" | grep -q "cgroup_memory=1"; then
        CGROUP_NEEDED=true
    fi
    if ! echo "$CMDLINE" | grep -q "cgroup_enable=memory"; then
        CGROUP_NEEDED=true
    fi

    if [[ "$CGROUP_NEEDED" == true ]]; then
        info "Enabling cgroup memory in ${CMDLINE_FILE}..."
        EXTRA=""
        echo "$CMDLINE" | grep -q "cgroup_memory=1"    || EXTRA="$EXTRA cgroup_memory=1"
        echo "$CMDLINE" | grep -q "cgroup_enable=memory" || EXTRA="$EXTRA cgroup_enable=memory"

        printf '%s%s\n' "$(cat "$CMDLINE_FILE" | tr -d '\n')" "$EXTRA" > "$CMDLINE_FILE"
        ok "cgroup memory enabled in ${CMDLINE_FILE}"
        REBOOT_REQUIRED=true
    else
        ok "cgroup memory already enabled"
    fi
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

# ── Helper: install Docker with codename fallback ────────────────────────────
# Docker's get.docker.com may not support bleeding-edge OS releases (e.g.
# Raspbian Trixie).  When the current VERSION_CODENAME has no Docker repo we
# install manually, pinning the apt source to the latest supported codename.
install_docker() {
    local codename=""
    local os_id=""
    if [[ -f /etc/os-release ]]; then
        codename=$(. /etc/os-release && echo "${VERSION_CODENAME:-}")
        os_id=$(. /etc/os-release && echo "${ID:-}")
    fi

    # Clean up broken Docker apt sources from previous failed installs
    # (e.g. get.docker.com may have added a source for an unsupported codename)
    for f in /etc/apt/sources.list.d/docker*; do
        [[ -f "$f" ]] || continue
        if grep -qE "(raspbian|${codename:-NONE})" "$f" 2>/dev/null; then
            info "Removing stale Docker apt source: $f"
            rm -f "$f"
        fi
    done

    # Codenames known to have Docker packages (Debian + Ubuntu)
    local supported="buster bullseye bookworm focal jammy noble"
    local fallback="bookworm"

    # Docker publishes packages under "debian" (not "raspbian") and "ubuntu"
    local repo_distro="debian"
    [[ "$os_id" == "ubuntu" ]] && repo_distro="ubuntu"

    if echo "$supported" | grep -qw "${codename:-}"; then
        # Supported — use the official convenience script
        info "Installing Docker via get.docker.com..."
        curl -fsSL https://get.docker.com | sh
    else
        # Not (yet) supported — add Docker repo manually with fallback codename
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

# ── 6. Install Docker ────────────────────────────────────────────────────────
step "Installing Docker"

if ! command -v docker &>/dev/null; then
    wait_for_apt_lock
    install_docker
    ok "Docker installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
else
    ok "Docker already installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
fi

# Docker Compose plugin
if ! docker compose version &>/dev/null; then
    wait_for_apt_lock
    info "Installing Docker Compose plugin..."
    apt-get update -qq
    apt-get install -y -qq docker-compose-plugin
    ok "Docker Compose plugin installed"
else
    ok "Docker Compose available ($(docker compose version --short))"
fi

# Configure Docker storage driver (overlay2 + log rotation)
DOCKER_DAEMON_FILE="/etc/docker/daemon.json"
if [[ ! -f "$DOCKER_DAEMON_FILE" ]]; then
    info "Configuring Docker daemon..."
    mkdir -p /etc/docker
    cat > "$DOCKER_DAEMON_FILE" <<'EOF'
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    if ! systemctl restart docker; then
        warn "Docker daemon restart failed — removing daemon.json and retrying with defaults..."
        rm -f "$DOCKER_DAEMON_FILE"
        systemctl restart docker || err "Docker failed to start. Check: journalctl -xeu docker.service"
    fi
    ok "Docker daemon configured"
else
    ok "Docker daemon config already exists — leaving unchanged"
fi

# Verify Docker daemon is responsive
step "Verifying Docker daemon"
RETRIES=10
for i in $(seq 1 $RETRIES); do
    if docker info >/dev/null 2>&1; then
        ok "Docker daemon responsive"
        DOCKER_READY=true
        break
    fi
    info "Waiting for docker daemon to be ready... ($i/$RETRIES)"
    sleep 2
done
if [[ "${DOCKER_READY:-false}" != true ]]; then
    warn "Docker daemon not responsive; attempting to restart docker service..."
    if command -v systemctl >/dev/null 2>&1; then
        systemctl restart docker || true
    else
        warn "systemctl not available — cannot restart docker automatically"
    fi

    for i in $(seq 1 30); do
        if docker info >/dev/null 2>&1; then
            ok "Docker daemon responsive after restart"
            DOCKER_READY=true
            break
        fi
        sleep 2
    done
fi

if [[ "${DOCKER_READY:-false}" != true ]]; then
    err "Docker daemon is not running or not accessible. Check: 'systemctl status docker' and 'journalctl -u docker'"
fi

# ── 7. Create directory structure ────────────────────────────────────────────
step "Creating directory structure"

mkdir -p "${INSTALL_DIR}"/{updates,updates/applied,updates/backups,updates/failed,plugins,certs}
ok "Directories created at ${INSTALL_DIR}"

# ── 8. Generate .env file ───────────────────────────────────────────────────
step "Generating configuration"

ENV_FILE="${INSTALL_DIR}/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    info "Generating secure .env..."

    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    ADMIN_PASS="WebMACS-$(openssl rand -hex 4)"

    cat > "$ENV_FILE" <<EOF
# WebMACS Configuration — generated on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# ─────────────────────────────────────────────────────────────────

# Database password (do not change after first start)
DB_PASSWORD=${DB_PASSWORD}

# JWT secret key
SECRET_KEY=${SECRET_KEY}

# Admin credentials (change the password after first login!)
ADMIN_EMAIL=admin@webmacs.local
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMIN_PASS}

# WebMACS version (managed by updater — do not edit manually)
WEBMACS_VERSION=latest

# Controller settings
POLL_INTERVAL=1.0
TELEMETRY_MODE=http
WEBMACS_AUTO_SEED=true
EOF

    chmod 640 "$ENV_FILE"
    chgrp docker "$ENV_FILE" 2>/dev/null || true
    ok ".env created"
    echo ""
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  ⚠  SAVE THESE CREDENTIALS (shown once)    │"
    echo "  ├─────────────────────────────────────────────┤"
    printf "  │  Admin email:    %-28s│\n" "$(grep ADMIN_EMAIL "$ENV_FILE" | cut -d= -f2)"
    printf "  │  Admin password: %-28s│\n" "$(grep ADMIN_PASSWORD "$ENV_FILE" | cut -d= -f2)"
    echo "  └─────────────────────────────────────────────┘"
    echo ""
else
    ok ".env already exists — keeping existing configuration"
fi

# ── 9. Generate TLS certificate (self-signed if none provided) ──────────────
step "Setting up TLS"

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
else
    ok "TLS certificate found in ${CERT_DIR}/"
fi

# ── 10. Load images from bundle or pull ──────────────────────────────────────
step "Loading Docker images"

if [[ -n "$BUNDLE_PATH" && -f "$BUNDLE_PATH" ]]; then
    info "Loading from bundle: ${BUNDLE_PATH}..."

    WORK_DIR=$(mktemp -d)
    trap 'rm -rf "$WORK_DIR"' EXIT

    tar -xzf "$BUNDLE_PATH" -C "$WORK_DIR"

    if [[ ! -f "$WORK_DIR/manifest.json" ]]; then
        err "Invalid bundle: manifest.json not found"
    fi

    VERSION=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$WORK_DIR/manifest.json" 2>/dev/null || echo "unknown")
    info "Bundle version: ${VERSION}"

    # Checksum verification
    EXPECTED_SHA=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['images_sha256'])" "$WORK_DIR/manifest.json" 2>/dev/null || echo "")
    if [[ -n "$EXPECTED_SHA" ]]; then
        info "Verifying checksum..."
        ACTUAL_SHA=$(sha256sum "$WORK_DIR/images.tar" | cut -d' ' -f1)
        if [[ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]]; then
            err "Checksum mismatch! Bundle may be corrupted."
        fi
        ok "Checksum verified"
    fi

    info "Loading Docker images (this may take several minutes)..."
    docker load -i "$WORK_DIR/images.tar"
    ok "Images loaded"

    if [[ -f "$WORK_DIR/docker-compose.prod.yml" ]]; then
        cp "$WORK_DIR/docker-compose.prod.yml" "${INSTALL_DIR}/docker-compose.prod.yml"
    fi
    if [[ -f "$WORK_DIR/nginx.conf" ]]; then
        cp "$WORK_DIR/nginx.conf" "${INSTALL_DIR}/nginx.conf"
    fi

    sed -i "s/^WEBMACS_VERSION=.*/WEBMACS_VERSION=${VERSION}/" "$ENV_FILE"

elif [[ "$OFFLINE" == "true" ]]; then
    if [[ -f "${INSTALL_DIR}/docker-compose.prod.yml" ]]; then
        info "Offline mode: using existing ${INSTALL_DIR}/docker-compose.prod.yml (no network actions)"
    else
        err "Offline mode selected but ${INSTALL_DIR}/docker-compose.prod.yml not found. Provide a bundle or run without --offline."
    fi
elif [[ -f "${INSTALL_DIR}/docker-compose.prod.yml" ]]; then
    info "Pulling latest images from Docker Hub..."
    cd "${INSTALL_DIR}"
    if docker compose -f docker-compose.prod.yml --env-file .env pull; then
        ok "Images pulled from Docker Hub"
    else
        warn "docker compose pull failed — using existing local images"
    fi
else
    info "No bundle provided — downloading compose file and pulling images from Docker Hub..."

    GITHUB_BASE="${GITHUB_BASE:-https://raw.githubusercontent.com/stefanposs/webmacs/main}"
    mkdir -p "${INSTALL_DIR}"
    if curl -fsSL "${GITHUB_BASE}/docker-compose.prod.yml" -o "${INSTALL_DIR}/docker-compose.prod.yml" && \
       curl -fsSL "${GITHUB_BASE}/docker/nginx.conf" -o "${INSTALL_DIR}/nginx.conf"; then
        ok "Downloaded docker-compose.prod.yml + nginx.conf"
        info "Pulling images from Docker Hub (may take a while on first install)..."
        cd "${INSTALL_DIR}"
        if ! docker compose -f docker-compose.prod.yml --env-file .env pull; then
            err "Failed to pull images from Docker Hub. Check your internet connection."
        fi
        ok "Images pulled from Docker Hub"
    else
        err "Failed to download docker-compose.prod.yml.\nUsage: sudo $0 <path-to-webmacs-update-bundle.tar.gz>"
    fi
fi

if [[ ! -f "${INSTALL_DIR}/docker-compose.prod.yml" ]]; then
    err "docker-compose.prod.yml not found in ${INSTALL_DIR}/"
fi

# ── 11. Start WebMACS ───────────────────────────────────────────────────────
step "Starting WebMACS"

if [[ "$REBOOT_REQUIRED" == true ]]; then
    warn "Skipping container start — cgroup memory was just enabled and requires a reboot."
    warn "WebMACS will start automatically after you reboot (systemd service is enabled)."
else
    cd "${INSTALL_DIR}"
    docker compose -f docker-compose.prod.yml --env-file .env up -d

    # Wait for backend health
    info "Waiting for backend to become healthy (may take 2–3 min on first start)..."
    RETRIES=60
    for i in $(seq 1 $RETRIES); do
        if docker compose -f docker-compose.prod.yml exec -T backend \
            python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
            ok "Backend is healthy"
            break
        fi
        if [[ $i -eq $RETRIES ]]; then
            warn "Backend not yet healthy after $((RETRIES * 3)) s — check logs:"
            warn "  cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml logs backend"
        fi
        sleep 3
    done
fi

# ── 12. Systemd service ─────────────────────────────────────────────────────
step "Configuring auto-start"

SYSTEMD_FILE="/etc/systemd/system/webmacs.service"
if [[ ! -f "$SYSTEMD_FILE" ]]; then
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

# ── 13. Done ─────────────────────────────────────────────────────────────────
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "═══════════════════════════════════════════════════════"
echo ""
echo "   ✓ WebMACS installed successfully!"
echo ""
echo "   Open in browser:"
echo "      https://${IP_ADDR}"
echo ""
echo "   Credentials stored in: ${ENV_FILE}"
echo ""
echo "   Useful commands:"
echo "      Status:  cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml ps"
echo "      Logs:    cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml logs -f"
echo "      Restart: sudo systemctl restart webmacs"
echo "      Stop:    sudo systemctl stop webmacs"
echo "      Backup:  cd ${INSTALL_DIR} && docker compose -f docker-compose.prod.yml exec -T db \\"
echo "                 pg_dump -U webmacs webmacs > backup_\$(date +%Y%m%d).sql"
echo ""
echo "   To update WebMACS:"
echo "      Upload a .tar.gz bundle via the WebMACS UI (OTA Updates → Upload)"
echo ""
echo "═══════════════════════════════════════════════════════"

if [[ "$REBOOT_REQUIRED" == true ]]; then
    echo ""
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  ⚠  REBOOT REQUIRED                        │"
    echo "  │                                             │"
    echo "  │  cgroup memory was enabled in cmdline.txt.  │"
    echo "  │  WebMACS will start automatically after     │"
    echo "  │  reboot (systemd service is already set up).│"
    echo "  │                                             │"
    echo "  │  Run:  sudo reboot                          │"
    echo "  └─────────────────────────────────────────────┘"
    echo ""
fi
