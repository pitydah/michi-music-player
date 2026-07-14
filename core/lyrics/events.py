from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class LyricDomainEvent:
    type: str
    request_id: str = ""
    track_hash: str = ""
    source: str = ""
    status: str = ""
    trace_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    generation: int = 0


EventHandler = Callable[[LyricDomainEvent], None]


class LyricEventBus:
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}
        self._generation: int = 0

    def subscribe(self, event_type: str, handler: EventHandler):
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event_type: str, request_id: str = "", track_hash: str = "",
             source: str = "", status: str = "", trace_id: str = "",
             data: dict[str, Any] | None = None):
        self._generation += 1
        event = LyricDomainEvent(
            type=event_type, request_id=request_id, track_hash=track_hash,
            source=source, status=status, trace_id=trace_id,
            data=data or {}, generation=self._generation,
        )
        for handler in self._handlers.get(event_type, []):
            handler(event)

    def clear(self):
        self._handlers.clear()
