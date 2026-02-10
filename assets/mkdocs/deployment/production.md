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

### Option 1: Reverse Proxy (Recommended)

Place a TLS-terminating reverse proxy (Traefik, Caddy, cloud LB) in front of the Nginx container.

### Option 2: Nginx with Certbot

Add SSL configuration to `docker/nginx.conf`:

```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/webmacs.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/webmacs.example.com/privkey.pem;

    # ... existing location blocks
}
```

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
