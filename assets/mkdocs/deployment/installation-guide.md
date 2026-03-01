# Installation Guide

Step-by-step instructions for installing WebMACS on a Revolution Pi, Raspberry Pi, or any Debian/Ubuntu-based system.

---

## Prerequisites

| Requirement         | Revolution Pi / RPi 4/5     | Raspberry Pi 3              |
|---------------------|-----------------------------|-----------------------------||
| **OS**              | Debian 11+ / Raspberry Pi OS Bookworm (64-bit recommended) | Raspberry Pi OS Bullseye/Bookworm |
| **RAM**             | 2 GB+                       | 1 GB (750 MB minimum)       |
| **Storage**         | 8 GB free                   | 16 GB+ SD card or USB SSD   |
| **Network**         | Ethernet recommended        | Ethernet recommended        |

Docker and Docker Compose are installed automatically by the installation script if not already present.

---

## Choosing the Right Installer

| Hardware | Script | Notes |
|----------|--------|-------|
| **KUNBUS Revolution Pi** (Connect, Connect 4, Connect S) | `install-revpi.sh` | Industrial-grade, no cgroup patching needed |
| **Raspberry Pi 4 / Pi 5** | `install-rpi.sh` | Configures cgroup + swap automatically |
| **Raspberry Pi 3** (1 GB) | `install-rpi.sh` | Supported; 3 GB swap configured; startup takes ~3 min |
| **x86\_64 server / mini-PC** | `install-revpi.sh` | Works on any Debian/Ubuntu |

!!! tip "Not sure?"
    If you’re running standard Raspberry Pi OS on consumer hardware, use `install-rpi.sh`.
    For Revolution Pi or server deployments, use `install-revpi.sh`.

---

## Installation

### Option A — Revolution Pi: `scripts/install-revpi.sh` (Recommended)

For **KUNBUS Revolution Pi** and any Debian/Ubuntu server:

```bash
# Copy the bundle to the device (from your workstation)
scp webmacs-update-2.0.0.tar.gz pi@<device-ip>:/tmp/

# SSH into the device
ssh pi@<device-ip>

# Run the installer
sudo bash scripts/install-revpi.sh /tmp/webmacs-update-2.0.0.tar.gz
```

Or use the one-liner on a fresh device:

```bash
curl -sSL https://raw.githubusercontent.com/stefanposs/webmacs/main/scripts/install-revpi.sh | sudo bash
```

### Option A — Raspberry Pi 3/4/5: `scripts/install-rpi.sh`

For **consumer Raspberry Pi** hardware. Adds cgroup memory configuration, swap management,
and Docker daemon tuning on top of the base installer:

```bash
# Copy the bundle to the Pi
scp webmacs-update-2.0.0.tar.gz pi@<rpi-ip>:/tmp/

# SSH into the Pi
ssh pi@<rpi-ip>

# Run the RPi-specific installer
sudo bash scripts/install-rpi.sh /tmp/webmacs-update-2.0.0.tar.gz
```

One-liner:

```bash
curl -sSL https://raw.githubusercontent.com/stefanposs/webmacs/main/scripts/install-rpi.sh | sudo bash
```

!!! warning "Reboot may be required"
    On a fresh Raspberry Pi OS, the script patches `cmdline.txt` to enable cgroup memory.
    If patched, it will remind you to run `sudo reboot` before Docker works correctly.

!!! note "Raspberry Pi 3 (1 GB RAM)"
    Fully supported. The script automatically configures 3 GB swap to compensate for
    limited RAM. First startup takes approximately **3 minutes** while the database
    initialises. Subsequent starts are faster.

Both installers will:

1. Detect hardware and verify compatibility
2. Install Docker and Docker Compose (if missing)
3. Create the `/opt/webmacs` directory structure
4. Generate a secure `.env` with random passwords
5. Generate a self-signed TLS certificate (if none found)
6. Deploy `nginx.conf` for HTTPS termination
7. Load the Docker images from the bundle (SHA-256 verified)
8. Start all services (HTTPS on port 443)
9. Create a systemd service for automatic start on boot

