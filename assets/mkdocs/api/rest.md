# REST API Reference

All endpoints are mounted under `/api/v1/`. Authentication uses JWT Bearer tokens unless noted otherwise.

---

## Authentication

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
| `PUT` | `/api/v1/experiments/{id}` | JWT | Update (e.g. stop) |
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
  "description": "Temperature at the fluidised-bed inlet"
}
```

**Event Types:** `sensor`, `actuator`, `range`, `cmd_button`, `cmd_opened`, `cmd_closed`

---

## Datapoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/datapoints` | JWT | List datapoints (paginated) |
| `POST` | `/api/v1/datapoints` | JWT | Create single datapoint |
| `POST` | `/api/v1/datapoints/bulk` | JWT | Create multiple datapoints |

### Create Datapoint

```json
{
  "value": 23.45,
  "event_public_id": "evt_temp01",
  "experiment_public_id": "exp_001"
}
```

### Query Parameters

| Param | Type | Default | Description |
|---|---|---|---|
| `limit` | `int` | `50` | Max results per page |
| `offset` | `int` | `0` | Pagination offset |
| `event_id` | `string` | — | Filter by event |
| `experiment_id` | `string` | — | Filter by experiment |

---

## Logs

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/logs` | JWT | List log entries |
| `POST` | `/api/v1/logs` | JWT | Create log entry |
| `PUT` | `/api/v1/logs/{id}` | JWT | Update (mark read) |
| `DELETE` | `/api/v1/logs/{id}` | JWT | Delete log entry |

### Create Log Entry

```json
{
  "message": "Experiment started",
  "type": "info",
  "status": "unread"
}
```

**Log types:** `error`, `warning`, `info`
**Statuses:** `read`, `unread`

---

## Health Check

### `GET /health`

Returns `200 OK` — used by Docker healthcheck.

```json
{
  "status": "healthy"
}
```

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
