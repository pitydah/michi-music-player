"""Qt compatibility wrapper around the canonical vinyl recorder.

Historically this module contained a second GStreamer recording engine. Keeping
it as a facade removes duplicate capture state while preserving its public Qt
signals for any future consumers.
"""

from __future__ import annotations

import os
import tempfile

from PySide6.QtCore import QObject, Signal

from .vinyl_recorder_service import VinylRecorderService


class VinylCaptureService(QObject):
    recording_started = Signal(str)
    recording_progress = Signal(float)
    recording_finished = Signal(str)
    recording_error = Signal(str)
    recording_paused = Signal()
    recording_resumed = Signal()

    def __init__(self, parent=None, recorder: VinylRecorderService | None = None):
        super().__init__(parent)
        self._recorder = recorder or VinylRecorderService()
        self._filepath = ""
        self._sample_rate = 96000
        self._bit_depth = 24
        self._channels = 2

    @property
    def is_recording(self) -> bool:
        return self._recorder.is_recording

    @property
    def is_paused(self) -> bool:
        return self._recorder.is_paused

    def set_format(
        self, sample_rate: int = 96000, bit_depth: int = 24, channels: int = 2
    ) -> None:
        self._sample_rate = int(sample_rate)
        self._bit_depth = int(bit_depth)
        self._channels = int(channels)

    def start_recording(self, filepath: str | None = None) -> bool:
        if self.is_recording:
            return False
        if not filepath:
            fd, filepath = tempfile.mkstemp(suffix=".wav", prefix="vinyl_")
            os.close(fd)
        device = self._recorder.get_recommended_device()
        if device is None:
            self.recording_error.emit("No hay dispositivos de entrada disponibles")
            return False
        result = self._recorder.start_recording(
            device=device,
            output_path=filepath,
            format="wav",
            sample_rate=self._sample_rate,
            bit_depth=self._bit_depth,
            channels=self._channels,
        )
        if not result.get("success"):
            self.recording_error.emit(str(result.get("error", "Error de captura")))
            return False
        self._filepath = filepath
        self.recording_started.emit(filepath)
        return True

    def stop_recording(self) -> str:
        if not self.is_recording:
            return self._filepath
        result = self._recorder.stop_recording()
        if not result.get("success"):
            self.recording_error.emit(str(result.get("error", "Error al detener")))
            return self._filepath
        self._filepath = str(result.get("output_path", self._filepath))
        self.recording_finished.emit(self._filepath)
        return self._filepath

    def list_devices(self) -> list[dict]:
        return [device.to_dict() for device in self._recorder.detect_devices()]

    def get_level(self) -> float:
        status = self._recorder.get_recording_status()
        peak_dbfs = float(status.get("level", -60.0))
        return max(0.0, min(1.0, (peak_dbfs + 60.0) / 60.0))

    def get_recording_seconds(self) -> float:
        return float(self._recorder.get_recording_status().get("duration", 0.0))

    def pause_recording(self) -> bool:
        paused = self._recorder.pause_recording()
        if paused:
            self.recording_paused.emit()
        return paused

    def resume_recording(self) -> bool:
        resumed = self._recorder.resume_recording()
        if resumed:
            self.recording_resumed.emit()
        return resumed

    def cleanup(self) -> None:
        self._recorder.cleanup()