!!! warning "Save Your Credentials"
    The admin password is displayed **only once** during installation.
    It is also stored in `/opt/webmacs/.env`.

!!! tip "Running Docker Commands Without sudo"
    The `.env` file is owned by `root:docker` (mode `640`). To run `docker compose`
    commands without `sudo`, add your user to the `docker` group:

    ```bash
    sudo usermod -aG docker $USER
    # Log out and back in for the change to take effect
    ```

    Alternatively, prefix all `docker compose` commands with `sudo`.

### Option B — Manual Install

If you prefer to set up components individually:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker && sudo systemctl start docker

# 2. Create directories
sudo mkdir -p /opt/webmacs/{updates,updates/applied,updates/backups,updates/failed,certs}

# 3. Copy the compose file, nginx config, and bundle
sudo cp docker-compose.prod.yml /opt/webmacs/
sudo cp nginx.conf /opt/webmacs/
sudo cp webmacs-update-*.tar.gz /opt/webmacs/

# 4. Extract and load images
cd /opt/webmacs
sudo tar -xzf webmacs-update-*.tar.gz
sudo docker load -i images.tar

# 5. Create .env (see Environment Variables page for all options)
sudo cp .env.example /opt/webmacs/.env
sudo nano /opt/webmacs/.env

# 6. Generate self-signed TLS certificate
sudo openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /opt/webmacs/certs/key.pem \
    -out /opt/webmacs/certs/cert.pem \
    -days 3650 -subj "/CN=webmacs.local/O=WebMACS/OU=Self-Signed"

# 7. Start
cd /opt/webmacs
sudo docker compose -f docker-compose.prod.yml --env-file .env up -d
```

### Option C — Docker Hub Pull (No Bundle Required)

If the device has internet access, you can pull images directly from Docker Hub — no bundle needed:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker && sudo systemctl start docker

# 2. Create directory
sudo mkdir -p /opt/webmacs
cd /opt/webmacs

# 3. Download the compose file and nginx config
sudo curl -fsSL \
  https://raw.githubusercontent.com/stefanposs/webmacs/main/docker-compose.prod.yml \
  -o docker-compose.prod.yml
sudo curl -fsSL \
  https://raw.githubusercontent.com/stefanposs/webmacs/main/docker/nginx.conf \
  -o nginx.conf

# 4. Create certs directory and generate self-signed TLS certificate
sudo mkdir -p /opt/webmacs/certs
sudo openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /opt/webmacs/certs/key.pem \
    -out /opt/webmacs/certs/cert.pem \
    -days 3650 -subj "/CN=webmacs.local/O=WebMACS/OU=Self-Signed"

# 5. Generate .env with secure credentials
sudo bash -c 'cat > .env' <<EOF
DB_PASSWORD=$(openssl rand -hex 16)
SECRET_KEY=$(openssl rand -hex 32)
ADMIN_PASSWORD=$(openssl rand -base64 12)
ADMIN_EMAIL=admin@webmacs.local
ADMIN_USERNAME=admin
WEBMACS_VERSION=latest
EOF

# 6. Show the generated admin password (save it!)
echo "Admin password: $(sudo grep ADMIN_PASSWORD /opt/webmacs/.env | cut -d= -f2)"

# 7. Pull images and start
sudo docker compose -f docker-compose.prod.yml --env-file .env pull
sudo docker compose -f docker-compose.prod.yml --env-file .env up -d
```

!!! tip "First pull takes a while"
    On a Raspberry Pi, the first `docker compose pull` can take 5–10 minutes
    depending on your internet connection. Subsequent pulls only download changed layers.

---

## First Login

1. Open a browser and navigate to `http://<device-ip>`
2. Log in with the admin credentials shown during installation
3. **Change the admin password** immediately under *Settings → Profile*

!!! tip "Finding the Device IP"
    Run `hostname -I` on the device to see its IP address.
    On a Revolution Pi connected via Ethernet, the IP is typically
    assigned by DHCP.

