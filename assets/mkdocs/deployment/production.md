# Production Deployment

This guide covers hardening WebMACS for production environments.

---

## Security Checklist

- [ ] Generate a strong `SECRET_KEY` (`openssl rand -hex 32`)
- [ ] Change default admin password
- [ ] Set `DEBUG=false`
- [ ] Use a strong `DB_PASSWORD`
- [ ] Restrict `CORS_ORIGINS` to your domain
- [ ] Enable HTTPS (TLS termination at load balancer or Nginx)
- [ ] Configure Sentry for error tracking (`SENTRY_DSN`)

---

## Environment File

Create a production `.env`:

```dotenv
# Security
SECRET_KEY=<generated-64-char-hex>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DATABASE_URL=postgresql+asyncpg://webmacs:<strong-password>@db:5432/webmacs
DB_PASSWORD=<strong-password>

# Admin
INITIAL_ADMIN_EMAIL=admin@yourcompany.com
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=<strong-password>

# Backend
CORS_ORIGINS=["https://webmacs.yourcompany.com"]
DEBUG=false
WEBMACS_ENV=production

# Controller
WEBMACS_TELEMETRY_MODE=websocket
```

---

## HTTPS / TLS

WebMACS ships with **built-in SSL/TLS termination** at the Nginx reverse proxy.
All traffic on port 80 is automatically redirected to HTTPS (443).

### How It Works

```
Browser ──── HTTPS (443) ────▶ Nginx ──── HTTP (8000) ────▶ Backend
         ◀── 301 redirect ──── :80                         (internal)
```

- **TLS 1.2 / TLS 1.3** only — older protocols are disabled
- **HSTS** header (`max-age=63072000`) prevents downgrade attacks
- **HTTP/2** enabled for faster page loads
- WebSocket connections automatically use **WSS** (encrypted)
- Internal Docker networking stays plain HTTP (no overhead)

### Deployment Files

The SSL setup uses files deployed to `/opt/webmacs/`:

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Orchestrates all services; mounts `nginx.conf` and certs into the frontend container |
| `nginx.conf` | Nginx reverse proxy config with SSL termination (bind-mounted at runtime) |
| `certs/cert.pem` | TLS certificate |
| `certs/key.pem` | TLS private key |

!!! info "Why a bind-mounted nginx.conf?"
    The `nginx.conf` is mounted from the host filesystem rather than baked into the Docker image.
    This means HTTPS works regardless of which image version is running — no need to rebuild
    or pull new images after enabling SSL.

### Certificate Setup

Certificates must be placed in `/opt/webmacs/certs/`:

| File | Description |
|------|-------------|
| `cert.pem` | TLS certificate (or full chain) |
| `key.pem` | Private key |

#### Option 1: Self-Signed (Generated Automatically)

The install scripts (`install.sh`, `install-revpi.sh`, `install-rpi.sh`) auto-generate a
self-signed certificate if none is found. Valid for 10 years.

!!! warning "Browser Warning"
    Self-signed certificates trigger a browser warning. This is expected —
    click "Advanced → Proceed" to continue. For trusted access, use your own certificate.

#### Option 2: Bring Your Own Certificate

Replace the self-signed certificate with your own:

```bash
# Copy your certificate files
sudo cp your-cert.pem /opt/webmacs/certs/cert.pem
sudo cp your-key.pem  /opt/webmacs/certs/key.pem
sudo chmod 644 /opt/webmacs/certs/cert.pem
sudo chmod 600 /opt/webmacs/certs/key.pem

# Restart to pick up the new certificate
sudo systemctl restart webmacs
```

!!! tip "Certificate Formats"
    The certificate file should be PEM-encoded. If your CA provides a chain,
    concatenate it: `cat your-cert.pem intermediate.pem > /opt/webmacs/certs/cert.pem`

#### Option 3: Let's Encrypt (Public-Facing Servers)

For internet-facing deployments, use Certbot to obtain a free trusted certificate:

```bash
sudo apt install certbot
sudo certbot certonly --standalone -d webmacs.example.com

# Copy to WebMACS certs directory
sudo cp /etc/letsencrypt/live/webmacs.example.com/fullchain.pem /opt/webmacs/certs/cert.pem
sudo cp /etc/letsencrypt/live/webmacs.example.com/privkey.pem   /opt/webmacs/certs/key.pem

# Set up auto-renewal cron
echo "0 3 * * * certbot renew --quiet --deploy-hook 'cd /opt/webmacs && docker compose -f docker-compose.prod.yml restart frontend'" | sudo crontab -
```

### CORS Configuration

Update `CORS_ORIGINS` in your `.env` or `docker-compose.prod.yml` to use `https://`:

```dotenv
CORS_ORIGINS=["https://webmacs.yourcompany.com"]
```

### Upgrading Existing Installations

If you're upgrading an existing HTTP-only installation:

```bash
cd /opt/webmacs

# 1. Download updated compose file and nginx config
sudo curl -fsSL \
  https://raw.githubusercontent.com/stefanposs/webmacs/main/docker-compose.prod.yml \
  -o docker-compose.prod.yml
sudo curl -fsSL \
  https://raw.githubusercontent.com/stefanposs/webmacs/main/docker/nginx.conf \
  -o nginx.conf

# 2. Create certs directory and generate self-signed cert
sudo mkdir -p /opt/webmacs/certs
sudo openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout /opt/webmacs/certs/key.pem \
    -out /opt/webmacs/certs/cert.pem \
    -days 3650 \
    -subj "/CN=webmacs.local/O=WebMACS/OU=Self-Signed"
sudo chmod 600 /opt/webmacs/certs/key.pem

# 3. Update CORS_ORIGINS from http:// to https:// in .env (if set)
# 4. Restart
sudo docker compose -f docker-compose.prod.yml --env-file .env up -d
```

!!! info "How it works"
    The `nginx.conf` file is bind-mounted into the frontend container at runtime.
    This means SSL works regardless of which Docker image version you're running —
    no need to rebuild or pull new images.

---

## Database Backups

### Automated Dump

```bash
docker compose exec db pg_dump -U webmacs webmacs > backup_$(date +%Y%m%d).sql
```

### Restore

```bash
cat backup_20250115.sql | docker compose exec -T db psql -U webmacs webmacs
```

### Scheduled Backups

Add a cron job:

```cron
0 2 * * * cd /path/to/webmacs && docker compose exec -T db pg_dump -U webmacs webmacs | gzip > /backups/webmacs_$(date +\%Y\%m\%d).sql.gz
```

---

## Monitoring

### Health Endpoints

| Endpoint | Service | Purpose |
|---|---|---|
| `GET /health` | Backend | Application health |
| `pg_isready` | PostgreSQL | Database connectivity |

### Sentry Integration

Set `SENTRY_DSN` to enable error tracking:

```dotenv
SENTRY_DSN=https://abc123@sentry.io/12345
```

### Logging

The backend uses **structlog** for structured JSON logging. In production, pipe logs to your log aggregator (ELK, Loki, CloudWatch).

---

## Scaling Considerations

| Component | Scaling | Notes |
|---|---|---|
| Backend | Horizontal | Run multiple replicas behind a load balancer |
| Frontend | CDN | Serve static files from a CDN |
| Controller | Single | One controller per physical installation |
| Database | Vertical / Read replicas | Consider TimescaleDB for time-series |

---

## Next Steps

- [Docker Setup](docker.md) — container configuration
- [Environment Variables](env-vars.md) — full reference
