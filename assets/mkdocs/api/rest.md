# REST API Reference

All endpoints are mounted under `/api/v1/`. Authentication uses JWT Bearer tokens unless noted otherwise.

---

## Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Public | Authenticate and receive JWT |
| `POST` | `/api/v1/auth/logout` | JWT | Revoke current token |
| `GET` | `/api/v1/auth/me` | JWT | Get current user info |

### `POST /api/v1/auth/login`

Authenticate and receive a JWT token.

**Request:**

```json
{
  "email": "admin@webmacs.io",
  "password": "admin123"
}
```

**Response** `200`:

```json
{
  "status": "success",
  "message": "Successfully logged in.",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "public_id": "usr_abc123",
  "username": "admin"
}
```

!!! note "Token usage"
    Include the token in all subsequent requests:
    `Authorization: Bearer <access_token>`

### `POST /api/v1/auth/logout`

Blacklists the current JWT so it cannot be reused.

**Response** `200`:

```json
{ "status": "success", "message": "Successfully logged out." }
```

### `GET /api/v1/auth/me`

Returns the authenticated user's profile.

**Response** `200`:

```json
{
  "public_id": "usr_abc123",
  "email": "admin@webmacs.io",
  "username": "admin",
  "admin": true,
  "created_on": "2025-01-01T00:00:00"
}
```

---

## Users

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/users` | Admin | List all users |
| `GET` | `/api/v1/users/{id}` | Admin | Get user by public_id |
| `POST` | `/api/v1/users` | Admin | Create user |
| `PUT` | `/api/v1/users/{id}` | Admin | Update user |
| `DELETE` | `/api/v1/users/{id}` | Admin | Delete user |

### Create User

```json
{
  "email": "operator@example.com",
  "username": "operator1",
  "password": "securepassword123"
}
```

---

## Experiments

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/experiments` | JWT | List all experiments |
| `GET` | `/api/v1/experiments/{id}` | JWT | Get single experiment |
| `POST` | `/api/v1/experiments` | JWT | Create & start experiment |
| `PUT` | `/api/v1/experiments/{id}` | JWT | Update experiment |
| `PUT` | `/api/v1/experiments/{id}/stop` | JWT | Stop experiment |
| `DELETE` | `/api/v1/experiments/{id}` | JWT | Delete experiment |
| `GET` | `/api/v1/experiments/{id}/export/csv` | JWT | Download CSV |

### Create Experiment

```json
{
  "name": "Fluidised Bed Run 07"
}
```

### CSV Export

```bash
GET /api/v1/experiments/{id}/export/csv
```

Returns `text/csv` as a streaming response. See [CSV Export Guide](../guide/csv-export.md).

---

## Events

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/events` | JWT | List all events |
| `GET` | `/api/v1/events/{id}` | JWT | Get single event |
| `POST` | `/api/v1/events` | JWT | Create event |
| `PUT` | `/api/v1/events/{id}` | JWT | Update event |
| `DELETE` | `/api/v1/events/{id}` | JWT | Delete event |

### Create Event

```json
{
  "name": "Inlet Temperature",
  "type": "sensor",
  "unit": "°C",
  "min_value": 0.0,
  "max_value": 200.0
}
```

**Event Types:** `sensor`, `actuator`, `range`, `cmd_button`, `cmd_opened`, `cmd_closed`

---

## Dashboards

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/dashboards` | JWT | List dashboards (own + global) |
| `POST` | `/api/v1/dashboards` | JWT | Create dashboard |
| `GET` | `/api/v1/dashboards/{id}` | JWT | Get dashboard with widgets |
| `PUT` | `/api/v1/dashboards/{id}` | JWT | Update dashboard |
| `DELETE` | `/api/v1/dashboards/{id}` | JWT | Delete dashboard |
| `POST` | `/api/v1/dashboards/{id}/widgets` | JWT | Add widget to dashboard |
| `PUT` | `/api/v1/dashboards/{id}/widgets/{wid}` | JWT | Update widget |
| `DELETE` | `/api/v1/dashboards/{id}/widgets/{wid}` | JWT | Delete widget |

### Create Dashboard

```json
{
  "name": "Production Overview",
  "is_global": false
}
```

### Add Widget

```json
{
  "widget_type": "line_chart",
  "title": "Inlet Temperature",
  "event_public_id": "evt_temp01",
  "x": 0,
  "y": 0,
  "w": 6,
  "h": 3
}
```

**Widget Types:** `line_chart`, `gauge`, `stat_card`, `actuator_toggle`

!!! info "Visibility"
    Users see their own dashboards plus any dashboard marked `is_global: true`.
    Only the dashboard owner can modify or delete it.

---

## Datapoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/datapoints` | JWT | List datapoints (paginated) |
| `POST` | `/api/v1/datapoints` | JWT | Create single datapoint |
| `POST` | `/api/v1/datapoints/batch` | JWT | Create multiple datapoints |
| `POST` | `/api/v1/datapoints/series` | JWT | Get time-series data (for charts) |
| `GET` | `/api/v1/datapoints/latest` | JWT | Get latest datapoint per event |
| `GET` | `/api/v1/datapoints/{id}` | JWT | Get single datapoint |
| `DELETE` | `/api/v1/datapoints/{id}` | JWT | Delete datapoint |

### Create Datapoint

```json
{
  "value": 23.45,
  "event_public_id": "evt_temp01"
}
```

### Query Parameters

