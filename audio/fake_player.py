"""FakePlayer — lightweight player backend for testing, no GStreamer dependency."""
from __future__ import annotations

import logging
from enum import Enum

from PySide6.QtCore import QObject, Signal, QTimer

logger = logging.getLogger("michi.fake_player")


class PlaybackState(Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2
    LOADING = 3
    FAILED = 4


class FakePlayer(QObject):
    position_changed = Signal(float)
    duration_changed = Signal(float)
    state_changed = Signal(object)  # PlaybackState
    finished = Signal()
    error_occurred = Signal(str)
    queue_changed = Signal(list)
    stream_metadata_changed = Signal(str, str, str)

    def __init__(self, parent=None, use_timer: bool = True):
        super().__init__(parent)
        self._state = PlaybackState.STOPPED
        self._position = 0.0
        self._duration = 0.0
        self._volume = 80
        self._muted = False
        self._queue: list[dict] = []
        self._current_index = -1
        self._current_filepath = ""
        self._shuffle = False
        self._repeat = "none"
        self._use_timer = use_timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._error_mode = False
        self._last_error = ""

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def position(self) -> float:
        return self._position

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def current_filepath(self) -> str:
        return self._current_filepath

    @property
    def queue(self) -> list[dict]:
        return list(self._queue)

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def repeat(self) -> str:
        return self._repeat

    @property
    def last_error(self) -> str:
        return self._last_error

    def set_error_mode(self, enabled: bool):
        self._error_mode = enabled

    def play(self, filepath_or_url: str = ""):
        if self._error_mode:
            self._state = PlaybackState.FAILED
            self._last_error = "SIMULATED_ERROR"
            self.error_occurred.emit("SIMULATED_ERROR")
            self.state_changed.emit(PlaybackState.FAILED)
            return
        if filepath_or_url:
            self._current_filepath = filepath_or_url
            self._duration = 180.0
        self._state = PlaybackState.PLAYING
        self._position = 0.0
        if self._use_timer:
            self._timer.start(100)
        self.state_changed.emit(PlaybackState.PLAYING)

    def pause(self):
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.PAUSED
            self._timer.stop()
            self.state_changed.emit(PlaybackState.PAUSED)

    def stop(self):
        self._state = PlaybackState.STOPPED
        self._position = 0.0
        self._timer.stop()
        self.state_changed.emit(PlaybackState.STOPPED)

    def resume(self):
        if self._state == PlaybackState.PAUSED:
            self._state = PlaybackState.PLAYING
            self._timer.start(100)
            self.state_changed.emit(PlaybackState.PLAYING)

    def seek(self, seconds: float):
        if self._duration > 0:
            self._position = max(0.0, min(seconds, self._duration))

    def set_volume(self, vol: int):
        self._volume = max(0, min(100, vol))
        self.position_changed.emit(float(self._volume))

    def set_muted(self, muted: bool):
        self._muted = muted

    def next(self):
        if self._current_index < len(self._queue) - 1:
            self._current_index += 1
            self.play(self._queue[self._current_index].get("filepath", ""))
        elif self._repeat == "all" and self._queue:
            self._current_index = 0
            self.play(self._queue[0].get("filepath", ""))
        else:
            self.stop()
            self.finished.emit()

    def previous(self):
        if self._current_index > 0:
            self._current_index -= 1
            self.play(self._queue[self._current_index].get("filepath", ""))

    def set_queue(self, items: list[dict]):
        self._queue = list(items)
        self.queue_changed.emit(list(items))

    def enqueue(self, items: list[dict]):
        self._queue.extend(items)
        self.queue_changed.emit(list(self._queue))

    def clear_queue(self):
        self._queue = []
        self._current_index = -1
        self.queue_changed.emit([])

    def set_shuffle(self, enabled: bool):
        self._shuffle = enabled

    def set_repeat(self, mode: str):
        self._repeat = mode

    def _tick(self):
        self._advance_position()

    def _advance_position(self):
        if self._state == PlaybackState.PLAYING:
            self._position += 0.1
            self.position_changed.emit(self._position)
            if self._duration > 0 and self._position >= self._duration:
                if self._timer and self._use_timer:
                    self._timer.stop()
                self.finished.emit()
