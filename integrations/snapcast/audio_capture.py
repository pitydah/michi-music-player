"""AudioCaptureManager — creates a Pulse/PipeWire null sink for Snapcast."""
import shutil

from PySide6.QtCore import QObject, Signal, QProcess

PACTL_BIN = shutil.which("pactl") or ""
SINK_NAME = "michi_snapcast_sink"


class AudioCaptureManager(QObject):
    sink_ready = Signal(str)  # sink monitor name
    sink_removed = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sink_id = None
        self._loopback_id = None
        self._local_monitor = True
        self._last_error = ""

    @property
    def is_available(self) -> bool:
        return bool(PACTL_BIN)

    @property
    def last_error(self) -> str:
        return self._last_error

    def is_sink_active(self) -> bool:
        return self._sink_id is not None

    def create_sink(self):
        if not PACTL_BIN:
            self._last_error = (
                "pactl no encontrado. Se necesita PipeWire-Pulse o PulseAudio.\n"
                "Instala: sudo apt install pipewire-pulse")
            self.error_occurred.emit(self._last_error)
            return

        # Remove existing sink first
        self.remove_sink()

        proc = QProcess(self)
        proc.start(PACTL_BIN, [
            "load-module", "module-null-sink",
            f"sink_name={SINK_NAME}",
            "sink_properties=device.description=Michi_Multiroom"])
        proc.waitForFinished(3000)
        out = bytes(proc.readAllStandardOutput()).decode(errors="replace").strip()
        err = bytes(proc.readAllStandardError()).decode(errors="replace").strip()

        if err and "Failure" in err:
            self._last_error = f"Error al crear sink: {err}"
            self.error_occurred.emit(self._last_error)
            return
        if out.isdigit():
            self._sink_id = int(out)
        else:
            self._sink_id = 1  # assume success

        monitor = f"{SINK_NAME}.monitor"
        self.sink_ready.emit(monitor)

    def remove_sink(self):
        if not PACTL_BIN:
            return
        proc = QProcess(self)
        proc.start(PACTL_BIN, ["list", "short", "modules"])
        proc.waitForFinished(3000)
        out = bytes(proc.readAllStandardOutput()).decode(errors="replace")
        for line in out.splitlines():
            if SINK_NAME in line:
                parts = line.split()
                if parts:
                    QProcess.execute(PACTL_BIN,
                                     ["unload-module", parts[0]])
        self._sink_id = None
        self._loopback_id = None
        self.sink_removed.emit()

    def enable_local_monitor(self):
        if not PACTL_BIN or not self._sink_id:
            return
        if self._loopback_id:
            return
        proc = QProcess(self)
        proc.start(PACTL_BIN, [
            "load-module", "module-loopback",
            f"source={SINK_NAME}.monitor"])
        proc.waitForFinished(3000)
        out = bytes(proc.readAllStandardOutput()).decode(errors="replace").strip()
        if out.isdigit():
            self._loopback_id = int(out)
        self._local_monitor = True

    def disable_local_monitor(self):
        if self._loopback_id and PACTL_BIN:
            QProcess.execute(PACTL_BIN,
                             ["unload-module", str(self._loopback_id)])
        self._loopback_id = None
        self._local_monitor = False
