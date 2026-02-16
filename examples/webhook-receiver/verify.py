"""HMAC-SHA256 signature verification for WebMACS webhooks.

WebMACS signs webhook payloads when a secret is configured.
This module provides helpers to verify signatures and reject tampered
or replayed deliveries.

Usage::

    from verify import verify_signature

    ok = verify_signature(
        body=request_body,
        secret="my-webhook-secret",
        timestamp=headers["X-Webhook-Timestamp"],
        signature=headers["X-Webhook-Signature"],
    )
"""

from __future__ import annotations

import hashlib
import hmac
import time


def verify_signature(
    body: bytes,
    secret: str,
    timestamp: str,
    signature: str,
    *,
    max_age_seconds: int = 300,
) -> bool:
    """Verify the HMAC-SHA256 signature of a WebMACS webhook delivery.

    Args:
        body: Raw request body bytes.
        secret: The shared secret configured on the webhook.
        timestamp: Value of the ``X-Webhook-Timestamp`` header (unix seconds).
        signature: Value of the ``X-Webhook-Signature`` header (hex digest).
        max_age_seconds: Maximum allowed age of the timestamp (default: 5 min).
            Set to ``0`` to disable replay protection.

    Returns:
        ``True`` if the signature is valid and the timestamp is recent.
    """
    # Replay protection — reject old deliveries
    if max_age_seconds > 0:
        try:
            ts = int(timestamp)
        except (ValueError, TypeError):
            return False
        if abs(time.time() - ts) > max_age_seconds:
            return False

    # Reconstruct the expected signature
    message = f"{timestamp}.{body.decode()}"
    expected = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
