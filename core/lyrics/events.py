from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.event_bus import EventBus


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

_EVENT_PREFIX = "lyrics."


class LyricEventBus:
    """Thin typed wrapper over the canonical event bus (single EventBus rule).

    All lyrics events flow through the wrapped :class:`EventBus` instance
    under the ``lyrics.*`` namespace; this class only adds the typed
    :class:`LyricDomainEvent` payload. It keeps no handler state of its own —
    ``subscribe``/``unsubscribe`` delegate to the canonical bus.
    """

    def __init__(self, bus: EventBus | None = None):
        self._bus = bus if bus is not None else EventBus()
        self._generation: int = 0

    def subscribe(self, event_type: str, handler: EventHandler):
        self._bus.on(f"{_EVENT_PREFIX}{event_type}", handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        self._bus.off(f"{_EVENT_PREFIX}{event_type}", handler)

    def emit(self, event_type: str, request_id: str = "", track_hash: str = "",
             source: str = "", status: str = "", trace_id: str = "",
             data: dict[str, Any] | None = None):
        self._generation += 1
        event = LyricDomainEvent(
            type=event_type, request_id=request_id, track_hash=track_hash,
            source=source, status=status, trace_id=trace_id,
            data=data or {}, generation=self._generation,
        )
        self._bus.publish(f"{_EVENT_PREFIX}{event_type}", event)

    def clear(self):
        """Drop all handlers registered in the lyrics namespace."""
        self._bus.clear_namespace(_EVENT_PREFIX)
