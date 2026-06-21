"""AudioCaptureService — capture audio from system outputs for recognition.

Captures audio from:
    - PulseAudio/PipeWire monitor source (auto-detect)
    - Default input device

Produces raw PCM samples (S16LE, mono, 22050Hz) for fingerprinting.
"""
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("astra.recognition.capture")

SAMPLE_RATE = 22050
CHANNELS = 1
SAMPLE_WIDTH = 2      # 16-bit
CHUNK_MS = 4000       # 4 seconds per capture
CHUNK_BYTES = SAMPLE_RATE * SAMPLE_WIDTH * CHUNK_MS // 1000


class AudioCaptureService(QObject):
    """Captures audio samples from system audio for recognition providers."""

    sample_ready = Signal(bytes)             # raw PCM bytes
    capture_started = Signal()
    capture_stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active = False
        self._pya_available = self._check_pyaudio()

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def is_available(self) -> bool:
        return self._pya_available

    def start(self):
        """Start capturing audio from monitor source."""
        if self._active:
            return
        if not self._pya_available:
            self.error_occurred.emit("PyAudio not available")
            return

        self._active = True
        self.capture_started.emit()
        logger.info("Audio capture started")

    def stop(self):
        """Stop capturing."""
        self._active = False
        self.capture_stopped.emit()
        logger.info("Audio capture stopped")

    def capture_once(self) -> bytes | None:
        """Capture a single chunk of audio (4 seconds) from the monitor.

        Returns raw PCM bytes (S16LE, mono, 22050Hz).
        """
        if not self._pya_available:
            return None
        return self._capture_chunk()

    def _capture_chunk(self) -> bytes | None:
        try:
            import pyaudio

            p = pyaudio.PyAudio()

            # Find the monitor/sink source
            device_index = self._find_monitor_device(p)
            if device_index is None:
                logger.warning("No monitor device found for capture")
                p.terminate()
                return None

            stream = p.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
            )

            frames = []
            total_samples = CHUNK_BYTES // SAMPLE_WIDTH
            remaining = total_samples

            while remaining > 0:
                data = stream.read(min(1024, remaining), exception_on_overflow=False)
                frames.append(data)
                remaining -= len(data) // SAMPLE_WIDTH

            stream.stop_stream()
            stream.close()
            p.terminate()

            return b"".join(frames)
        except Exception as e:
            logger.debug(f"Capture failed: {e}")
            return None

    @staticmethod
    def _find_monitor_device(pyaudio_instance) -> int | None:
        """Find the PulseAudio/PipeWire monitor source device index."""
        count = pyaudio_instance.get_device_count()
        for i in range(count):
            info = pyaudio_instance.get_device_info_by_index(i)
            name = info.get("name", "").lower()
            # Match monitor/sink devices
            if any(kw in name for kw in ("monitor", "output", "sink", "loopback")) and info.get("maxInputChannels", 0) > 0:
                return i
        # Fallback: find default input
        try:
            default = pyaudio_instance.get_default_input_device_info()
            return default.get("index")
        except Exception:
            pass
        return None

    @staticmethod
    def _check_pyaudio() -> bool:
        import importlib.util
        return importlib.util.find_spec("pyaudio") is not None
