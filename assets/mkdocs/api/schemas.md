# Schemas

WebMACS uses **Pydantic v2** for all request/response validation. This page documents every schema model used across the API.

!!! tip "Interactive Docs"
    FastAPI auto-generates interactive schemas at `/docs` (Swagger UI) and `/redoc`.

---

## Auth

### LoginRequest

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | `EmailStr` | Yes | User email address |
| `password` | `str` | Yes | User password (min 1 char) |

### LoginResponse

| Field | Type | Description |
|---|---|---|
| `status` | `str` | Always `"success"` |
| `message` | `str` | `"Successfully logged in."` |
| `access_token` | `str` | JWT token for subsequent requests |
| `public_id` | `str` | User's public identifier |
| `username` | `str` | Display name |

---

## Users

### UserCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `email` | `EmailStr` | Yes | Valid email |
| `username` | `str` | Yes | 2–50 characters |
| `password` | `str` | Yes | Min 8 characters |

### UserUpdate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `email` | `EmailStr` | No | Valid email |
| `username` | `str` | No | 2–50 characters |
| `password` | `str` | No | Min 8 characters |

### UserResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `email` | `str` | Email address |
| `username` | `str` | Display name |
| `admin` | `bool` | Admin privileges |
| `registered_on` | `datetime` | Registration timestamp |

---

## Events

### EventCreate

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | Yes | Event name (1–255 chars) |
| `min_value` | `float` | Yes | Minimum expected value |
| `max_value` | `float` | Yes | Maximum expected value |
| `unit` | `str` | Yes | Unit of measurement (1–255 chars) |
| `type` | `EventType` | Yes | One of: `sensor`, `actuator`, `range`, `cmd_button`, `cmd_opened`, `cmd_closed` |

### EventUpdate

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | No | Updated name |
| `min_value` | `float` | No | Updated minimum |
| `max_value` | `float` | No | Updated maximum |
| `unit` | `str` | No | Updated unit |
| `type` | `EventType` | No | Updated type |

### EventResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `name` | `str` | Event name |
| `min_value` | `float` | Minimum expected value |
| `max_value` | `float` | Maximum expected value |
| `unit` | `str` | Unit of measurement |
| `type` | `EventType` | Event type |
| `user_public_id` | `str` | Owner's public ID |

---

## Experiments

### ExperimentCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | `str` | Yes | 1–255 characters |

### ExperimentUpdate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | `str` | No | Max 255 characters |

### ExperimentResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `name` | `str` | Experiment name |
| `started_on` | `datetime \| null` | Start timestamp |
| `stopped_on` | `datetime \| null` | Stop timestamp (null if running) |
| `user_public_id` | `str` | Owner's public ID |

---

## Datapoints

### DatapointCreate

| Field | Type | Required | Description |
|---|---|---|---|
| `value` | `float` | Yes | Measured value |
| `event_public_id` | `str` | Yes | Associated event ID |

!!! info "Experiment linking"
    Datapoints are **automatically linked** to the currently running experiment.
    There is no `experiment_public_id` field on create.

### DatapointBatchCreate

| Field | Type | Required | Description |
|---|---|---|---|
| `datapoints` | `list[DatapointCreate]` | Yes | Array of datapoints to insert |

### DatapointResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `value` | `float` | Measured value |
| `timestamp` | `datetime` | When the value was recorded |
| `event_public_id` | `str` | Associated event ID |
| `experiment_public_id` | `str \| null` | Linked experiment (if any) |

### DatapointSeriesRequest

Used by `POST /api/v1/datapoints/series` for dashboard charts.

| Field | Type | Default | Constraints | Description |
|---|---|---|---|---|
| `event_public_ids` | `list[str]` | — | 1–20 items | Events to query |
| `minutes` | `int` | `60` | 1–14400 | Time window (max ~10 days) |
| `max_points` | `int` | `500` | 10–2000 | Server-side downsampling limit |

---

## Logs

### LogEntryCreate

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `content` | `str` | Yes | — | Log message (1–500 chars) |
| `logging_type` | `LoggingType` | No | `info` | Severity level |

### LogEntryUpdate

| Field | Type | Required | Description |
|---|---|---|---|
| `status_type` | `StatusType` | No | Mark as `read` or `unread` |
| `content` | `str` | No | Update content |

### LogEntryResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `content` | `str` | Log message |
| `logging_type` | `LoggingType` | Severity: `error`, `warning`, `info` |
| `status_type` | `StatusType` | Read status: `read`, `unread` |
| `created_on` | `datetime` | Creation timestamp |
| `user_public_id` | `str` | Author's public ID |

