"""Queue use case — sole mutation authority for QueueState. Publishes changes."""

import random
from collections.abc import Callable
from pathlib import Path

from michi.application.playback_service import PlaybackService
from michi.domain.queue import QueueState, RepeatMode, ShuffleNavigator, Track


class QueueService:
    """Owns QueueState. Coordinates with PlaybackService for actual playback."""

    def __init__(self, playback_service: PlaybackService, rng=None) -> None:
        self._playback = playback_service
        self._rng = rng if rng is not None else random.Random()
        self._navigator = ShuffleNavigator()
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

    def add(self, file_path: Path, title: str = "") -> None:
        track = Track(file_path=file_path, title=title)
        self._state.tracks.append(track)
        if self._state.shuffle_enabled:
            self._navigator.add(track)
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
            if self._state.shuffle_enabled:
                self._navigator.remove(removed_track)
            self._notify()

    def clear(self) -> None:
        self._playback.stop()
        self._pending_track = None
        self._navigator.clear()
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

    def set_shuffle_enabled(self, enabled: bool) -> None:
        if not isinstance(enabled, bool):
            raise ValueError(f"invalid shuffle flag: {enabled!r}")
        if self._state.shuffle_enabled is enabled:
            return
        self._state.shuffle_enabled = enabled
        if enabled:
            self._navigator.reset(
                self._state.tracks, self._state.current_track, self._rng
            )
        else:
            self._navigator.clear()
        self._notify()

    def _index_of(self, track: Track) -> int:
        for i, t in enumerate(self._state.tracks):
            if t is track:
                return i
        return -1

    def _shuffle_pick(self) -> Track | None:
        return self._navigator.pop_next(self._rng)

    def _on_end_of_media(self) -> None:
        """Natural end of the committed track. Applies the repeat mode.

        Canonical decision order (LOCAL-STABILIZATION-01.6.1):
        1. Repeat ONE takes precedence: the exact current entry replays,
           regardless of any remaining shuffle pool (A → A, never A → B/C).
        2. Shuffle enabled: the next pick comes from the shuffle pool; an
           exhausted pool stops on NONE or regenerates a new cycle on ALL.
        3. Natural order: NONE advances by index (stops at the end), ALL
           wraps around.

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
        if self._state.repeat_mode is RepeatMode.ONE:
            # Repeat ONE has precedence over shuffle: the exact current entry
            # replays regardless of any remaining shuffle pool. The replay
            # path never touches the navigator, so the pool is not popped.
            self.play_index(self._state.current_index)
            return
        if self._state.shuffle_enabled:
            target = self._shuffle_pick()
            if target is None:
                if self._state.repeat_mode is RepeatMode.ALL:
                    self._navigator.regenerate(
                        self._state.tracks, self._state.current_track, self._rng
                    )
                    target = self._shuffle_pick()
                    if target is None:  # single-track edge
                        self.play_index(self._state.current_index)
                        return
                else:  # RepeatMode.NONE
                    self._playback.stop()
                    return
            self.play_index(self._index_of(target))
            return
        if self._state.repeat_mode is RepeatMode.ALL:
            self.play_index((self._state.current_index + 1) % len(self._state.tracks))
        elif self._state.current_index + 1 < len(self._state.tracks):
            self.play_index(self._state.current_index + 1)
        else:
            self._playback.stop()

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
                if self._state.shuffle_enabled:
                    self._navigator.record_commit(track)
                self._notify()
                return
        self._pending_track = None

    def _reject_pending(self, track: Track, path: Path, message: str) -> None:
        """Rejection point: drop the pending candidate if it is still the
        pending request. The request is already terminal at the playback
        layer — nothing else may mutate or notify. A rejected shuffled
        candidate is dropped from the cycle, so playback is stopped."""
        if self._pending_track is not track:
            return
        if track.file_path != path:
            return
        self._pending_track = None
        if self._state.shuffle_enabled:
            self._playback.stop()

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
        if self._state.shuffle_enabled:
            target = self._shuffle_pick()
            if target is None:
                mode = self._state.repeat_mode
                if mode is RepeatMode.ALL:
                    self._navigator.regenerate(
                        self._state.tracks, self._state.current_track, self._rng
                    )
                    target = self._shuffle_pick()
                    if target is None:
                        self.play_index(self._state.current_index)
                        return
                elif mode is RepeatMode.NONE:
                    self._playback.stop()
                    return
                else:  # RepeatMode.ONE
                    self.play_index(self._state.current_index)
                    return
            self.play_index(self._index_of(target))
            return
        self.play_index(self._state.current_index + 1)

    def previous(self) -> None:
        if self._state.shuffle_enabled:
            target = self._navigator.previous_pick()
            if target is None:
                return
            self.play_index(self._index_of(target))
            return
        self.play_index(self._state.current_index - 1)

    @property
    def has_next(self) -> bool:
        if self._state.shuffle_enabled:
            if self._navigator.pool:
                return True
            return self._state.repeat_mode is not RepeatMode.NONE
        return self._state.has_next

    def play_current(self) -> None:
        self.play_index(self._state.current_index)
