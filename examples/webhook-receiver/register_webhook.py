#!/usr/bin/env python3
"""Register a webhook subscription in WebMACS via the REST API.

Configure via environment variables::

    export WEBMACS_URL=http://localhost:8000   # WebMACS backend URL
    export WEBMACS_TOKEN=your-jwt-token        # Admin JWT token
    export WEBHOOK_SECRET=my-webhook-secret    # Optional: HMAC signing secret
    export RECEIVER_URL=http://localhost:9000/webhook  # Your receiver endpoint

Run::

    python register_webhook.py

The script will create a new webhook subscription that listens for
threshold, experiment, and health events.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

# ── Configuration ────────────────────────────────────────────────────────────

WEBMACS_URL = os.environ.get("WEBMACS_URL", "http://localhost:8000")
WEBMACS_TOKEN = os.environ.get("WEBMACS_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
RECEIVER_URL = os.environ.get("RECEIVER_URL", "http://localhost:9000/webhook")

if not WEBMACS_TOKEN:
    print("Error: Set WEBMACS_TOKEN environment variable to your admin JWT token.")
    print()
    print("  # Login first:")
    print(f'  TOKEN=$(curl -s -X POST {WEBMACS_URL}/api/v1/auth/login \\')
    print('    -H "Content-Type: application/json" \\')
    print("    -d '{\"email\": \"admin@example.com\", \"password\": \"changeme\"}' \\")
    print("    | python3 -c \"import sys,json; print(json.load(sys.stdin)['Authorization'])\")")
    print()
    print("  export WEBMACS_TOKEN=$TOKEN")
    sys.exit(1)


def main() -> None:
    """Create a webhook subscription via the WebMACS API."""
    payload = {
        "url": RECEIVER_URL,
        "events": [
            "sensor.threshold_exceeded",
            "experiment.started",
            "experiment.stopped",
            "system.health_changed",
        ],
        "enabled": True,
    }

    # Include secret if configured
    if WEBHOOK_SECRET:
        payload["secret"] = WEBHOOK_SECRET

    body = json.dumps(payload).encode()

    req = urllib.request.Request(
        f"{WEBMACS_URL}/api/v1/webhooks",
        data=body,
        headers={
            "Authorization": f"Bearer {WEBMACS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            result = json.loads(resp.read())
            print(f"✅ Webhook registered successfully!")
            print(f"   URL:    {RECEIVER_URL}")
            print(f"   Events: {', '.join(payload['events'])}")
            print(f"   Secret: {'configured' if WEBHOOK_SECRET else 'none (no signature verification)'}")
            print(f"   Response: {json.dumps(result, indent=2)}")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode()
        print(f"❌ Failed to register webhook (HTTP {exc.code}):")
        print(f"   {error_body}")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"❌ Connection failed: {exc.reason}")
        print(f"   Is WebMACS running at {WEBMACS_URL}?")
        sys.exit(1)


if __name__ == "__main__":
    main()
