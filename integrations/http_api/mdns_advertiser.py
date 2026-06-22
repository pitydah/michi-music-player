"""mDNS advertiser — announces Michi API via avahi-publish-service."""
import shutil

from PySide6.QtCore import QObject, Signal, QProcess

AVAHI_PUBLISH = shutil.which("avahi-publish-service") or ""


class MDNSAdvertiser(QObject):
    started = Signal()
    stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = None
        self._running = False
        self._port = 8124

    @property
    def is_available(self) -> bool:
        return bool(AVAHI_PUBLISH)

    @property
    def is_running(self) -> bool:
        return self._running

    def configure(self, port: int = 8124):
        self._port = port

    def start(self):
        if self._running or not AVAHI_PUBLISH:
            return
        self._process = QProcess(self)
        self._process.finished.connect(self._on_finished)
        self._process.readyReadStandardError.connect(self._on_error)
        self._process.start(AVAHI_PUBLISH, [
            "Michi Music Player",
            "_michi-http._tcp",
            str(self._port),
        ])
        self._running = True
        self.started.emit()

    def stop(self):
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.terminate()
            if not self._process.waitForFinished(2000):
                self._process.kill()
        self._running = False
        self.stopped.emit()

    def _on_finished(self, exit_code, exit_status):
        self._running = False
        self.stopped.emit()

    def _on_error(self):
        if self._process:
            err = bytes(self._process.readAllStandardError()).decode(
                errors="replace")
            if err.strip():
                self.error_occurred.emit(f"mDNS: {err.strip()}")
