"""EventBus — lightweight pub-sub event bus for cross-service communication."""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger("michi.event_bus")


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event: str, handler: Callable):
        self._handlers.setdefault(event, []).append(handler)

    def off(self, event: str, handler: Callable):
        handlers = self._handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event: str, *args, **kwargs):
        for h in self._handlers.get(event, []):
            try:
                h(*args, **kwargs)
            except Exception as e:
                logger.error("EventBus handler error for %s: %s", event, e)

    def clear(self):
        self._handlers.clear()
