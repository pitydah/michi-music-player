from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class DomainEvent:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    generation: int = 0


EventHandler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}
        self._generation: int = 0

    def next_generation(self) -> int:
        self._generation += 1
        return self._generation

    def subscribe(self, event_type: str, handler: EventHandler):
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, event_type: str, data: dict[str, Any] | None = None, generation: int | None = None):
        if generation is None:
            generation = self._generation
        event = DomainEvent(type=event_type, data=data or {}, generation=generation)
        for handler in self._handlers.get(event_type, []):
            handler(event)

    def clear(self):
        self._handlers.clear()
