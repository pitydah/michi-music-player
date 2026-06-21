"""DSD Controller — manages appsrc-based DFF playback with backpressure."""
import contextlib
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("astra.dsd")


class DsdController(QObject):
    """Controls DFF (non-DST) playback via appsrc with need-data/enough-data."""

    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, filepath: str, appsrc, parent=None):
        super().__init__(parent)
        self._filepath = filepath
        self._appsrc = appsrc
        self._file_handle = None
        self._data_offset = 0
        self._data_size = 0
        self._running = False
        self._cancelled = False
        self._chunk_size = 65536  # 64KB

    def start(self):
        """Open DFF file, parse header, configure appsrc."""
        try:
            import struct
            self._file_handle = open(self._filepath, "rb")  # noqa: SIM115

            # Read DFF header
            header = self._file_handle.read(12)
            if header[:4] != b"FRM8":
                self.error_occurred.emit("Formato DFF no valido")
                return

            # Find DSD chunk
            self._file_handle.seek(12)
            while True:
                ck_id = self._file_handle.read(4)
                ck_size_bytes = self._file_handle.read(8)
                if len(ck_id) < 4 or len(ck_size_bytes) < 8:
                    break
                ck_size = struct.unpack(">Q", ck_size_bytes)[0]
                if ck_id == b"DSD ":
                    self._data_offset = self._file_handle.tell()
                    self._data_size = ck_size
                    break
                # DST check
                if ck_id == b"DST " or ck_id == b"DST\x20":
                    self.error_occurred.emit(
                        "DFF con compresion DST no soportado")
                    return
                self._file_handle.seek(ck_size, 1)

            if self._data_offset == 0:
                self.error_occurred.emit(
                    "No se encontro el bloque DSD en el DFF")
                return

            self._file_handle.seek(self._data_offset)

            # Configure appsrc
            self._appsrc.set_property("format", Gst.Format.TIME)
            self._appsrc.set_property("block", True)
            self._appsrc.set_property("max-bytes", self._chunk_size)
            self._appsrc.connect("need-data", self._on_need_data)
            self._appsrc.connect("enough-data", self._on_enough_data)

            self._running = True
            self._push_chunk()

        except (OSError, struct.error) as e:
            self.error_occurred.emit(str(e))
            self.stop()

    def _push_chunk(self):
        if not self._running or self._cancelled:
            return
        try:
            remaining = self._data_size - (
                self._file_handle.tell() - self._data_offset)
            if remaining <= 0:
                self._appsrc.emit("end-of-stream", 0)
                self.finished.emit()
                return
            chunk = self._file_handle.read(
                min(self._chunk_size, remaining))
            if not chunk:
                self._appsrc.emit("end-of-stream", 0)
                self.finished.emit()
                return
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # noqa: E402
            buf = Gst.Buffer.new_wrapped(chunk)
            self._appsrc.emit("push-buffer", buf)
        except (OSError, Exception) as e:
            self.error_occurred.emit(str(e))

    def _on_need_data(self, appsrc, length):
        if self._cancelled:
            return
        self._push_chunk()

    def _on_enough_data(self, appsrc):
        pass  # Backpressure — pause pushing

    def stop(self):
        self._cancelled = True
        self._running = False
        if self._file_handle:
            with contextlib.suppress(OSError):
                self._file_handle.close()
            self._file_handle = None

    def cancel(self):
        self.stop()


# Delayed Gst import to avoid issues at module load
import gi  # noqa: E402
gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402
