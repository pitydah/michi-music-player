"""WorkerManager — QThreadPool for offloading slow operations from the main thread."""
import logging

from PySide6.QtCore import QObject, QRunnable, Signal, QThreadPool, Slot, Qt


class _WorkerSignals(QObject):
    """Internal signals for QRunnable workers."""
    done = Signal(object)         # result (type varies by worker)
    error = Signal(str)           # error message


class _CoverLoaderWorker(QRunnable):
    """Load album covers in background thread."""

    def __init__(self, items, cover_size, existing_groups=None):
        super().__init__()
        self._signals = _WorkerSignals()
        self._items = items
        self._cover_size = cover_size
        self._existing = existing_groups

    def run(self):
        try:
            if self._items:
                from library.album_art import load_covers_for_albums
                result = load_covers_for_albums(self._items, self._cover_size)
                self._signals.done.emit(result)
            else:
                self._signals.done.emit([])
        except Exception as e:
            self._signals.error.emit(str(e))


class _IdentifyWorker(QRunnable):
    """Run capture + identify in background thread."""

    def __init__(self, capture_service, recognizer):
        super().__init__()
        self._signals = _WorkerSignals()
        self._capture = capture_service
        self._recognizer = recognizer

    def run(self):
        try:
            audio_bytes = self._capture.capture_once()
            if audio_bytes and self._recognizer:
                result = self._recognizer.identify(audio_bytes)
                self._signals.done.emit(result)
            else:
                self._signals.done.emit(None)
        except Exception as e:
            self._signals.error.emit(str(e))


class _TaskWorker(QRunnable):
    """Run an arbitrary function in background. No QObject children (thread-safe)."""

    def __init__(self, fn, done_callback=None, error_callback=None, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._done_cb = done_callback
        self._error_cb = error_callback
        self.setAutoDelete(True)

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            if self._done_cb:
                self._done_cb(result)
        except Exception as e:
            if self._error_cb:
                self._error_cb(str(e))


class WorkerManager(QObject):
    """Thread pool manager for slow operations. Workers emit results via signals.

    Usage:
        self._workers = WorkerManager(self)
        self._workers.covers_ready.connect(self._on_covers_ready)
        self._workers.identify_done.connect(self._on_identify_done)
        self._workers.load_covers(items, cover_size)
    """

    covers_ready = Signal(list)           # list[dict] album groups with loaded covers
    identify_done = Signal(object)        # DetectedTrack | None
    identify_error = Signal(str)          # Error message
    task_done = Signal(str, object)       # task_id, result
    task_error = Signal(str, str)         # task_id, error

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(4)
        self._log = logging.getLogger("michi.workers")

    def load_covers(self, items, cover_size):
        """Load album covers in background. Emits covers_ready."""
        worker = _CoverLoaderWorker(items, cover_size)
        worker._signals.done.connect(self._on_covers_done, type=Qt.ConnectionType.QueuedConnection)
        worker._signals.error.connect(lambda e: self._log.warning("Cover load failed: %s", e))
        self._pool.start(worker)

    @Slot(object)
    def _on_covers_done(self, result):
        if isinstance(result, list):
            self.covers_ready.emit(result)
        else:
            self._log.warning("Cover loader returned invalid result: %r", type(result))

    def identify(self, capture_service, recognizer):
        """Run capture + identify in background thread."""
        worker = _IdentifyWorker(capture_service, recognizer)
        worker._signals.done.connect(self._on_identify_done, type=Qt.ConnectionType.QueuedConnection)
        worker._signals.error.connect(self.identify_error.emit, type=Qt.ConnectionType.QueuedConnection)
        self._pool.start(worker)

    @Slot(object)
    def _on_identify_done(self, result):
        self.identify_done.emit(result)

    def run_task(self, task_id: str, fn, *args, on_done=None, on_error=None, **kwargs):
        """Run fn in background thread. Callbacks invoked on main thread via QTimer."""
        from PySide6.QtCore import QTimer

        def _done_wrapper(result):
            self.task_done.emit(task_id, result)
            if on_done:
                QTimer.singleShot(0, lambda: on_done(result))

        def _error_wrapper(error):
            self.task_error.emit(task_id, error)
            if on_error:
                QTimer.singleShot(0, lambda: on_error(error))

        worker = _TaskWorker(fn, done_callback=_done_wrapper,
                             error_callback=_error_wrapper)
        worker._args = args
        worker._kwargs = kwargs
        self._pool.start(worker)

    def pending(self) -> int:
        return self._pool.activeThreadCount()

    def shutdown(self, timeout_ms: int = 2000):
        """Wait for pending tasks and clear the pool."""
        self._pool.clear()
        if not self._pool.waitForDone(timeout_ms):
            self._log.warning("WorkerManager shutdown: %d tasks still active after %dms",
                              self._pool.activeThreadCount(), timeout_ms)
