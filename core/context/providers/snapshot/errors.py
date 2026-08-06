"""Errors snapshot section — recent operational errors from the context store."""

from __future__ import annotations

from typing import Any

from core.context.context_events import AppEvent


class ErrorsSectionProvider:
    section_key = "errors"

    def build(self, context) -> dict[str, Any]:
        from core.context import context_repository as repo
        try:
            events = repo.recent_events(limit=50)
        except Exception as exc:
            return {
                "available": False,
                "reason": "repository_unavailable",
                "error": str(exc)[:200],
                "errors": [],
                "count": 0,
            }
        errors = [
            ev for ev in events
            if ev.get("event_type") == AppEvent.CONTEXT_ERROR_RECORDED
        ][:10]
        return {
            "available": True,
            "count": len(errors),
            "errors": [
                {
                    "area": (ev.get("payload") or {}).get("area", ""),
                    "code": (ev.get("payload") or {}).get("code", ""),
                    "message": (ev.get("payload") or {}).get("message", ""),
                    "recorded_at": ev.get("recorded_at", 0),
                }
                for ev in errors
            ],
        }
