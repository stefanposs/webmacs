# Configuration

WebMACS is configured entirely through **environment variables**. Copy `.env.example` to `.env` and customise as needed.

---

## Backend Settings

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://webmacs:webmacs@localhost:5432/webmacs` | Async SQLAlchemy connection string |
| `SECRET_KEY` | *(empty — must set)* | JWT signing key. Generate with `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT token lifetime (default 24 h) |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `BACKEND_HOST` | `0.0.0.0` | Uvicorn bind address |
| `BACKEND_PORT` | `8000` | Uvicorn port |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `DEBUG` | `false` | Enable debug mode |
| `STORAGE_BACKEND` | `postgresql` | Database backend: `postgresql` or `timescale` |
| `SENTRY_DSN` | *(empty)* | Optional Sentry error tracking |
| `WS_HEARTBEAT_INTERVAL` | `30` | WebSocket heartbeat interval (seconds) |
| `TIMEZONE` | `Europe/Berlin` | Default timezone for timestamps |

### Initial Admin User

| Variable | Default | Description |
|---|---|---|
| `INITIAL_ADMIN_EMAIL` | `admin@webmacs.io` | Email for the auto-seeded admin |
| `INITIAL_ADMIN_USERNAME` | `admin` | Username |
| `INITIAL_ADMIN_PASSWORD` | `admin123` | Password — **change in production!** |

---

## Controller Settings

| Variable | Default | Description |
|---|---|---|
| `WEBMACS_ENV` | `development` | Environment (`development` / `production`) |
| `WEBMACS_SERVER_URL` | `http://localhost` | Backend base URL |
| `WEBMACS_SERVER_PORT` | `8000` | Backend port |
| `WEBMACS_ADMIN_EMAIL` | `admin@example.com` | Credentials for controller ↔ backend auth |
| `WEBMACS_ADMIN_PASSWORD` | *(set in .env)* | Password for auto-login |
| `WEBMACS_POLL_INTERVAL` | `1.0` | Sensor polling interval in seconds (min `0.2`, see [Fast Mode](hardware-sizing.md#fast-mode-sub-second-polling)) |
| `WEBMACS_REQUEST_TIMEOUT` | `30.0` | HTTP request timeout |
| `WEBMACS_MAX_BATCH_SIZE` | `100` | Max datapoints per telemetry payload (1–500) |
| `WEBMACS_DEDUP_ENABLED` | `false` | Drop unchanged sensor values to reduce write I/O |
| `WEBMACS_TELEMETRY_MODE` | `http` | `http` or `websocket` |
| `WEBMACS_RULE_EVENT_ID` | *(empty)* | Event public_id triggering rule evaluation |
| `WEBMACS_AUTO_SEED` | `true` | Auto-register simulated plugin in dev mode |
| `WEBMACS_PLUGIN_SYNC_INTERVAL` | `10.0` | Plugin re-sync interval (seconds) |
| `WEBMACS_REVPI_MAPPING` | `{}` | JSON mapping of RevPi I/O pins to event ids |

---

## Docker Compose Variables

These are used by `docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| `DB_PASSWORD` | `webmacs_dev_password` | PostgreSQL password |
| `ADMIN_EMAIL` | `admin@webmacs.io` | Passed to backend + controller |
| `ADMIN_USERNAME` | `admin` | Admin username |
| `ADMIN_PASSWORD` | `admin123` | Admin password |
| `TELEMETRY_MODE` | `http` | Controller telemetry transport |

---

## Generating a Secret Key

```bash
openssl rand -hex 32
```

Copy the output into `SECRET_KEY` in your `.env` file.

---

## Next Steps

- [Docker Deployment](../deployment/docker.md) — production Docker setup
- [Environment Variables Reference](../deployment/env-vars.md) — full reference
