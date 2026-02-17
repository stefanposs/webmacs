# Security

WebMACS implements defence-in-depth from the transport layer down to individual plugin uploads.
This page documents every security control so operators can evaluate compliance and auditors can verify posture.

---

## Authentication

### JWT Bearer Tokens

All API endpoints (except `/health`) require a valid JWT token in the `Authorization: Bearer <token>` header.

| Property | Value |
|---|---|
| Algorithm | **HS256** (HMAC-SHA256) |
| TTL | **24 hours** (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`) |
| Claims | `sub` (user ID), `exp` (expiry), `iat` (issued at) |
| Library | `python-jose` |

```python
# Token creation (simplified)
payload = {"sub": str(user_id), "exp": now + timedelta(minutes=1440), "iat": now}
jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

### API Tokens

API tokens provide long-lived authentication for scripts and integrations. They use the `wm_` prefix and are stored as **SHA-256 hashes** — the plaintext is shown only once at creation.

| Property | Value |
|---|---|
| Format | `wm_` + 43 random URL-safe characters |
| Storage | SHA-256 hash in `api_tokens` table |
| Permissions | Inherits the role of the owning user |
| Expiry | Optional (set at creation) |

API tokens are accepted in the same `Authorization: Bearer` header as JWTs. The backend distinguishes them by the `wm_` prefix.

### Password Hashing

Passwords are hashed with **bcrypt** (auto-salted). The raw password is never stored or logged.

```python
bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
```

### Token Blacklisting (Logout)

When a user logs out, their token is added to the `blacklist_tokens` table. Every authentication check queries this table first.
A background task runs hourly to prune expired blacklist entries (tokens older than the JWT TTL).

### WebSocket Authentication

WebSocket connections use the same JWT token, passed as a query parameter:

```
ws://host/ws/controller/telemetry?token=<jwt>
```

The token is validated on the WebSocket handshake — no unauthenticated connections are possible.

### OIDC Single Sign-On

WebMACS supports **OpenID Connect (OIDC)** for enterprise Single Sign-On. The implementation includes multiple security controls:

| Control | Details |
|---|---|
| **PKCE S256** | Proof Key for Code Exchange prevents authorization code interception |
| **Signed state token** | CSRF protection via HMAC-signed JWT with 10-minute expiry |
| **One-time auth codes** | JWT tokens are never exposed in URLs; a short-lived (60 s) one-time code is used instead |
| **email_verified** | Rejects SSO logins where the IdP has not verified the user's email |
| **Admin linking refusal** | Auto-linking SSO accounts to existing admin users is blocked |
| **Username sanitization** | Only `[a-zA-Z0-9._-]` characters are allowed in auto-generated usernames |
| **TTL-based discovery cache** | OIDC discovery metadata is refreshed every hour |
| **Dedicated frontend URL** | Post-login redirect uses an explicit config setting (`OIDC_FRONTEND_URL`) |

For setup instructions, see the [SSO Guide](sso.md).

---

## Role-Based Access Control (RBAC)

WebMACS enforces a three-tier hierarchical role model:

| Role | Level | Access |
|---|---|---|
| **Viewer** | 1 | Read-only access to dashboards, events, experiments, datapoints, logs |
| **Operator** | 2 | Everything Viewer can do + create/edit experiments, events, datapoints |
| **Admin** | 3 | Full access including rules, webhooks, OTA, users, API tokens, plugins |

Access checks use the hierarchy: `admin (3) > operator (2) > viewer (1)`. An endpoint requiring operator access will also allow admin users.

API endpoints enforce roles via dependency injection — unauthorized requests receive `403 Forbidden`:

```json
{"detail": "Admin access required."}
```

For details on managing users and roles, see [Users & Auth](users.md).

---

## SECRET_KEY Validation

The `SECRET_KEY` environment variable signs all JWTs. WebMACS enforces minimum security:

| Environment | Behaviour |
|---|---|
| **Production** (`ENV=production`) | **Startup fails** if `SECRET_KEY` is empty or < 32 characters |
| **Development** | Logs a warning but allows startup |

Generate a strong key:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

---

## Rate Limiting

An in-memory ASGI middleware enforces per-IP request limits.

| Setting | Default |
|---|---|
| **Limit** | 300 requests per minute per IP |
| **Window** | 60 seconds (sliding) |
| **Response** | `429 Too Many Requests` (JSON body) |
| **Cleanup** | Stale IPs pruned every 60 s |

### Exempt Paths

These paths are **not** rate-limited:

| Path | Reason |
|---|---|
| `/ws/*` | WebSocket upgrade requests |
| `/health` | Health check probes |
| `/api/v1/ota/*` | Large firmware uploads |
| `POST /api/v1/datapoints` | High-frequency controller telemetry |

### Trusted Networks

Requests from Docker bridge / loopback networks (`172.16.0.0/12`, `10.0.0.0/8`, `192.168.0.0/16`, `127.0.0.0/8`) are exempt from rate limiting.

### Reverse Proxy Headers

The middleware respects `X-Forwarded-For` (first hop) and `X-Real-IP` to identify the true client behind nginx.

!!! warning "Single-Worker Assumption"
    Rate-limit state is in-memory (per process). For multi-worker deployments, use Redis-backed rate limiting instead.

---

## CORS

Cross-Origin Resource Sharing is configured via `CORS_ORIGINS`:

```python
# Default (development)
cors_origins = ["http://localhost:3000", "http://localhost:5173"]
```

In production, set `CORS_ORIGINS` to the actual frontend URL. All methods and headers are allowed for authenticated requests.

---

## Webhook HMAC Signatures

When a webhook has a `secret` configured, every delivery includes a cryptographic signature:

| Header | Value |
|---|---|
| `X-Webhook-Signature` | `HMAC-SHA256(secret, "{timestamp}.{payload}")` |
| `X-Webhook-Timestamp` | Unix timestamp (seconds) |

### Verification (Python)

```python
import hmac, hashlib

def verify_signature(payload: str, signature: str, timestamp: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.{payload}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Replay Protection

The timestamp is included in the signed message. Receivers should reject payloads where the timestamp is older than 5 minutes.

### Retry Policy

| Attempt | Delay |
|---|---|
| 1st retry | 2 s |
| 2nd retry | 4 s |
| 3rd retry | 8 s |
| After 3 failures | Marked as `dead_letter` |

---

## Plugin Upload Validation

Plugin packages (`.whl` files) are validated before installation:

| Check | Details |
|---|---|
| File format | Must be a valid Python wheel (`.whl`) |
| Size limit | Max **50 MB** per upload |
| Entry point | Must declare a `webmacs.plugins` entry point |
| Isolation | Installed via `pip install --no-deps` to prevent dependency conflicts |

!!! danger "Plugin Trust"
    Plugins execute arbitrary Python code in the controller process.
    Only install plugins from trusted sources.

---

## Network Architecture

```
┌─────────────┐     HTTPS (443)     ┌───────────┐
│   Browser   │ ───────────────────▶│   nginx   │
└─────────────┘                     │ (reverse  │
                                    │  proxy)   │
                                    └─────┬─────┘
                                          │ HTTP (8000)
                                    ┌─────▼─────┐
                                    │  Backend   │
                                    │ (FastAPI)  │
                                    └─────┬─────┘
                                          │ WebSocket
                                    ┌─────▼──────┐
                                    │ Controller  │
                                    │ (Python)    │
                                    └─────┬──────┘
                                          │ GPIO / Modbus
                                    ┌─────▼──────┐
                                    │  Hardware   │
                                    └────────────┘
```

### Air-Gapped Deployments

WebMACS is designed to run **without internet access**:

- All Docker images are bundled in OTA update packages
- No external CDN or telemetry calls
- Plugin wheels are uploaded manually
- GitHub access is optional (only for update checks)

---

## Security Checklist

Use this checklist before going to production:

- [ ] Set a strong `SECRET_KEY` (≥ 32 characters)
- [ ] Set `ENV=production`
- [ ] Change default admin password
- [ ] Configure `CORS_ORIGINS` to your frontend domain
- [ ] Enable HTTPS via nginx (see [Production Guide](../deployment/production.md))
- [ ] Set webhook secrets for all registered webhooks
- [ ] Review plugin sources before installation
- [ ] Configure firewall to restrict port access
- [ ] Set up database backups (see [Production Guide](../deployment/production.md))
- [ ] Configure OIDC SSO if using centralized identity (see [SSO Guide](sso.md))
- [ ] Set `OIDC_FRONTEND_URL` explicitly when using SSO
- [ ] Use API tokens instead of shared passwords for automation
- [ ] Assign the principle of least privilege — use `viewer` and `operator` roles

---

## Next Steps

- [Single Sign-On (OIDC)](sso.md) — configure SSO with your Identity Provider
- [Users & Auth](users.md) — roles, API tokens, user management
- [Environment Variables](../deployment/env-vars.md) — all configuration options
- [Production Deployment](../deployment/production.md) — HTTPS, backups, monitoring
- [Webhooks](webhooks.md) — setting up webhook integrations
- [Plugin Development](../development/plugin-development.md) — building trusted plugins
