# Events & Sensors

Events represent the physical sensors and actuators connected to the IoT controller. Every datapoint recorded by WebMACS belongs to exactly one event.

Think of events as **channel definitions** — they describe *what* is being measured (or controlled), while [datapoints](datapoints.md) hold the actual values.

---

## Event Types

WebMACS supports six event types:

| Type | Icon | Description | Dashboard Widget |
|---|---|---|---|
| `sensor` | :material-thermometer: | Continuous measurement (temperature, pressure, flow) | Value card with range bar |
| `actuator` | :material-toggle-switch: | Binary on/off control (valves, heaters, motors) | ON / OFF toggle |
| `range` | :material-tune-vertical: | Adjustable value within min/max bounds | Slider control |
| `cmd_button` | :material-gesture-tap-button: | Momentary command button | — |
| `cmd_opened` | :material-arrow-expand: | Open-state command | — |
| `cmd_closed` | :material-arrow-collapse: | Close-state command | — |

!!! tip "Choosing the right type"
    - Use **sensor** for anything you want to monitor passively (readings from the hardware).
    - Use **actuator** for anything the operator needs to switch on or off.
    - Use **range** for setpoints where the operator picks a value within a defined range.

---

## Event Properties

| Field | Required | Description |
|---|---|---|
| **Name** | Yes | Human-readable label (must be unique) |
| **Type** | Yes | One of the six types above |
| **Unit** | No | Measurement unit (°C, bar, L/min, %, rpm) |
| **Min Value** | No | Lower bound (used for range bar / slider) |
| **Max Value** | No | Upper bound (used for range bar / slider) |

!!! info "Min / Max values"
    For **range** events, `min_value` and `max_value` define the slider boundaries. For **sensor** events they define the range bar visual on the Dashboard. If not set, the range bar is not displayed.

---

## Managing Events via the UI

### Creating an Event

1. Navigate to **Events** in the sidebar
2. Click **New Event**
3. Fill in the fields:
    - **Name** — e.g. "Inlet Temperature"
    - **Type** — select from dropdown
    - **Unit** — e.g. "°C"
    - **Min / Max Value** — optional range bounds
4. Click **Create**

### Editing an Event

Click the :material-pencil: edit button on any event row. Change the fields you need and save.

### Deleting an Event

Click the :material-delete: delete button and confirm. Deleting an event **does not** delete its historical datapoints.

---

## Managing Events via the API

### List Events

```bash
curl http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $TOKEN"
```

Response is paginated. Use `?page=1&page_size=50` query parameters.

### Create an Event

```bash
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Inlet Temperature",
    "type": "sensor",
    "unit": "°C",
    "min_value": 0,
    "max_value": 300
  }'
```

!!! warning "Duplicate names"
    Event names must be unique. Attempting to create an event with an existing name returns **409 Conflict**.

### Update an Event

```bash
curl -X PUT http://localhost:8000/api/v1/events/$EVENT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"unit": "K"}'
```

### Delete an Event

```bash
curl -X DELETE http://localhost:8000/api/v1/events/$EVENT_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Controller Mapping

The IoT controller maps physical I/O pins to event Public IDs. This is configured via the `WEBMACS_REVPI_MAPPING` environment variable:

```json
{
  "Input_1": "evt_temp_inlet",
  "Input_2": "evt_pressure_chamber",
  "Output_1": "evt_valve_main"
}
```

The controller reads hardware values for each mapped input and sends them as datapoints to the backend. For output events (actuators), the controller watches for new datapoints and writes the value to the physical output.

!!! info "No mapping, no data"
    Only events that appear in the controller mapping will produce live data. You can create events in the UI first, then configure the mapping on the controller.

---

## Best Practices

- **Name descriptively**: "Inlet Temperature Reactor A" is better than "Temp1"
- **Set units**: They appear on the Dashboard and in CSV exports
- **Set min/max**: Enables range bars on the Dashboard and `between`/`not_between` operators in [Rules](rules.md)
- **Use the right type**: The Dashboard renders different widgets per type

---

## Next Steps

- [Dashboard](dashboard.md) — see events in action
- [Experiments](experiments.md) — group datapoints by experiment
- [Automation Rules](rules.md) — alert when sensor values cross thresholds
- [API Reference](../api/rest.md) — full events endpoint documentation