---

## Creating Additional Users

After your first login as admin:

1. Navigate to **Settings → Users**
2. Click **Add User**
3. Fill in email, username, and password
4. Assign the appropriate role (`admin` or `viewer`)

---

## Updating WebMACS

There are two ways to apply updates:

### Via Web UI (Recommended)

1. Go to **OTA Updates** in the sidebar
2. Click **Upload Bundle**
3. Select the `.tar.gz` update bundle
4. The system will verify the bundle integrity, back up the database, load new images, and restart automatically
5. The page will reload once the update is complete

### Via USB / SCP

1. Copy the update bundle to the device:
   ```bash
   scp webmacs-update-2.1.0.tar.gz pi@<device-ip>:/opt/webmacs/updates/
   ```
2. The built-in updater service will detect the bundle within 60 seconds
3. It will automatically verify, apply, and restart the stack

### Via Command Line

```bash
cd /opt/webmacs
sudo tar -xzf updates/webmacs-update-2.1.0.tar.gz -C /tmp/webmacs-update
sudo docker load -i /tmp/webmacs-update/images.tar
sudo sed -i "s/^WEBMACS_VERSION=.*/WEBMACS_VERSION=2.1.0/" .env
sudo docker compose -f docker-compose.prod.yml --env-file .env up -d
```

---

## Backup & Restore

### Create a Database Backup

```bash
cd /opt/webmacs
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U webmacs webmacs > backup-$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
cd /opt/webmacs
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U webmacs webmacs < backup-20250101.sql
```

!!! note
    The updater creates automatic backups before every update in
    `/opt/webmacs/updates/backups/`.

---

## Troubleshooting

### Services Won't Start

```bash
# Check service status
cd /opt/webmacs
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f backend

# Restart everything
sudo systemctl restart webmacs
```

### Cannot Access Web UI

1. Check that the backend is healthy:
   ```bash
   curl -s http://localhost:8000/health
   ```
2. Check that nginx/frontend is running:
   ```bash
   docker compose -f docker-compose.prod.yml ps frontend
   ```
3. Verify no firewall is blocking port 80:
   ```bash
   sudo ufw allow 80/tcp   # if ufw is active
   ```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Remove old Docker images
docker image prune -a

# Remove old update bundles
rm /opt/webmacs/updates/applied/*.tar.gz
```

### Forgot Admin Password

```bash
cd /opt/webmacs
cat .env | grep ADMIN_PASSWORD
```

If the password was changed via the UI and is no longer in `.env`, reset it:

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -c "
from webmacs_backend.security import hash_password
print(hash_password('NewPassword123!'))
" | xargs -I{} docker compose -f docker-compose.prod.yml exec -T db \
  psql -U webmacs webmacs -c "UPDATE users SET password_hash='{}' WHERE username='admin';"
```

---

## Uninstalling

```bash
cd /opt/webmacs
sudo docker compose -f docker-compose.prod.yml down -v
sudo systemctl disable webmacs
sudo rm /etc/systemd/system/webmacs.service
sudo systemctl daemon-reload
sudo rm -rf /opt/webmacs
```

!!! danger
    This removes all data including the database. Create a backup first.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────┐
│  Revolution Pi / Host                            │
│                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│   │ Frontend │  │ Backend  │  │  Controller  │  │
│   │ (nginx)  │  │ (FastAPI)│  │ (sensors)    │  │
│   │ :80      │  │ :8000    │  │              │  │
│   └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│        │              │               │          │
│        └──────┬───────┘               │          │
│               │                       │          │
│         ┌─────┴─────┐                 │          │
│         │ PostgreSQL│◀────────────────┘          │
│         │ :5432     │                            │
│         └───────────┘                            │
│                                                  │
│   ┌──────────┐                                   │
│   │ Updater  │  (monitors /opt/webmacs/updates/) │
│   └──────────┘                                   │
└──────────────────────────────────────────────────┘
```

All services run as Docker containers managed by Docker Compose. The systemd unit ensures they start automatically after a reboot.
