# WebSocket API

WebMACS uses WebSockets for **real-time sensor data streaming** between the IoT controller, backend, and browser dashboards.

---

## Endpoints

| Endpoint | Direction | Purpose |
|---|---|---|
| `/ws/controller/telemetry` | Controller → Backend | Push sensor readings in batches |
| `/ws/datapoints/stream` | Backend → Browser | Live dashboard updates |

Both endpoints are mounted under the `/ws/` prefix.

---

## Authentication

**All WebSocket endpoints require a valid JWT token** passed as a query parameter:

```
ws://your-host/ws/controller/telemetry?token=<jwt>
wss://your-host/ws/datapoints/stream?token=<jwt>
```

!!! warning "Token required"
    Connections without a valid token are immediately closed with code **1008** (Policy Violation) and one of:

    - `"Authentication required"` — no token provided
    - `"Invalid or expired token"` — JWT decoding failed
    - `"Token has been revoked"` — token was blacklisted (user logged out)
    - `"User not found"` — user deleted after token issued

---

## Controller Telemetry — `/ws/controller/telemetry`

This endpoint receives **batches of sensor readings** from the IoT controller and persists them.

### Inbound Message Format

```json
{
  "datapoints": [
    { "value": 23.5, "event_public_id": "abc-123" },
    { "value": 1013.2, "event_public_id": "def-456" },
    { "value": 7.14, "event_public_id": "ghi-789" }
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `datapoints` | array | Yes | Batch of readings (max **500** items) |
| `datapoints[].value` | number | Yes | Sensor reading value |
| `datapoints[].event_public_id` | string (UUID) | Yes | Matches an Event's `public_id` |

!!! warning "Batch size limit"
    Batches exceeding **500 datapoints** are rejected with an error message.
    The controller automatically chunks large batches via `WEBMACS_MAX_BATCH_SIZE`.

### Processing Pipeline

For each valid batch, the backend:

1. **Validates** each datapoint (must have `value` and `event_public_id`)
2. **Filters** by active plugin linkage — only events with an enabled plugin instance are accepted
3. **Persists** to PostgreSQL (bulk `INSERT` with `experiment_public_id` from active experiment)
4. **Dispatches webhooks** — fires `sensor_reading` webhook events (throttled to 1 per 5 s per sensor)
5. **Evaluates rules** — checks threshold rules for the **last value per event** in the batch
6. **Broadcasts** to all connected frontends (throttled to ≥ 200 ms per event)

### Error Response

If no valid datapoints are found in a batch:

```json
{ "type": "error", "message": "No valid datapoints in batch" }
```

---

## Datapoint Stream — `/ws/datapoints/stream`

This is a **read-only subscription** endpoint for browser dashboards. Clients connect and receive real-time broadcasts.

### Connection Flow

```
Browser                         Backend
  │                                │
  │──── WebSocket connect ────────►│
  │     ?token=<jwt>               │
  │                                │
  │◄─── { type: "connected" } ────│  (1) confirmation
  │                                │
  │     { type: "ping" }  ────────►│  (2) keep-alive (optional)
  │◄─── { type: "pong" }  ────────│
  │                                │
  │◄─── datapoints_batch ─────────│  (3) live data
  │◄─── datapoints_batch ─────────│
  │     ...                        │
```

### 1. Connection Confirmation

Immediately after authentication, the server sends:

```json
{
  "type": "connected",
  "message": "Subscribed to live datapoint stream."
}
```

### 2. Keep-Alive (Ping/Pong)

Clients can send periodic pings to prevent connection timeouts:

```json
{ "type": "ping" }
```

Server responds:

```json
{ "type": "pong" }
```

!!! tip "Frontend default"
    The built-in Vue frontend sends a ping every **25 seconds**.

### 3. Broadcast Messages

When the controller pushes new sensor data, all connected frontends receive:

```json
{
  "type": "datapoints_batch",
  "datapoints": [
    {
      "value": 23.5,
      "event_public_id": "abc-123",
      "timestamp": "2025-01-15T14:30:00.123456",
      "experiment_public_id": "exp-001"
    },
    {
      "value": 1013.2,
      "event_public_id": "def-456",
      "timestamp": "2025-01-15T14:30:00.123456",
      "experiment_public_id": "exp-001"
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Always `"datapoints_batch"` |
| `datapoints` | array | Array of persisted datapoints |
| `datapoints[].value` | number | Sensor reading |
| `datapoints[].event_public_id` | string | Event UUID |
| `datapoints[].timestamp` | string | ISO 8601 timestamp |
| `datapoints[].experiment_public_id` | string \| null | Active experiment UUID, or `null` if none |

---

## Connection Manager

The backend uses a **pub/sub connection manager** with named groups:

| Group | Members | Purpose |
|---|---|---|
| `"controller"` | IoT controller(s) | Data ingestion |
| `"frontend"` | Browser clients | Data consumption |

The `broadcast("frontend", payload)` call sends to all connected browsers simultaneously.

---

## Frontend Fallback Strategy

The Vue frontend implements **WebSocket-first with automatic HTTP polling fallback**:

1. Attempts WebSocket connection to `/ws/datapoints/stream`
2. After **3 consecutive failures**, falls back to `GET /api/v1/datapoints/latest` every **1500ms**
3. When WebSocket reconnects, polling is automatically stopped

```typescript
type ConnectionMode = 'websocket' | 'polling' | 'connecting'
```

---

## Nginx Proxy Configuration

For production, Nginx must proxy WebSocket connections:

```nginx
location /ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;  # 24h — prevent premature close
}
```

---

## Next Steps

- [Backend Architecture](../architecture/backend.md) — application structure
- [REST API](rest.md) — HTTP endpoint reference
- [Schema Reference](schemas.md) — request/response models