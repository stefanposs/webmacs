# WebMACS Modbus TCP Sensor Plugin — Example

A production-style example demonstrating how to build a WebMACS plugin
that communicates over **Modbus TCP** with both **input** (sensor) and
**output** (actuator) channels plus **custom configuration**.

> This plugin ships with **simulated hardware** by default (demo mode).
> Replace the `_do_*` methods with real `pymodbus` calls for production.

## Channels

| Channel ID     | Name                    | Direction | Unit  | Range    |
| -------------- | ----------------------- | --------- | ----- | -------- |
| `temperature`  | Process Temperature     | input     | °C    | 0 – 500  |
| `flow_rate`    | Flow Rate               | input     | L/min | 0 – 100  |
| `valve_setpoint` | Valve Setpoint        | output    | %     | 0 – 100  |

## Features demonstrated

- **Custom configuration** — `ModbusSensorConfig` with `host`, `port`,
  `unit_id`, and `timeout_seconds` fields that render as a dynamic form
  in the WebMACS frontend.
- **Output (actuator) channels** — write values back to hardware via
  `_do_write()`.
- **Error handling** — connection failures, read timeouts, and graceful
  disconnect.
- **Conversion specs** — raw Modbus register values are scaled to
  engineering units.
- **Health check** — custom health report with connection latency.

## Quick start

```bash
# Build the wheel
pip install build
python -m build

# Upload to WebMACS
curl -X POST https://your-webmacs/api/v1/plugins/packages/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@dist/webmacs_plugin_modbus_sensor-0.1.0-py3-none-any.whl"

# Create an instance via API
curl -X POST https://your-webmacs/api/v1/plugins/instances \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "plugin_id": "modbus_sensor",
    "instance_name": "Reactor Tank 1",
    "demo_mode": true,
    "config": {
      "host": "192.168.1.50",
      "port": 502,
      "unit_id": 1,
      "timeout_seconds": 3.0
    }
  }'
```

## Running tests

```bash
uv sync
uv run pytest tests/ -v
```

## Project structure

```
examples/modbus-plugin/
├── pyproject.toml
├── README.md
├── src/
│   └── webmacs_plugin_modbus/
│       ├── __init__.py
│       ├── config.py          # Custom Pydantic config model
│       └── plugin.py          # Plugin implementation
└── tests/
    ├── __init__.py
    └── test_modbus.py         # Conformance suite + custom tests
```

## Adapting for real Modbus hardware

1. `pip install pymodbus` and add it to `dependencies` in `pyproject.toml`.
2. In `_do_connect()`, create a `AsyncModbusTcpClient` connection.
3. In `_do_read()`, call `client.read_holding_registers(...)` and scale the
   raw register value using the conversion spec.
4. In `_do_write()`, call `client.write_register(...)` to set actuator values.
5. Set `demo_mode=false` when creating the instance.

## License

MIT
