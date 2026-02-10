# Events & Sensors

Events represent the physical sensors and actuators connected to the IoT controller. Every datapoint is linked to exactly one event.

---

## Event Types

WebMACS defines six event types via a `StrEnum`:

| Type | Description | Typical Use |
|---|---|---|
| `sensor` | Continuous measurement | Temperature, pressure, flow rate |
| `actuator` | Controllable output | Valves, heaters, motors |
| `range` | Range-bounded value | Min/max temperature thresholds |
| `cmd_button` | Momentary command | Start/stop buttons, triggers |
| `cmd_opened` | Open state command | Valve open confirmation |
| `cmd_closed` | Close state command | Valve close confirmation |

---

## Event Properties

Each event has:

| Field | Type | Description |
|---|---|---|
| `public_id` | `string` | Unique identifier (UUID) |
| `name` | `string` | Human-readable label |
| `type` | `EventType` | One of the six types above |
| `unit` | `string` | Measurement unit (°C, bar, L/min) |
| `description` | `string` | Optional notes |

---

## Managing Events

### Via the UI

Navigate to **Events** in the sidebar to view, create, edit, and delete events.

### Via the API

```bash
# List all events
curl http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $TOKEN"

# Create a new sensor event
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Inlet Temperature",
    "type": "sensor",
    "unit": "°C"
  }'
```

---

## Controller Mapping

The IoT controller maps physical I/O pins to event IDs. Configure via `WEBMACS_REVPI_MAPPING`:

```json
{
  "Input_1": "evt_temp_inlet",
  "Input_2": "evt_pressure_01",
  "Output_1": "evt_valve_main"
}
```

---

## Next Steps

- [Experiments](experiments.md) — group datapoints by experiment
- [API Reference](../api/rest.md) — full events endpoint docs
