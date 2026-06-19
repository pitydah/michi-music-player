"""Player Service — controller layer between UI and GStreamer engine."""

from PySide6.QtCore import QObject, Signal
from audio.player import GStreamerEngine, PlaybackState


class PlayerService(QObject):
    track_changed = Signal(str, str)    # title, artist
    state_changed = Signal(str)         # playing/paused/stopped
    position_changed = Signal(float)    # seconds
    duration_changed = Signal(float)    # seconds
    error_occurred = Signal(str)

    def __init__(self, engine: GStreamerEngine, parent=None):
        super().__init__(parent)
        self._engine = engine

        self._engine.position_changed.connect(
            lambda s: self.position_changed.emit(s))
        self._engine.duration_changed.connect(
            lambda s: self.duration_changed.emit(s))
        self._engine.state_changed.connect(self._on_state)
        self._engine.error_occurred.connect(
            lambda m: self.error_occurred.emit(m))

    def _on_state(self, state: PlaybackState):
        s_map = {PlaybackState.PLAYING: "playing",
                 PlaybackState.PAUSED: "paused",
                 PlaybackState.STOPPED: "stopped"}
        self.state_changed.emit(s_map.get(state, "stopped"))

    def play(self, filepath: str, title: str = "", artist: str = ""):
        self._engine.play(filepath)
        if title:
            self.track_changed.emit(title, artist)

    def toggle(self):
        self._engine.toggle()

    def stop(self):
        self._engine.stop()

    def seek(self, seconds: float):
        self._engine.seek(seconds)

    def set_volume(self, vol: int):
        self._engine.set_volume(vol)

    def play_next(self):
        self._engine.play_next()

    def play_prev(self):
        self._engine.play_prev()

    def enqueue(self, paths: list, play_now: bool = True):
        self._engine.enqueue(paths, play_now)

    def get_engine(self) -> GStreamerEngine:
        return self._engine
