"""Queue snapshot section — canonical queue state from QueueService."""

from __future__ import annotations

from typing import Any


class QueueSectionProvider:
    section_key = "queue"

    def build(self, context) -> dict[str, Any]:
        queue = context.services.get("queue_service")
        if queue is None:
            return {
                "available": False,
                "reason": "queue_service_missing",
                "count": 0,
                "active": False,
            }
        try:
            if hasattr(queue, "get_state"):
                state = queue.get_state()
                if isinstance(state, dict):
                    items = state.get("items") or []
                    return {
                        "available": True,
                        "count": len(items),
                        "active": len(items) > 0,
                        "current_index": state.get("current_index", -1),
                        "repeat": state.get("repeat", "none"),
                        "shuffle": bool(state.get("shuffle", False)),
                        "context": state.get("context", ""),
                        "revision": int(state.get("revision", 0)),
                    }
            count = getattr(queue, "count", 0) or 0
            return {
                "available": True,
                "count": int(count),
                "active": int(count) > 0,
                "current_index": getattr(queue, "current_index", -1),
            }
        except Exception as exc:
            return {
                "available": False,
                "reason": "queue_readback_failed",
                "error": str(exc)[:200],
                "count": 0,
                "active": False,
            }
