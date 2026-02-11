"""Webhook dispatcher — public API re-export."""

from __future__ import annotations

from webmacs_backend.services import build_payload, dispatch_event

__all__ = ["build_payload", "dispatch_event"]
