#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# WebMACS — Raspberry Pi Installation Script
# Tested on: Raspberry Pi OS Lite (Bookworm / Bullseye), 64-bit and 32-bit
# Supported hardware: Raspberry Pi 3 (1 GB), Pi 4, Pi 5
# Minimum RAM: 750 MB (+ swap configured automatically)
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/stefanposs/webmacs/main/scripts/install-rpi.sh | sudo bash
#   — or —
#   sudo ./scripts/install-rpi.sh [update-bundle.tar.gz]
#
# What it does:
#   1. Verifies Raspberry Pi hardware
#   2. Enables cgroup memory (required for Docker)
#   3. Configures swap (if RAM < 4 GB)
#   4. Installs Docker + Docker Compose
#   5. Creates /opt/webmacs directory structure
#   6. Generates secure .env file
#   7. Loads images from bundle (if provided) or pulls from registry
#   8. Starts the WebMACS stack
#   9. Creates systemd service for auto-start on boot
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="/opt/webmacs"
BUNDLE_PATH="${1:-}"
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
echo "   WebMACS — Raspberry Pi Installer"
echo "   Web-based Monitoring and Control System"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Root check ────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    err "Run with sudo: sudo bash $0 $*"
fi

# ── 2. Raspberry Pi detection ────────────────────────────────────────────────
step "Checking hardware"

ARCH=$(uname -m)   # aarch64 | armv7l | armv6l

# Detect RPi model from /proc/device-tree/model or /sys/firmware/devicetree
RPI_MODEL=""
for model_file in /proc/device-tree/model /sys/firmware/devicetree/base/model; do
    if [[ -f "$model_file" ]]; then
        RPI_MODEL=$(tr -d '\0' < "$model_file" 2>/dev/null || true)
        break
    fi
done

if [[ -z "$RPI_MODEL" ]]; then
    # Fallback: check /proc/cpuinfo for Hardware field
    RPI_MODEL=$(grep -i "Model" /proc/cpuinfo 2>/dev/null | head -1 | cut -d':' -f2 | xargs || true)
fi

if [[ "$RPI_MODEL" == *"Raspberry Pi"* ]]; then
    ok "Detected: ${RPI_MODEL}"
else
    warn "Could not confirm Raspberry Pi hardware (model: '${RPI_MODEL:-unknown}')."
    warn "Continuing anyway — this script works on any Debian/Ubuntu ARM system."
fi

# Architecture check
case "$ARCH" in
    aarch64) ok "Architecture: 64-bit ARM (aarch64)" ;;
    armv7l)  ok "Architecture: 32-bit ARM (armv7l) — Raspberry Pi 3 supported" ;;
    armv6l)  warn "Architecture: ARMv6 (armv6l) — Raspberry Pi 1/Zero, too slow for WebMACS" ;;
    x86_64)  ok "Architecture: x86_64 (testing/dev mode)" ;;
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
        *) warn "Untested OS '${ID:-unknown}'. Proceeding, but Debian/Raspberry Pi OS is recommended." ;;
    esac
else
    warn "Cannot read /etc/os-release. Proceeding anyway."
fi

# ── 4. Memory check + swap ───────────────────────────────────────────────────
step "Checking memory"

TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_MB=$((TOTAL_RAM_KB / 1024))
TOTAL_RAM_GB=$((TOTAL_RAM_MB / 1024))

if [[ $TOTAL_RAM_MB -lt 750 ]]; then
    err "Only ${TOTAL_RAM_MB} MB RAM detected. WebMACS requires at least 750 MB."
elif [[ $TOTAL_RAM_MB -lt 1024 ]]; then
    warn "${TOTAL_RAM_MB} MB RAM — minimum met (Raspberry Pi 3), swap will be configured."
elif [[ $TOTAL_RAM_MB -lt 2048 ]]; then
    warn "${TOTAL_RAM_MB} MB RAM — sufficient, but 4 GB recommended for best performance."
else
    ok "${TOTAL_RAM_MB} MB RAM (≈ ${TOTAL_RAM_GB} GB)"
fi

# Configure swap if RAM < 4 GB (especially important for RPi 3 with 1 GB)
if [[ $TOTAL_RAM_MB -lt 4096 ]]; then
    SWAP_FILE="/var/swap"
    CURRENT_SWAP_KB=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    CURRENT_SWAP_MB=$((CURRENT_SWAP_KB / 1024))

    # < 1 GB RAM (e.g. RPi 3 ~900 MB) → 3 GB swap
    # 1–2 GB RAM                       → 2 GB swap
    # 2–4 GB RAM                       → 1 GB swap
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

# ── 5. cgroup memory (required for Docker on RPi) ────────────────────────────
step "Checking cgroup configuration"

# Raspberry Pi OS Bookworm uses /boot/firmware/cmdline.txt
# Older versions use /boot/cmdline.txt
CMDLINE_FILE=""
for f in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
    if [[ -f "$f" ]]; then
        CMDLINE_FILE="$f"
        break
    fi
done

