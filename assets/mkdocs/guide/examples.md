# Examples

WebMACS ships with complete, ready-to-use examples in the `examples/` directory.
Each example is a standalone project with its own `README`, source code, and tests.

---

## Weather Station Plugin

**Path:** `examples/custom-plugin/`

A beginner-friendly example showing how to write a custom WebMACS plugin from scratch.

| Channel | Direction | Unit | Range |
|---|---|---|---|
| `temperature` | input | °C | −40 … 60 |
| `humidity` | input | % | 0 … 100 |
| `wind_speed` | input | km/h | 0 … 200 |
| `pressure` | input | hPa | 900 … 1 100 |
| `rainfall` | input | mm/h | 0 … 100 |

**What you'll learn:**

- Plugin structure (`pyproject.toml`, entry points)
- Defining input channels with metadata
- Building and uploading a `.whl` file
- Demo mode with simulated data

```bash
cd examples/custom-plugin
pip install build && python -m build
# Upload dist/*.whl via WebMACS UI → Settings → Plugins
```

See [Plugin Development Guide](../development/plugin-development.md) for the full documentation.

---

## Modbus TCP Sensor Plugin

**Path:** `examples/modbus-plugin/`

A production-style example demonstrating Modbus TCP communication with both input sensors and output actuators.

| Channel | Direction | Unit | Range |
|---|---|---|---|
| `temperature` | input | °C | 0 – 500 |
| `flow_rate` | input | L/min | 0 – 100 |
| `valve_setpoint` | output | % | 0 – 100 |

**What you'll learn:**

- **Custom configuration** — `ModbusSensorConfig` with host, port, unit_id fields
- **Output channels** — writing values back to hardware actuators
- **Error handling** — connection failures, read timeouts, graceful disconnect
- **Conversion specs** — raw Modbus register values → engineering units
- **Health checks** — custom health reporting with connection latency

```bash
cd examples/modbus-plugin
pip install build && python -m build
# Includes 23 tests: pytest
```

!!! tip "Demo Mode"
    The plugin ships with simulated hardware by default. Replace the `_do_*` methods with real `pymodbus` calls for production.

---

## Webhook Receiver

**Path:** `examples/webhook-receiver/`

A complete example showing how to receive, verify, and process webhook deliveries from WebMACS.

| File | Purpose |
|---|---|
| `receiver.py` | Minimal stdlib-based HTTP receiver |
| `receiver_fastapi.py` | Production FastAPI receiver with HMAC verification |
| `register_webhook.py` | Script to register a webhook via the REST API |
| `verify.py` | HMAC-SHA256 signature verification helper |

**Supported events:**

| Event | When |
|---|---|
| `sensor.threshold_exceeded` | Rule triggers on threshold crossing |
| `sensor.reading` | New datapoint recorded |
| `experiment.started` | Experiment starts |
| `experiment.stopped` | Experiment stops |
| `system.health_changed` | Controller health changes |

**Quick start:**

```bash
cd examples/webhook-receiver

# Start the receiver
python receiver_fastapi.py

# In another terminal, register it with WebMACS
python register_webhook.py --url http://your-server:9000/webhook --secret my-secret
```

See [Webhooks Guide](webhooks.md) and [Security — HMAC Signatures](security.md#webhook-hmac-signatures) for payload format and verification details.

---

## Running Example Tests

```bash
# Run all example tests
just test-example-plugin

# Run modbus plugin tests specifically
cd examples/modbus-plugin && pytest
```

---

## Next Steps

- [Plugin Development](../development/plugin-development.md) — full plugin SDK reference
- [Webhooks](webhooks.md) — configuring webhook subscriptions
- [Security](security.md) — HMAC signatures, authentication
