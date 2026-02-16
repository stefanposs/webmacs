# WebMACS Webhook Receiver — Example

A ready-to-run example showing how to **receive**, **verify**, and
**process** webhook deliveries from [WebMACS](https://github.com/stefanposs/webmacs).

## What it does

WebMACS delivers JSON payloads via HTTP POST to your URL whenever
subscribed events occur (e.g. sensor threshold exceeded, experiment
started/stopped, system health changed).

This example provides:

| File | Description |
|------|-------------|
| `receiver.py` | Standalone Flask/FastAPI-free receiver using the stdlib |
| `receiver_fastapi.py` | Production-ready FastAPI receiver with HMAC verification |
| `register_webhook.py` | Script to register the webhook via the REST API |
| `verify.py` | Helper to verify HMAC-SHA256 signatures |

## Supported event types

| Event | Fired when |
|-------|------------|
| `sensor.threshold_exceeded` | A rule triggers because a sensor value crosses a threshold |
| `sensor.reading` | A new datapoint is recorded |
| `experiment.started` | An experiment is started |
| `experiment.stopped` | An experiment is stopped |
| `system.health_changed` | Controller health status changes |

## Quick start

### 1. Start the receiver

```bash
# Minimal — no dependencies required
python receiver.py

# Or with FastAPI (pip install fastapi uvicorn)
uvicorn receiver_fastapi:app --host 0.0.0.0 --port 9000
```

### 2. Register the webhook in WebMACS

```bash
# Via the helper script
export WEBMACS_URL=http://localhost:8000
export WEBMACS_TOKEN=your-jwt-token
python register_webhook.py

# Or via curl
curl -X POST "$WEBMACS_URL/api/v1/webhooks" \
  -H "Authorization: Bearer $WEBMACS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://your-server:9000/webhook",
    "secret": "my-webhook-secret",
    "events": ["sensor.threshold_exceeded", "experiment.started", "experiment.stopped"],
    "enabled": true
  }'
```

### 3. Trigger an event

Create a datapoint that exceeds a rule threshold, or start/stop an
experiment — the webhook receiver will log the delivery.

## Payload format

```json
{
  "type": "sensor.threshold_exceeded",
  "time": "2026-02-16T14:30:00+00:00",
  "sensor": "temperature-main",
  "value": 85.3,
  "device": "reactor-1"
}
```

## Signature verification

When you configure a `secret` on the webhook, WebMACS signs every
delivery with HMAC-SHA256. Two headers are sent:

| Header | Content |
|--------|---------|
| `X-Webhook-Timestamp` | Unix timestamp (replay protection) |
| `X-Webhook-Signature` | `HMAC-SHA256(secret, "{timestamp}.{body}")` |

To verify (see `verify.py`):

```python
import hashlib, hmac

def verify_signature(body: bytes, secret: str, timestamp: str, signature: str) -> bool:
    message = f"{timestamp}.{body.decode()}"
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Adapting for production

- **Forward to Slack / Teams / PagerDuty** — parse the payload and POST
  to your messaging platform's incoming webhook URL.
- **Store in InfluxDB / Prometheus** — push metrics on
  `sensor.threshold_exceeded` events.
- **Trigger CI/CD pipelines** — react to `system.health_changed` events.
- **Add replay protection** — reject payloads where `X-Webhook-Timestamp`
  is older than 5 minutes.

## License

MIT
