"""Queue use case — sole mutation authority for QueueState. Publishes changes."""

from collections.abc import Callable
from pathlib import Path

from michi.application.playback_service import PlaybackService
from michi.domain.queue import QueueState, RepeatMode, Track


class QueueService:
    """Owns QueueState. Coordinates with PlaybackService for actual playback."""

    def __init__(self, playback_service: PlaybackService) -> None:
        self._playback = playback_service
        self._state = QueueState()
        self._subscribers: list[Callable[[], None]] = []
        self._pending_track: Track | None = None
        self._playback.subscribe_end_of_media(self._on_end_of_media)

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
            removed_track = self._state.tracks[index]
            if removed_track is self._pending_track:
                self._pending_track = None
                self._playback.stop()
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
        self._pending_track = None
        self._state.tracks.clear()
        self._state.current_index = -1
        self._notify()

    def play_index(self, index: int) -> None:
        """Request playback of a track. Commits the track only on acceptance."""
        if 0 <= index < len(self._state.tracks):
            track = self._state.tracks[index]
            self._pending_track = track
            try:
                self._playback.load_and_play(
                    track.file_path,
                    on_accepted=lambda path, track=track: self._commit_pending(
                        track, path
                    ),
                    on_rejected=lambda path, message, track=track: self._reject_pending(
                        track, path, message
                    ),
                    on_cancelled=lambda path, track=track: self._cancel_pending(
                        track, path
                    ),
                )
            except Exception:
                if self._pending_track is track:
                    self._pending_track = None
                raise

    def set_repeat_mode(self, mode: RepeatMode) -> None:
        if not isinstance(mode, RepeatMode):
            raise ValueError(f"invalid repeat mode: {mode!r}")
        if self._state.repeat_mode is mode:
            return
        self._state.repeat_mode = mode
        self._notify()

    def _on_end_of_media(self) -> None:
        """Natural end of the committed track. Applies the repeat mode.

        A pending request means a new candidate is already in flight (manual
        navigation or a previous auto-advance): the EOM is stale and is
        ignored. Auto-advance goes through play_index so the pending/
        acceptance/rejection/cancellation machinery (TD-015/TD-016) applies
        unchanged.
        """
        if self._pending_track is not None:
            return
        if not self._state.tracks or self._state.current_index < 0:
            return
        index = self._state.current_index
        mode = self._state.repeat_mode
        if mode is RepeatMode.NONE:
            if index + 1 < len(self._state.tracks):
                self.play_index(index + 1)
            else:
                self._playback.stop()
        elif mode is RepeatMode.ONE:
            self.play_index(index)
        else:  # RepeatMode.ALL
            self.play_index((index + 1) % len(self._state.tracks))

    def _commit_pending(self, track: Track, path: Path) -> None:
        """Acceptance point: commit only if `track` is still the pending
        candidate, the backend-accepted path matches, and the same object
        still exists in the queue."""
        if self._pending_track is not track:
            return
        if track.file_path != path:
            return
        for current_idx, candidate in enumerate(self._state.tracks):
            if candidate is track:
                self._pending_track = None
                self._state.current_index = current_idx
                self._notify()
                return
        self._pending_track = None

    def _reject_pending(self, track: Track, path: Path, message: str) -> None:
        """Rejection point: drop the pending candidate if it is still the
        pending request. The request is already terminal at the playback
        layer — nothing else may mutate or notify."""
        if self._pending_track is not track:
            return
        if track.file_path != path:
            return
        self._pending_track = None

    def _cancel_pending(self, track: Track, path: Path) -> None:
        """Cancellation terminal: the requestor (PlaybackService.stop) reported
        the pending request cancelled. Clear the pending candidate only when
        `track` is still the exact pending object and the path matches;
        QueueState is not mutated, current_index is untouched, no track is
        removed, no stop is issued, and no notification fires (public state
        did not change)."""
        if self._pending_track is not track:
            return
        if track.file_path != path:
            return
        self._pending_track = None

    def next(self) -> None:
        self.play_index(self._state.current_index + 1)

    def previous(self) -> None:
        self.play_index(self._state.current_index - 1)

    def play_current(self) -> None:
        self.play_index(self._state.current_index)
