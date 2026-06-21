"""LocalMediaServerController — lifecycle management for local HTTP file server."""
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("astra.local_media.controller")


class LocalMediaServerController(QObject):
    """Manages the LocalMediaServer lifecycle for streaming local files to HA."""

    server_started = Signal(int)           # port
    server_stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self._win = window
        self._port = 8125
        self._server = None

    @property
    def is_running(self) -> bool:
        server = self._get_server()
        return server is not None and server.is_running

    def start(self, port: int = 8125):
        server = self._get_server()
        if not server:
            self.error_occurred.emit("LocalMediaServer not initialized")
            return
        if server.is_running:
            return

        server.configure(port)
        server.start()
        self.server_started.emit(port)

    def stop(self):
        server = self._get_server()
        if server and server.is_running:
            server.stop()
            self.server_stopped.emit()

    def register_file(self, filepath: str) -> str:
        """Register a local file and return its streaming URL."""
        server = self._get_server()
        if not server:
            raise ValueError("LocalMediaServer not initialized")
        if not server.is_running:
            self.start(self._port)
        return server.register_file(filepath)

    def _get_server(self):
        if self._server is None:
            self._server = getattr(self._win, '_local_media', None)
        return self._server
