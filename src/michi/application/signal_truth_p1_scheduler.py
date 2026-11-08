"""AP2-F11 A48: bounded UI owner dispatch coalescing policy, NOT an RT queue.

Input must already be delivered to a safe worker/Qt owner executor. Critical
lifecycle events are never silently dropped: overflow triggers resync-required
instead. This is a candidate adapter, not a replacement for Qt signals.
"""

from __future__ import annotations

from dataclasses import dataclass

_CRITICAL = frozenset(
    {"RETIRE", "HOST_LOSS", "CONTRADICTION", "EXECUTION_CHANGED", "RELEASE"}
)


@dataclass(frozen=True, slots=True)
class UiNotice:
    execution_id: str
    epoch: int
    sequence: int
    kind: str

    def __post_init__(self) -> None:
        if not self.execution_id or type(self.epoch) is not int or self.epoch <= 0:
            raise ValueError("unscoped UI notice")
        if type(self.sequence) is not int or self.sequence <= 0:
            raise ValueError("invalid notice sequence")
        if self.kind not in _CRITICAL | {"METRIC_UPDATE", "FRAME_UPDATE"}:
            raise ValueError("unsupported UI notice")


class UiNoticeCoalescer:
    """Non-RT bounded queue; caller drains on Qt owner thread.

    Preserve critical events; collapse only observational refreshes for same
    execution. If saturated, force full resync rather than falsify chronology.
    """

    def __init__(self, *, capacity: int = 64) -> None:
        if type(capacity) is not int or not 8 <= capacity <= 1024:
            raise ValueError("invalid UI event budget")
        self.capacity = capacity
        self._events: list[UiNotice] = []
        self._scope: tuple[str, int] | None = None
        self._last: int = 0
        self.resync_required = False

    def begin(self, execution_id: str, epoch: int) -> None:
        if not execution_id or type(epoch) is not int or epoch <= 0:
            raise ValueError("invalid UI execution")
        self._scope = (execution_id, epoch)
        self._events.clear()
        self._last = 0
        self.resync_required = False

    def submit(self, event: UiNotice) -> bool:
        if self._scope != (event.execution_id, event.epoch):
            return False
        if event.sequence <= self._last:
            return False
        self._last = event.sequence
        if event.kind not in _CRITICAL:
            self._events = [old for old in self._events if old.kind in _CRITICAL]
        if len(self._events) >= self.capacity:
            self.resync_required = True
            self._events.clear()
            return False
        self._events.append(event)
        return True

    def drain(self) -> tuple[UiNotice, ...]:
        if self.resync_required:
            # Caller must read one new coherent canonical recorder snapshot.
            raise RuntimeError("ST_P1_QT_FULL_RESNAPSHOT_REQUIRED")
        items = tuple(self._events)
        self._events.clear()
        return items