| Param | Type | Default | Description |
|---|---|---|---|
| `page` | `int` | `1` | Page number (≥ 1) |
| `page_size` | `int` | `25` | Results per page (1–100) |

### Time-Series Query

`POST /api/v1/datapoints/series` — returns datapoints grouped by event, with server-side downsampling for dashboard performance.

```json
{
  "event_public_ids": ["evt_temp01", "evt_pressure"],
  "minutes": 60,
  "max_points": 500
}
```

| Param | Type | Default | Range | Description |
|---|---|---|---|---|
| `event_public_ids` | `list[str]` | — | 1–20 | Events to query |
| `minutes` | `int` | `60` | 1–14400 | Time window (up to 10 days) |
| `max_points` | `int` | `500` | 10–2000 | Max points per event (downsampled) |

**Response:** `{ "evt_temp01": [...], "evt_pressure": [...] }`

!!! tip "Performance"
    Use `max_points` to limit data transferred to the frontend — the server uniformly samples large datasets while always preserving the latest value.

---

## Logs

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/logging` | JWT | List log entries |
| `POST` | `/api/v1/logging` | JWT | Create log entry |
| `PUT` | `/api/v1/logging/{id}` | JWT | Update (mark read) |

### Create Log Entry

```json
{
  "content": "Experiment started",
  "logging_type": "info"
}
```

**Log types:** `error`, `warning`, `info`
**Statuses:** `read`, `unread`

---

## Webhooks

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/webhooks` | Admin | List webhook subscriptions |
| `POST` | `/api/v1/webhooks` | Admin | Create webhook |
| `GET` | `/api/v1/webhooks/{id}` | Admin | Get webhook details |
| `PUT` | `/api/v1/webhooks/{id}` | Admin | Update webhook |
| `DELETE` | `/api/v1/webhooks/{id}` | Admin | Delete webhook |
| `GET` | `/api/v1/webhooks/{id}/deliveries` | Admin | List delivery log |

### Create Webhook

```json
{
  "url": "https://example.com/webhook",
  "secret": "my-hmac-secret",
  "events": ["sensor.threshold_exceeded", "experiment.started"],
  "enabled": true
}
```

**Webhook Event Types:** `sensor.threshold_exceeded`, `sensor.reading`, `experiment.started`, `experiment.stopped`, `system.health_changed`

**Delivery Statuses:** `pending`, `delivered`, `failed`, `dead_letter`

!!! info "HMAC Verification"
    If a `secret` is provided, each delivery includes an `X-Webhook-Signature` header containing
    the HMAC-SHA256 signature of the payload body, which can be used to verify authenticity.

---

## Rules

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/rules` | Admin | List automation rules |
| `POST` | `/api/v1/rules` | Admin | Create rule |
| `GET` | `/api/v1/rules/{id}` | Admin | Get rule details |
| `PUT` | `/api/v1/rules/{id}` | Admin | Update rule |
| `DELETE` | `/api/v1/rules/{id}` | Admin | Delete rule |

### Create Rule

```json
{
  "name": "High Temperature Alert",
  "event_public_id": "evt_temp01",
  "operator": "gt",
  "threshold": 50.0,
  "action_type": "webhook",
  "webhook_event_type": "sensor.threshold_exceeded",
  "cooldown_seconds": 300,
  "enabled": true
}
```

**Operators:** `gt` (>), `lt` (<), `gte` (>=), `lte` (<=), `eq` (==), `between`, `not_between`

**Action Types:** `webhook`, `log`

!!! tip "Between operator"
    When using `between` or `not_between`, provide both `threshold` (low) and `threshold_high` (high) values.

---

## OTA Updates

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/ota` | Admin | List firmware updates |
| `POST` | `/api/v1/ota` | Admin | Create firmware update |
| `GET` | `/api/v1/ota/{id}` | Admin | Get update details |
| `DELETE` | `/api/v1/ota/{id}` | Admin | Delete firmware update |
| `POST` | `/api/v1/ota/{id}/apply` | Admin | Apply firmware update |
| `POST` | `/api/v1/ota/{id}/rollback` | Admin | Rollback firmware update |
| `GET` | `/api/v1/ota/check` | Admin | Check for available updates |

### Create Firmware Update

```json
{
  "version": "2.1.0",
  "changelog": "Performance improvements and bug fixes"
}
```

**Update Statuses:** `pending`, `downloading`, `verifying`, `applying`, `completed`, `failed`, `rolled_back`

---

## Health Check

### `GET /health`

Returns system health — no authentication required. Used by Docker healthcheck.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "database": "ok",
  "last_datapoint": "2025-01-15T14:30:00.123456",
  "uptime_seconds": 3621.5
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | `"ok"` or `"degraded"` |
| `version` | string | Application version |
| `database` | string | `"ok"` or `"error"` |
| `last_datapoint` | string \| null | ISO timestamp of last datapoint, or `null` |
| `uptime_seconds` | number | Seconds since application start |

---

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Not Found"
}
```

| Status Code | Meaning |
|---|---|
| `400` | Bad request / validation error |
| `401` | Unauthorized — invalid or missing token |
| `403` | Forbidden — insufficient permissions |
| `404` | Resource not found |
| `422` | Validation error — Pydantic schema mismatch |
| `500` | Internal server error |

---

## OpenAPI Documentation

FastAPI auto-generates interactive API docs:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## Next Steps

- [WebSocket API](websocket.md) — real-time endpoints
- [Schemas](schemas.md) — Pydantic model reference
