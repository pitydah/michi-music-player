"""SnapServerManager — manages snapserver lifecycle via QProcess."""
import shutil

from PySide6.QtCore import QObject, Signal, QProcess


SNAPSERVER_BIN = shutil.which("snapserver") or ""

DEFAULT_CONFIG = """\
[server]
tcp_port = {tcp}
control_port = {ctrl}
http_port = {http}
stream = pipe:///tmp/snapfifo?name=michi&codec=flac&sampleformat=44100:16:2
"""


class SnapServerManager(QObject):
    started = Signal()
    stopped = Signal()
    error_occurred = Signal(str)
    server_ready = Signal(int, int)  # tcp_port, control_port

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = None
        self._running = False
        self._tcp_port = 1704
        self._control_port = 1705
        self._http_port = 1780
        self._config_path = "/tmp/michi_snapserver.conf"
        self._last_error = ""

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def tcp_port(self) -> int:
        return self._tcp_port

    @property
    def control_port(self) -> int:
        return self._control_port

    @property
    def http_port(self) -> int:
        return self._http_port

    @property
    def last_error(self) -> str:
        return self._last_error

    def is_binary_available(self) -> bool:
        return bool(SNAPSERVER_BIN)

    def configure(self, tcp: int = 1704, ctrl: int = 1705, http: int = 1780):
        self._tcp_port = tcp
        self._control_port = ctrl
        self._http_port = http

    def start(self):
        if self._running:
            return
        if not SNAPSERVER_BIN:
            self._last_error = (
                "snapserver no encontrado. Instalalo con:\n"
                "  wget https://github.com/badaix/snapcast/releases\n"
                "  snap install snapcast  (si usas snap)\n"
                "O compila desde https://github.com/badaix/snapcast")
            self.error_occurred.emit(self._last_error)
            return

        cfg = self._write_config()
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.finished.connect(self._on_finished)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.start(SNAPSERVER_BIN, ["-c", cfg])

    def stop(self):
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.terminate()
            # finished signal already connected → _on_finished handles cleanup
        self._running = False
        if not self._process or self._process.state() == QProcess.NotRunning:
            self.stopped.emit()

    def _write_config(self) -> str:
        cfg = DEFAULT_CONFIG.format(
            tcp=self._tcp_port, ctrl=self._control_port,
            http=self._http_port)
        with open(self._config_path, "w") as f:
            f.write(cfg)
        return self._config_path

    def _on_finished(self, exit_code, exit_status):
        self._running = False
        if exit_status != QProcess.NormalExit or exit_code != 0:
            err = bytes(self._process.readAllStandardError()).decode(
                errors="replace") if self._process else ""
            self._last_error = (
                f"snapserver termino con codigo {exit_code}") + (
                f"\n{err}" if err else "")
            self.error_occurred.emit(self._last_error)
        self.stopped.emit()

    def _on_output(self):
        if self._process:
            data = bytes(self._process.readAllStandardOutput()).decode(
                errors="replace")
            if ("Server ready" in data or "listening" in data.lower()) and not self._running:
                self._running = True
                self.started.emit()
                self.server_ready.emit(
                    self._tcp_port, self._control_port)
