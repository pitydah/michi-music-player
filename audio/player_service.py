"""Player Service — single facade between UI and GStreamer engine."""

from PySide6.QtCore import QObject, Signal, QTimer
from audio.player import GStreamerEngine, PlaybackState


class PlayerService(QObject):
    # ── Signals (relayed from engine) ──
    track_changed = Signal(str, str)    # title, artist
    state_changed = Signal(str)         # playing/paused/stopped
    position_changed = Signal(float)    # seconds
    duration_changed = Signal(float)    # seconds
    error_occurred = Signal(str)
    queue_changed = Signal(list)        # list[dict]
    finished = Signal()

    def __init__(self, engine: GStreamerEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._retry_url: str | None = None
        self._retry_title: str = ""
        self._retry_artist: str = ""
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._do_retry)

        # Relay engine signals
        self._engine.position_changed.connect(
            lambda s: self.position_changed.emit(s))
        self._engine.duration_changed.connect(
            lambda s: self.duration_changed.emit(s))
        self._engine.state_changed.connect(self._on_state)
        self._engine.queue_changed.connect(
            lambda q: self.queue_changed.emit(q))
        self._engine.finished.connect(
            lambda: self.finished.emit())

        # Streaming retry — intercept errors
        self._engine.error_occurred.connect(self._on_error)

    def _on_state(self, state: PlaybackState):
        s_map = {PlaybackState.PLAYING: "playing",
                 PlaybackState.PAUSED: "paused",
                 PlaybackState.STOPPED: "stopped"}
        s = s_map.get(state, "stopped")
        if s == "playing":
            self._retry_url = None
        self.state_changed.emit(s)

    def _on_error(self, msg: str):
        if self._retry_url:
            self._retry_timer.start(2000)
        else:
            self.error_occurred.emit(msg)

    def _do_retry(self):
        url = self._retry_url
        title = self._retry_title
        artist = self._retry_artist
        self._retry_url = None
        if url:
            self._engine.play_url(url)
            if title:
                self.track_changed.emit(title, artist)
            import logging
            logging.getLogger("michi.service").info(
                "Retrying stream: %s", url)

    # ── Core playback ──

    def play(self, filepath: str, title: str = "", artist: str = ""):
        self._retry_url = None
        self._engine.play(filepath)
        if title:
            self.track_changed.emit(title, artist)

    def pause(self):
        self._engine.pause()

    def resume(self):
        self._engine.resume()

    def play_or_resume(self):
        from audio.player import PlaybackState
        current = self._engine.current
        state = getattr(self._engine, '_state', None)
        if current:
            if state in (PlaybackState.PAUSED, PlaybackState.STOPPED):
                self._engine.resume()
            else:
                self._engine.play(current)
        else:
            self.error_occurred.emit("No hay archivo para reproducir")

    def toggle(self):
        self._engine.toggle()

    def stop(self):
        self._engine.stop()

    def seek(self, seconds: float):
        self._engine.seek(seconds)

    def set_volume(self, vol: int):
        self._engine.set_volume(vol)

    # ── Queue ──

    def play_next(self):
        self._engine.play_next()

    def play_prev(self):
        self._engine.play_prev()

    def enqueue(self, paths: list, play_now: bool = True):
        self._retry_url = None
        clean: list[str] = []
        for p in paths:
            if not p:
                continue
            if isinstance(p, str):
                clean.append(p)
        if not clean:
            self.error_occurred.emit("No hay archivos válidos para reproducir")
            return
        self._engine.enqueue(clean, play_now)

    def play_queue(self, filepaths: list[str], start_index: int = 0):
        """Replace the queue with given tracks and start playing from index."""
        self._retry_url = None
        self._engine.set_queue(filepaths, start_index)

    def clear_queue(self):
        self._engine.clear_queue()

    def get_queue(self) -> list[dict]:
        return self._engine.get_queue()

    def reorder_queue(self, filepaths: list[str]):
        self._engine.reorder_queue(filepaths)

    # ── Modes ──

    def toggle_shuffle(self):
        self._engine.toggle_shuffle()

    def toggle_repeat(self) -> str:
        """Toggle repeat. Returns new mode: 'off', 'one', 'all'."""
        return self._engine.toggle_repeat()

    # ── Streaming ──

    def play_url(self, url: str, title: str = "", artist: str = ""):
        self._retry_url = url
        self._retry_title = title
        self._retry_artist = artist
        self._engine.play_url(url)
        if title:
            self.track_changed.emit(title, artist)

    # ── Output ──
    # Use set_output_device_id() for local output, set_transmit_device() for network transmit

    # ── Audio profile / DAC ──

    def set_audio_profile(self, profile: str):
        if hasattr(self._engine, 'set_audio_profile'):
            self._engine.set_audio_profile(profile)

    def set_output_device_id(self, device_id: str):
        if hasattr(self._engine, 'set_output_device_id'):
            self._engine.set_output_device_id(device_id)

    def get_output_device_id(self) -> str:
        if hasattr(self._engine, 'get_output_device_id'):
            return self._engine.get_output_device_id()
        return "auto"

    def get_audio_devices(self):
        from audio.output_device_manager import list_devices
        return list_devices()

    def refresh_audio_devices(self):
        return self.get_audio_devices()

    def get_audio_diagnostics(self):
        if hasattr(self._engine, 'get_audio_diagnostics'):
            return self._engine.get_audio_diagnostics()
        return None

    def test_output_device(self, device_id: str) -> tuple:
        return True, "OK"

    def set_dsd_mode(self, mode: str):
        if hasattr(self._engine, 'set_dsd_mode'):
            self._engine.set_dsd_mode(mode)

    def set_gapless_enabled(self, enabled: bool):
        if hasattr(self._engine, 'set_gapless_enabled'):
            self._engine.set_gapless_enabled(enabled)

    def set_replaygain_mode(self, mode: str):
        if hasattr(self._engine, 'set_replaygain_mode'):
            self._engine.set_replaygain_mode(mode)

    # ── Transmit ──

    def set_transmit_device(self, device):
        if hasattr(self._engine, 'set_transmit_device'):
            self._engine.set_transmit_device(device)

    def get_transmit_device(self):
        if hasattr(self._engine, 'get_transmit_device'):
            return self._engine.get_transmit_device()
        return None

    # ── EQ ──

    def set_eq_graphic(self, bands):
        if hasattr(self._engine, 'set_eq_graphic'):
            self._engine.set_eq_graphic(bands)

    def set_eq_parametric(self, bands):
        if hasattr(self._engine, 'set_eq_parametric'):
            self._engine.set_eq_parametric(bands)

    def set_eq_bypass(self, bypass: bool):
        if hasattr(self._engine, 'set_eq_bypass'):
            self._engine.set_eq_bypass(bypass)

    def set_eq_preamp(self, db: float):
        if hasattr(self._engine, 'set_eq_preamp'):
            self._engine.set_eq_preamp(db)

    def set_spectrum_enabled(self, enabled: bool):
        if hasattr(self._engine, 'set_spectrum_enabled'):
            self._engine.set_spectrum_enabled(enabled)

    # ── Accessors ──

    @property
    def state(self):
        return self._engine.state

    @property
    def current(self) -> str:
        """Current playing filepath or URL."""
        return self._engine.current if hasattr(self._engine, 'current') else ""

    @property
    def engine(self) -> GStreamerEngine:
        return self._engine
