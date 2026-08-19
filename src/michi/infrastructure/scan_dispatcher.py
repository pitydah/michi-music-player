"""Owner-thread scan dispatcher (M6-PRODUCTION-INTEGRATION-AND-ASYNC-CORRECTION).

The ThreadScanRunner emits progress/done from the worker thread; bootstrap
connects the relay signals to this QObject with an EXPLICIT
``Qt.QueuedConnection``, so the slots run on the owner (GUI) thread and
delegate to the application service. LibraryService itself stays Qt-free.

``shutdown()`` drops late callbacks: a worker that finishes after the app
graph has shut down can never mutate LibraryState or reach the bridge.
"""

from PySide6.QtCore import QObject, Slot

from michi.application.library_service import LibraryService


class LibraryScanDispatcher(QObject):
    """Forwards relay signals to LibraryService on the owner thread."""

    def __init__(self, service: LibraryService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._closed = False

    def shutdown(self) -> None:
        """Drop all late callbacks (called after the runner is frozen)."""
        self._closed = True

    @Slot(int, object)
    def on_progress(self, generation, progress) -> None:
        if self._closed:
            return
        self._service.handle_scan_progress(generation, progress)

    @Slot(int, object, object)
    def on_done(self, generation, result, error) -> None:
        if self._closed:
            return
        self._service.handle_scan_done(generation, result, error)