if [[ -z "$CMDLINE_FILE" ]]; then
    warn "Could not find cmdline.txt — skipping cgroup check."
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
        # Append to the single line without adding a newline at end
        EXTRA=""
        echo "$CMDLINE" | grep -q "cgroup_memory=1"    || EXTRA="$EXTRA cgroup_memory=1"
        echo "$CMDLINE" | grep -q "cgroup_enable=memory" || EXTRA="$EXTRA cgroup_enable=memory"

        # Write back (strip trailing newline, append options, add newline)
        printf '%s%s\n' "$(cat "$CMDLINE_FILE" | tr -d '\n')" "$EXTRA" > "$CMDLINE_FILE"
        ok "cgroup memory enabled in ${CMDLINE_FILE}"
        REBOOT_REQUIRED=true
    else
        ok "cgroup memory already enabled"
    fi
fi

# ── 6. Install Docker ────────────────────────────────────────────────────────
step "Installing Docker"

if ! command -v docker &>/dev/null; then
    info "Installing Docker via get.docker.com..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    ok "Docker installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
else
    ok "Docker already installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
fi

# Docker Compose plugin
if ! docker compose version &>/dev/null; then
    info "Installing Docker Compose plugin..."
    apt-get update -qq
    apt-get install -y -qq docker-compose-plugin
    ok "Docker Compose plugin installed"
else
    ok "Docker Compose available ($(docker compose version --short))"
fi

# Configure Docker storage driver for RPi (overlay2 + journald logging)
DOCKER_DAEMON_FILE="/etc/docker/daemon.json"
if [[ ! -f "$DOCKER_DAEMON_FILE" ]]; then
    info "Configuring Docker daemon for Raspberry Pi..."
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

# Verify Docker daemon is responsive (some systems need a moment to start)
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

    # Give it more time
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

# ── 7. Create directory structure ───────────────────────────────────────────
step "Creating directory structure"

mkdir -p "${INSTALL_DIR}"/{updates,updates/applied,updates/backups,updates/failed,plugins}
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

    chmod 600 "$ENV_FILE"
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

# ── 9. Load images from bundle or pull ──────────────────────────────────────
step "Loading Docker images"

if [[ -n "$BUNDLE_PATH" && -f "$BUNDLE_PATH" ]]; then
    info "Loading from bundle: ${BUNDLE_PATH}..."

    WORK_DIR=$(mktemp -d)
    trap 'rm -rf "$WORK_DIR"' EXIT

    tar -xzf "$BUNDLE_PATH" -C "$WORK_DIR"

    if [[ ! -f "$WORK_DIR/manifest.json" ]]; then
        err "Invalid bundle: manifest.json not found"
    fi

    VERSION=$(python3 -c "import json; print(json.load(open('$WORK_DIR/manifest.json'))['version'])" 2>/dev/null || echo "unknown")
    info "Bundle version: ${VERSION}"

    # Checksum verification
    EXPECTED_SHA=$(python3 -c "import json; print(json.load(open('$WORK_DIR/manifest.json'))['images_sha256'])" 2>/dev/null || echo "")
    if [[ -n "$EXPECTED_SHA" ]]; then
        info "Verifying checksum..."
        ACTUAL_SHA=$(sha256sum "$WORK_DIR/images.tar" | cut -d' ' -f1)
        if [[ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]]; then
            err "Checksum mismatch! Bundle may be corrupted."
        fi
        ok "Checksum verified"
    fi

    info "Loading Docker images (may take several minutes on Raspberry Pi)..."
    docker load -i "$WORK_DIR/images.tar"
    ok "Images loaded"

    if [[ -f "$WORK_DIR/docker-compose.prod.yml" ]]; then
        cp "$WORK_DIR/docker-compose.prod.yml" "${INSTALL_DIR}/docker-compose.prod.yml"
    fi

    sed -i "s/^WEBMACS_VERSION=.*/WEBMACS_VERSION=${VERSION}/" "$ENV_FILE"

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

    GITHUB_RAW_URL="${GITHUB_RAW_URL:-https://raw.githubusercontent.com/stefanposs/webmacs/main/docker-compose.prod.yml}"
    mkdir -p "${INSTALL_DIR}"
    if curl -fsSL "$GITHUB_RAW_URL" -o "${INSTALL_DIR}/docker-compose.prod.yml"; then
        ok "Downloaded docker-compose.prod.yml"
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

# ── 10. Start WebMACS ───────────────────────────────────────────────────────
step "Starting WebMACS"

if [[ "$REBOOT_REQUIRED" == true ]]; then
    warn "Skipping container start — cgroup memory was just enabled and requires a reboot."
    warn "WebMACS will start automatically after you reboot (systemd service is enabled)."
else
    cd "${INSTALL_DIR}"
    docker compose -f docker-compose.prod.yml --env-file .env up -d

    # Wait for backend health
    # RPi 3 is significantly slower on first start (DB init, migrations)
    info "Waiting for backend to become healthy (may take up to 3 min on RPi 3)..."
    RETRIES=60
    for i in $(seq 1 $RETRIES); do
        if docker compose -f docker-compose.prod.yml exec -T backend \
            python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
            ok "Backend is healthy"
            break
        fi
        if [[ $i -eq $RETRIES ]]; then
            warn "Backend not yet healthy after $((RETRIES * 3)) s — check logs:"
            warn "  docker compose -f docker-compose.prod.yml logs backend"
        fi
        sleep 3
    done
fi

# ── 11. Systemd service ─────────────────────────────────────────────────────
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

# ── 12. Done ────────────────────────────────────────────────────────────────
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "═══════════════════════════════════════════════════════"
echo ""
echo "   ✓ WebMACS installed successfully!"
echo ""
echo "   Open in browser:"
echo "      http://${IP_ADDR}"
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
