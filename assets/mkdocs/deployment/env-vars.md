# Environment Variables

Complete reference of all environment variables used by WebMACS.

---

## Backend

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...localhost...` | SQLAlchemy async connection string |
| `SECRET_KEY` | **Yes** | *(empty)* | JWT signing secret — **must set in production** |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | Token lifetime (minutes) |
| `BACKEND_HOST` | No | `0.0.0.0` | Uvicorn bind host |
| `BACKEND_PORT` | No | `8000` | Uvicorn bind port |
| `CORS_ORIGINS` | No | `["http://localhost:3000","http://localhost:5173"]` | JSON array of allowed origins |
| `DEBUG` | No | `false` | Enable debug mode |
| `STORAGE_BACKEND` | No | `postgresql` | `postgresql` or `timescale` |
| `SENTRY_DSN` | No | *(empty)* | Sentry error tracking URL |
| `WS_HEARTBEAT_INTERVAL` | No | `30` | WebSocket heartbeat (seconds) |
| `TIMEZONE` | No | `Europe/Berlin` | Default timezone |
| `INITIAL_ADMIN_EMAIL` | No | `admin@webmacs.io` | Seed admin email |
| `INITIAL_ADMIN_USERNAME` | No | `admin` | Seed admin username |
| `INITIAL_ADMIN_PASSWORD` | No | `admin123` | Seed admin password |

---

## OIDC / SSO

| Variable | Required | Default | Description |
|---|---|---|---|
| `OIDC_ENABLED` | No | `false` | Enable OIDC Single Sign-On |
| `OIDC_PROVIDER_NAME` | No | `SSO` | Display name on the login button |
| `OIDC_ISSUER_URL` | If SSO | *(empty)* | IdP issuer URL (e.g. `https://auth.example.com/realms/webmacs`) |
| `OIDC_CLIENT_ID` | If SSO | *(empty)* | OAuth2 Client ID |
| `OIDC_CLIENT_SECRET` | If SSO | *(empty)* | OAuth2 Client Secret |
| `OIDC_SCOPES` | No | `openid email profile` | Space-separated OIDC scopes |
| `OIDC_REDIRECT_URI` | If SSO | *(empty)* | Callback URL (`https://<domain>/api/v1/auth/sso/callback`) |
| `OIDC_DEFAULT_ROLE` | No | `viewer` | Role for auto-created SSO users (`admin`, `operator`, `viewer`) |
| `OIDC_AUTO_CREATE_USERS` | No | `true` | Auto-create local user on first SSO login |
| `OIDC_FRONTEND_URL` | No | *(empty)* | Frontend URL for post-login redirect |

---

## Controller

| Variable | Required | Default | Description |
|---|---|---|---|
| `WEBMACS_ENV` | No | `development` | `development` or `production` |
| `WEBMACS_SERVER_URL` | Yes | `http://localhost` | Backend base URL |
| `WEBMACS_SERVER_PORT` | Yes | `8000` | Backend port |
| `WEBMACS_ADMIN_EMAIL` | Yes | — | Login credentials for controller |
| `WEBMACS_ADMIN_PASSWORD` | Yes | — | Login password |
| `WEBMACS_POLL_INTERVAL` | No | `1.0` | Sensor read interval in seconds (min `0.2`) |
| `WEBMACS_REQUEST_TIMEOUT` | No | `30.0` | HTTP timeout (seconds) |
| `WEBMACS_MAX_BATCH_SIZE` | No | `100` | Max datapoints per telemetry payload (1–500) |
| `WEBMACS_DEDUP_ENABLED` | No | `false` | Drop unchanged sensor values to reduce I/O |
| `WEBMACS_TELEMETRY_MODE` | No | `http` | `http` or `websocket` |
| `WEBMACS_RULE_EVENT_ID` | No | *(empty)* | Event triggering rule evaluation |
| `WEBMACS_AUTO_SEED` | No | `true` | Auto-register simulated plugin in dev mode |
| `WEBMACS_PLUGIN_SYNC_INTERVAL` | No | `10.0` | Plugin re-sync interval (seconds) |
| `WEBMACS_REVPI_MAPPING` | No | `{}` | JSON: RevPi I/O pin → event ID |

---

## Docker Compose

These are used in `docker-compose.yml` and passed through to services:

| Variable | Default | Used By |
|---|---|---|
| `DB_PASSWORD` | `webmacs_dev_password` | db, backend |
| `SECRET_KEY` | `change-me-in-production` | backend |
| `ADMIN_EMAIL` | `admin@webmacs.io` | backend, controller |
| `ADMIN_USERNAME` | `admin` | backend |
| `ADMIN_PASSWORD` | `admin123` | backend, controller |
| `TELEMETRY_MODE` | `http` | controller |

---

## Generating Secrets

```bash
# Secret key (64 hex chars)
openssl rand -hex 32

# Database password
openssl rand -base64 24

# Admin password
openssl rand -base64 16
```

---

## Example `.env`

```dotenv
# Database
DATABASE_URL=postgresql+asyncpg://webmacs:MyStr0ngPwd!@db:5432/webmacs
DB_PASSWORD=MyStr0ngPwd!

# Security
SECRET_KEY=a1b2c3d4e5f6...64chars
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Admin
ADMIN_EMAIL=admin@company.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Ch4ng3M3!

# Controller
TELEMETRY_MODE=websocket

# SSO (optional)
OIDC_ENABLED=true
OIDC_PROVIDER_NAME=Company SSO
OIDC_ISSUER_URL=https://auth.example.com/realms/webmacs
OIDC_CLIENT_ID=webmacs-client
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://webmacs.example.com/api/v1/auth/sso/callback
OIDC_DEFAULT_ROLE=operator
OIDC_FRONTEND_URL=https://webmacs.example.com
```

---

## Next Steps

- [Docker Setup](docker.md) — container configuration
- [Production Guide](production.md) — hardening checklist
