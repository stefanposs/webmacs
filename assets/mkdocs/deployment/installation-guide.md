# Installation Guide

Step-by-step instructions for installing WebMACS on a Revolution Pi or any Debian/Ubuntu-based system.

---

## Prerequisites

| Requirement         | Minimum                        |
|---------------------|--------------------------------|
| **Hardware**        | Kunbus Revolution Pi, Raspberry Pi 4, or x86_64 server |
| **OS**              | Debian 11+ / Ubuntu 22.04+ (64-bit recommended) |
| **RAM**             | 2 GB                           |
| **Storage**         | 8 GB free                      |
| **Network**         | Ethernet (for sensor I/O and web access) |

Docker and Docker Compose are installed automatically by the installation script if not already present.

---

## Installation

### Option A — Automated Install (Recommended)

You will receive a **WebMACS update bundle** (`.tar.gz` file) from your system integrator. Copy it to the device via USB stick or SCP.

```bash
# Copy the bundle to the device (from your workstation)
scp webmacs-update-2.0.0.tar.gz pi@<device-ip>:/tmp/

# SSH into the device
ssh pi@<device-ip>

# Run the installer
sudo bash /tmp/install.sh /tmp/webmacs-update-2.0.0.tar.gz
```

The installer will:

1. Install Docker and Docker Compose (if missing)
2. Create the `/opt/webmacs` directory structure
3. Generate a secure `.env` with random passwords
4. Load the Docker images from the bundle
5. Start all services
6. Create a systemd service for automatic start on boot

!!! warning "Save Your Credentials"
    The admin password is displayed **only once** during installation.
    It is also stored in `/opt/webmacs/.env`.

### Option B — Manual Install

If you prefer to set up components individually:

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker && sudo systemctl start docker

# 2. Create directories
sudo mkdir -p /opt/webmacs/{updates,updates/applied,updates/backups,updates/failed}

# 3. Copy the compose file and bundle
sudo cp docker-compose.prod.yml /opt/webmacs/
sudo cp webmacs-update-*.tar.gz /opt/webmacs/

# 4. Extract and load images
cd /opt/webmacs
sudo tar -xzf webmacs-update-*.tar.gz
sudo docker load -i images.tar

# 5. Create .env (see Environment Variables page for all options)
sudo cp .env.example /opt/webmacs/.env
sudo nano /opt/webmacs/.env

# 6. Start
cd /opt/webmacs
sudo docker compose -f docker-compose.prod.yml --env-file .env up -d
```

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
from webmacs_backend.security import get_password_hash
print(get_password_hash('NewPassword123!'))
" | xargs -I{} docker compose -f docker-compose.prod.yml exec -T db \
  psql -U webmacs webmacs -c "UPDATE users SET hashed_password='{}' WHERE username='admin';"
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