---

## Rules

### RuleCreate

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | `str` | Yes | — | Rule name (1–255 chars) |
| `event_public_id` | `str` | Yes | — | Event to monitor |
| `operator` | `RuleOperator` | Yes | — | Comparison operator |
| `threshold` | `float` | Yes | — | Threshold value |
| `threshold_high` | `float` | No | — | Upper bound (required for `between` / `not_between`) |
| `action_type` | `RuleActionType` | Yes | — | `webhook` or `log` |
| `webhook_event_type` | `WebhookEventType` | No | — | Webhook event to fire |
| `enabled` | `bool` | No | `true` | Active state |
| `cooldown_seconds` | `int` | No | `60` | Minimum seconds between triggers |

!!! note "Operator validation"
    When using `between` or `not_between`, `threshold_high` is required and must be ≥ `threshold`.

### RuleResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `name` | `str` | Rule name |
| `event_public_id` | `str` | Monitored event |
| `operator` | `RuleOperator` | Comparison operator |
| `threshold` | `float` | Threshold value |
| `threshold_high` | `float \| null` | Upper bound |
| `action_type` | `RuleActionType` | Action type |
| `webhook_event_type` | `str \| null` | Webhook event type |
| `enabled` | `bool` | Active state |
| `cooldown_seconds` | `int` | Cooldown period |
| `last_triggered_at` | `datetime \| null` | Last trigger time |
| `created_on` | `datetime` | Creation timestamp |
| `user_public_id` | `str` | Owner's public ID |

---

## Webhooks

### WebhookCreate

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `url` | `str` | Yes | — | Endpoint URL (must start with `http://` or `https://`) |
| `secret` | `str` | No | — | HMAC-SHA256 signing secret (max 255 chars) |
| `events` | `list[WebhookEventType]` | Yes | — | Events to subscribe to |
| `enabled` | `bool` | No | `true` | Active state |

### WebhookResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `url` | `str` | Endpoint URL |
| `events` | `list[str]` | Subscribed event types |
| `enabled` | `bool` | Active state |
| `created_on` | `datetime` | Creation timestamp |
| `user_public_id` | `str` | Owner's public ID |

### WebhookDeliveryResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Delivery ID |
| `event_type` | `str` | Event that triggered the delivery |
| `status` | `WebhookDeliveryStatus` | `pending`, `delivered`, `failed`, `dead_letter` |
| `attempts` | `int` | Number of delivery attempts |
| `last_error` | `str \| null` | Last error message |
| `response_code` | `int \| null` | HTTP response code |
| `created_on` | `datetime` | Created at |
| `delivered_on` | `datetime \| null` | Successfully delivered at |

---

## OTA Updates

### FirmwareUpdateCreate

| Field | Type | Required | Constraints | Description |
|---|---|---|---|---|
| `version` | `str` | Yes | Semantic versioning (`X.Y.Z`) | Firmware version |
| `changelog` | `str` | No | — | Release notes |

### FirmwareUpdateResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `version` | `str` | Firmware version |
| `changelog` | `str \| null` | Release notes |
| `file_hash_sha256` | `str \| null` | SHA-256 hash of firmware file |
| `file_size_bytes` | `int \| null` | File size in bytes |
| `has_firmware_file` | `bool` | Whether a firmware binary has been uploaded |
| `status` | `UpdateStatus` | `pending`, `downloading`, `verifying`, `applying`, `completed`, `failed`, `rolled_back` |
| `error_message` | `str \| null` | Error details (if failed) |
| `created_on` | `datetime` | Created at |
| `started_on` | `datetime \| null` | Apply started at |
| `completed_on` | `datetime \| null` | Apply completed at |
| `user_public_id` | `str` | Owner's public ID |

### UpdateCheckResponse

| Field | Type | Description |
|---|---|---|
| `current_version` | `str` | Currently running version |
| `latest_version` | `str \| null` | Latest local version |
| `update_available` | `bool` | Whether an update is available |
| `github_latest_version` | `str \| null` | Latest GitHub release |
| `github_download_url` | `str \| null` | GitHub download URL |
| `github_release_url` | `str \| null` | GitHub release page |
| `github_error` | `str \| null` | Error fetching from GitHub |

---

## Dashboards

### DashboardCreate

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | `str` | Yes | — | Dashboard name (1–255 chars) |
| `is_global` | `bool` | No | `false` | Visible to all users |

### DashboardResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `name` | `str` | Dashboard name |
| `is_global` | `bool` | Globally visible |
| `created_on` | `datetime` | Created at |
| `user_public_id` | `str` | Owner's public ID |
| `widgets` | `list[DashboardWidgetResponse]` | Attached widgets |

### DashboardWidgetCreate

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `widget_type` | `WidgetType` | Yes | — | `line_chart`, `gauge`, `stat_card`, `actuator_toggle` |
| `title` | `str` | Yes | — | Widget title (1–255 chars) |
| `event_public_id` | `str` | No | — | Data source event |
| `x` | `int` | No | `0` | Grid column position |
| `y` | `int` | No | `0` | Grid row position |
| `w` | `int` | No | `4` | Width in grid columns (1–12) |
| `h` | `int` | No | `3` | Height in grid rows (1–12) |
| `config_json` | `str` | No | — | Custom widget configuration (JSON string) |

### DashboardWidgetResponse

| Field | Type | Description |
|---|---|---|
| `public_id` | `str` | Unique identifier |
| `widget_type` | `WidgetType` | Widget type |
| `title` | `str` | Widget title |
| `event_public_id` | `str \| null` | Data source |
| `x` | `int` | Grid column |
| `y` | `int` | Grid row |
| `w` | `int` | Width |
| `h` | `int` | Height |
| `config_json` | `str \| null` | Custom configuration |

---

## Health

### HealthResponse

| Field | Type | Description |
|---|---|---|
| `status` | `str` | `"healthy"` |
| `version` | `str` | Application version |
| `database` | `str` | Database status |
| `last_datapoint` | `datetime \| null` | Most recent datapoint timestamp |
| `uptime_seconds` | `float \| null` | Server uptime |

---

## Generic Schemas

### StatusResponse

| Field | Type | Description |
|---|---|---|
| `status` | `str` | `"success"` or `"error"` |
| `message` | `str` | Human-readable message |

### PaginatedResponse

| Field | Type | Description |
|---|---|---|
| `page` | `int` | Current page number |
| `page_size` | `int` | Items per page |
| `total` | `int` | Total item count |
| `data` | `list[T]` | Array of items |

---

## Enums

### EventType

| Value | Description |
|---|---|
| `sensor` | Continuous measurement input |
| `actuator` | Controllable output |
| `range` | Range-bounded value |
| `cmd_button` | Momentary command |
| `cmd_opened` | Open state command |
| `cmd_closed` | Close state command |

### LoggingType

| Value | Description |
|---|---|
| `error` | Error-level log |
| `warning` | Warning-level log |
| `info` | Informational log |

### StatusType

| Value | Description |
|---|---|
| `read` | Log entry has been read |
| `unread` | Log entry is unread |

### RuleOperator

| Value | Description |
|---|---|
| `gt` | Greater than (>) |
| `lt` | Less than (<) |
| `gte` | Greater than or equal (≥) |
| `lte` | Less than or equal (≤) |
| `eq` | Equal (==) |
| `between` | Within range (inclusive) |
| `not_between` | Outside range |

### RuleActionType

| Value | Description |
|---|---|
| `webhook` | Fire a webhook event |
| `log` | Create a log entry |

### WidgetType

| Value | Description |
|---|---|
| `line_chart` | Time-series line chart |
| `gauge` | Radial gauge indicator |
| `stat_card` | Single-value display card |
| `actuator_toggle` | On/off toggle switch |

### WebhookEventType

| Value | Description |
|---|---|
| `sensor.threshold_exceeded` | Sensor crossed a threshold |
| `sensor.reading` | New sensor reading |
| `experiment.started` | Experiment started |
| `experiment.stopped` | Experiment stopped |
| `system.health_changed` | System health changed |

### WebhookDeliveryStatus

| Value | Description |
|---|---|
| `pending` | Pending delivery |
| `delivered` | Successfully delivered |
| `failed` | Delivery failed |
| `dead_letter` | Permanently failed |

### UpdateStatus

| Value | Description |
|---|---|
| `pending` | Awaiting action |
| `downloading` | Downloading firmware |
| `verifying` | Verifying integrity |
| `applying` | Applying update |
| `completed` | Successfully applied |
| `failed` | Update failed |
| `rolled_back` | Rolled back to previous version |

---

## Next Steps

- [REST API](rest.md) — how schemas are used in endpoints
- [WebSocket API](websocket.md) — real-time protocol reference
- [Backend Architecture](../architecture/backend.md) — code structure