from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.event_bus import EventBus as CoreEventBus


@dataclass
class DomainEvent:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    generation: int = 0


EventHandler = Callable[[DomainEvent], None]

_EVENT_PREFIX = "radio."


class EventBus:
    """Thin typed wrapper over the canonical event bus (single EventBus rule).

    All radio events flow through the wrapped :class:`core.event_bus.EventBus`
    instance under the ``radio.*`` namespace; this class only adds the typed
    :class:`DomainEvent` payload and a generation counter. It keeps no handler
    state of its own — ``subscribe``/``unsubscribe`` delegate to the canonical
    bus.
    """

    def __init__(self, bus: CoreEventBus | None = None):
        self._bus = bus if bus is not None else CoreEventBus()
        self._generation: int = 0

    def next_generation(self) -> int:
        self._generation += 1
        return self._generation

    def subscribe(self, event_type: str, handler: EventHandler):
        self._bus.on(f"{_EVENT_PREFIX}{event_type}", handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        self._bus.off(f"{_EVENT_PREFIX}{event_type}", handler)

    def emit(self, event_type: str, data: dict[str, Any] | None = None,
             generation: int | None = None):
        if generation is None:
            self._generation += 1
            generation = self._generation
        event = DomainEvent(type=event_type, data=data or {},
                            generation=generation)
        self._bus.publish(f"{_EVENT_PREFIX}{event_type}", event)

    def clear(self):
        """Drop all handlers registered in the radio namespace."""
        self._bus.clear_namespace(_EVENT_PREFIX)
