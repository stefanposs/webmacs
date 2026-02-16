#!/usr/bin/env python3
"""Minimal WebMACS webhook receiver — zero external dependencies.

Run with::

    python receiver.py                     # default: 0.0.0.0:9000
    python receiver.py --port 8080         # custom port
    WEBHOOK_SECRET=s3cret python receiver.py  # enable signature verification

Handles POST /webhook and logs every delivery to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from verify import verify_signature

WEBHOOK_SECRET: str | None = os.environ.get("WEBHOOK_SECRET")


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler that accepts WebMACS webhook deliveries."""

    def do_POST(self) -> None:  # noqa: N802 — stdlib naming
        if self.path != "/webhook":
            self.send_error(404, "Not Found")
            return

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Verify signature (if secret is configured)
        if WEBHOOK_SECRET:
            timestamp = self.headers.get("X-Webhook-Timestamp", "")
            signature = self.headers.get("X-Webhook-Signature", "")
            if not verify_signature(body, WEBHOOK_SECRET, timestamp, signature):
                self.send_error(401, "Invalid signature")
                print("⚠  Rejected — invalid signature or replay")
                return

        # Parse payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        event_type = payload.get("type", "unknown")
        timestamp_str = payload.get("time", "")

        # ── Handle each event type ───────────────────────────────────────
        match event_type:
            case "sensor.threshold_exceeded":
                sensor = payload.get("sensor", "?")
                value = payload.get("value", "?")
                print(f"🔴 THRESHOLD EXCEEDED  sensor={sensor}  value={value}  time={timestamp_str}")

            case "sensor.reading":
                sensor = payload.get("sensor", "?")
                value = payload.get("value", "?")
                print(f"📊 SENSOR READING      sensor={sensor}  value={value}  time={timestamp_str}")

            case "experiment.started":
                print(f"🟢 EXPERIMENT STARTED  time={timestamp_str}  payload={json.dumps(payload)}")

            case "experiment.stopped":
                print(f"🔵 EXPERIMENT STOPPED  time={timestamp_str}  payload={json.dumps(payload)}")

            case "system.health_changed":
                print(f"⚙️  HEALTH CHANGED     time={timestamp_str}  payload={json.dumps(payload)}")

            case _:
                print(f"❓ UNKNOWN EVENT       type={event_type}  payload={json.dumps(payload)}")

        # Respond 200 — WebMACS marks the delivery as "delivered"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, fmt: str, *args: object) -> None:
        """Suppress default access logging (we log events ourselves)."""


def main() -> None:
    parser = argparse.ArgumentParser(description="WebMACS Webhook Receiver")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9000, help="Listen port (default: 9000)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), WebhookHandler)
    sig_status = "enabled" if WEBHOOK_SECRET else "disabled (set WEBHOOK_SECRET to enable)"
    print(f"🚀 WebMACS Webhook Receiver listening on {args.host}:{args.port}")
    print(f"   Endpoint:   POST http://{args.host}:{args.port}/webhook")
    print(f"   Signature:  {sig_status}")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
