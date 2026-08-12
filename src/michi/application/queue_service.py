"""Queue use case — sole mutation authority for QueueState. Publishes changes."""

from collections.abc import Callable
from pathlib import Path

from michi.application.playback_service import PlaybackService
from michi.domain.queue import QueueState, Track


class QueueService:
    """Owns QueueState. Coordinates with PlaybackService for actual playback."""

    def __init__(self, playback_service: PlaybackService) -> None:
        self._playback = playback_service
        self._state = QueueState()
        self._subscribers: list[Callable[[], None]] = []

    @property
    def state(self) -> QueueState:
        return self._state

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for cb in self._subscribers:
            cb()

    def add(self, file_path: Path) -> None:
        self._state.tracks.append(Track(file_path=file_path))
        self._notify()

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._state.tracks):
            del self._state.tracks[index]
            if index < self._state.current_index:
                self._state.current_index -= 1
            elif index == self._state.current_index:
                self._state.current_index = min(
                    self._state.current_index, len(self._state.tracks) - 1
                )
            self._notify()

    def clear(self) -> None:
        self._playback.stop()
        self._state.tracks.clear()
        self._state.current_index = -1
        self._notify()

    def play_index(self, index: int) -> None:
        if 0 <= index < len(self._state.tracks):
            self._playback.load_and_play(self._state.tracks[index].file_path)
            self._state.current_index = index
            self._notify()

    def next(self) -> None:
        self.play_index(self._state.current_index + 1)

    def previous(self) -> None:
        self.play_index(self._state.current_index - 1)

    def play_current(self) -> None:
        track = self._state.current_track
        if track:
            self._playback.load_and_play(track.file_path)
