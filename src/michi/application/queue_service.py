"""Queue use case — sole mutation authority for QueueState."""

from pathlib import Path

from michi.application.playback_service import PlaybackService
from michi.domain.queue import QueueState, Track


class QueueService:
    """Owns QueueState. Coordinates with PlaybackService for actual playback."""

    def __init__(self, playback_service: PlaybackService) -> None:
        self._playback = playback_service
        self._state = QueueState()

    @property
    def state(self) -> QueueState:
        return self._state

    def add(self, file_path: Path) -> None:
        self._state.tracks.append(Track(file_path=file_path))

    def add_multiple(self, paths: list[Path]) -> None:
        for p in paths:
            self._state.tracks.append(Track(file_path=p))

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._state.tracks):
            del self._state.tracks[index]
            if index < self._state.current_index:
                self._state.current_index -= 1
            elif index == self._state.current_index:
                self._state.current_index = min(
                    self._state.current_index, len(self._state.tracks) - 1
                )

    def clear(self) -> None:
        self._playback.stop()
        self._state.tracks.clear()
        self._state.current_index = -1

    def play_index(self, index: int) -> None:
        if 0 <= index < len(self._state.tracks):
            self._state.current_index = index
            track = self._state.tracks[index]
            self._playback.load_and_play(track.file_path)

    def next(self) -> None:
        if self._state.has_next:
            self._state.current_index += 1
            track = self._state.current_track
            if track:
                self._playback.load_and_play(track.file_path)

    def previous(self) -> None:
        if self._state.has_previous:
            self._state.current_index -= 1
            track = self._state.current_track
            if track:
                self._playback.load_and_play(track.file_path)

    def play_current(self) -> None:
        track = self._state.current_track
        if track:
            self._playback.load_and_play(track.file_path)
