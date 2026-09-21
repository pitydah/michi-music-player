"""Small Qt owner-thread completion seam for bounded blocking work."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot


class _Call(QRunnable):
    def __init__(self, work: Callable[[], object], completed: Callable) -> None:
        super().__init__()
        self._work = work
        self._completed = completed

    def run(self) -> None:
        try:
            value = self._work()
            error = None
        except Exception as exc:  # noqa: BLE001 - worker isolation boundary
            value = None
            error = exc
        self._completed(value, error)


class QtAsyncCallExecutor(QObject):
    """Run work in Qt's pool and deliver completion on this object's thread."""

    _completed = Signal(object, object, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._completed.connect(self._deliver, Qt.QueuedConnection)

    def submit(self, work: Callable[[], object], completed: Callable) -> None:
        def emit_completion(value, error) -> None:
            try:
                self._completed.emit(completed, value, error)
            except RuntimeError:
                return

        QThreadPool.globalInstance().start(_Call(work, emit_completion))

    @Slot(object, object, object)
    def _deliver(self, completed: Callable, value, error) -> None:
        completed(value, error)
