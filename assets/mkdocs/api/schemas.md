# Schemas

WebMACS uses **Pydantic v2** for all request/response validation. Below is a reference of all schema models.

---

## Auth Schemas

### LoginRequest

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str  # min_length=1
```

### LoginResponse

```python
class LoginResponse(BaseModel):
    status: str = "success"
    message: str = "Successfully logged in."
    access_token: str
    public_id: str
    username: str
```

---

## User Schemas

### UserCreate

```python
class UserCreate(BaseModel):
    email: EmailStr
    username: str  # min_length=2, max_length=50
    password: str  # min_length=8
```

### UserUpdate

```python
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None  # min_length=2, max_length=50
```

### UserResponse

```python
class UserResponse(BaseModel):
    public_id: str
    email: str
    username: str
    admin: bool
    registered_on: datetime
```

---

## Experiment Schemas

### ExperimentCreate

```python
class ExperimentCreate(BaseModel):
    name: str  # min_length=1, max_length=200
```

### ExperimentUpdate

```python
class ExperimentUpdate(BaseModel):
    name: str | None = None
    stopped_on: datetime | None = None
```

### ExperimentResponse

```python
class ExperimentResponse(BaseModel):
    public_id: str
    name: str
    started_on: datetime | None
    stopped_on: datetime | None
    user_public_id: str
```

---

## Event Schemas

### EventCreate

```python
class EventCreate(BaseModel):
    name: str
    type: EventType        # sensor | actuator | range | cmd_button | cmd_opened | cmd_closed
    unit: str | None = None
    description: str | None = None
```

### EventResponse

```python
class EventResponse(BaseModel):
    public_id: str
    name: str
    type: EventType
    unit: str | None
    description: str | None
```

---

## Datapoint Schemas

### DatapointCreate

```python
class DatapointCreate(BaseModel):
    value: float
    event_public_id: str
    experiment_public_id: str | None = None
```

### DatapointResponse

```python
class DatapointResponse(BaseModel):
    public_id: str
    value: float
    timestamp: datetime
    event_public_id: str
    experiment_public_id: str | None
```

---

## Log Schemas

### LogCreate

```python
class LogCreate(BaseModel):
    message: str
    type: LoggingType    # error | warning | info
    status: StatusType = StatusType.unread  # read | unread
```

### LogResponse

```python
class LogResponse(BaseModel):
    public_id: str
    message: str
    type: LoggingType
    status: StatusType
    created_on: datetime
```

---

## Enums

### EventType

| Value | Description |
|---|---|
| `sensor` | Continuous measurement |
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

---

## Next Steps

- [REST API](rest.md) — how schemas are used in endpoints
- [Backend Architecture](../architecture/backend.md) — code structure
