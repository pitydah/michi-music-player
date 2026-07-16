"""EventBus — lightweight pub-sub event bus for cross-service communication."""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger("michi.event_bus")


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._active = True

    def subscribe(self, event: str, handler: Callable):
        self.on(event, handler)

    def unsubscribe(self, event: str, handler: Callable):
        self.off(event, handler)

    def publish(self, event: str, *args, **kwargs):
        self.emit(event, *args, **kwargs)

    def on(self, event: str, handler: Callable):
        self._handlers.setdefault(event, []).append(handler)

    def off(self, event: str, handler: Callable):
        handlers = self._handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: str, *args, **kwargs):
        if not self._active:
            return
        for h in self._handlers.get(event, []):
            try:
                h(*args, **kwargs)
            except Exception as e:
                logger.error("EventBus handler error for %s: %s", event, e)

    def clear(self):
        self._handlers.clear()

    def health(self) -> dict:
        return {"active": self._active, "events": len(self._handlers),
                "total_handlers": sum(len(v) for v in self._handlers.values())}

    def shutdown(self):
        self._active = False
        self._handlers.clear()
