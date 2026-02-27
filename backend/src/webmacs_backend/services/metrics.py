"""Lightweight process-local metrics for instrumentation.

This module provides simple counters that are safe for the single-process
async worker used in tests and small deployments. Metrics are exposed as a
snapshot dictionary for scraping or health checks.
"""
from __future__ import annotations

import threading
from typing import Dict

_lock = threading.Lock()
_METRICS: Dict[str, int] = {
    "ingest_accepted_total": 0,
    "ingest_rejected_total": 0,
    "ingest_errors_total": 0,
    "webhook_dispatches": 0,
    "ws_broadcasts": 0,
}


def incr(name: str, amount: int = 1) -> None:
    """Increment a named counter by *amount*. Creates the counter if missing."""
    with _lock:
        _METRICS[name] = _METRICS.get(name, 0) + int(amount)


def snapshot() -> Dict[str, int]:
    """Return a shallow copy of current metrics."""
    with _lock:
        return dict(_METRICS)


def reset() -> None:
    """Reset all known counters to zero (useful for tests)."""
    with _lock:
        for k in list(_METRICS.keys()):
            _METRICS[k] = 0
