"""Queue use case (M4-R1) — SOLE mutation authority for QueueState CONTENT.

Queue is TEMPORARY USER-CREATED CONTENT ONLY: entries, ordering, add/
remove/move/clear/replace. It NEVER commands playback: no PlaybackService
import, no playback-request APIs, no EndOfMedia subscription, no
repeat/shuffle ownership, no pending playback candidate, no current
playback track. Navigation authority lives in PlaybackSessionService.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from michi.domain.queue import QueueCapacityError, QueueState, Track

logger = logging.getLogger(__name__)


class QueueService:
    """Owns QueueState content. No playback dependency (M4-R1)."""

    def __init__(self, *, max_tracks: int = 10000) -> None:
        """Final M4-R1 constructor seal: keyword-only max_tracks.

        QueueService(playback) MUST FAIL at the Python signature level —
        no legacy positional compatibility seam."""
        if max_tracks <= 0:
            raise ValueError(f"max_tracks must be positive: {max_tracks!r}")
        self._state = QueueState()
        self._max_tracks = max_tracks
        self._subscribers: list[Callable[[], None]] = []

    @property
    def state(self) -> QueueState:
        return self._state

    @property
    def max_tracks(self) -> int:
        return self._max_tracks

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
        if self._state.count >= self._max_tracks:
            raise QueueCapacityError(f"queue capacity {self._max_tracks} exceeded")
        self._state.tracks.append(Track(file_path=file_path, title=title))
        self._notify()

    def add_many(self, paths: list[Path]) -> None:
        """Bulk append (explicit Queue intent, e.g. Queue Playlist)."""
        if self._state.count + len(paths) > self._max_tracks:
            raise QueueCapacityError(f"queue capacity {self._max_tracks} exceeded")
        for path in paths:
            self._state.tracks.append(Track(file_path=path))
        self._notify()

    def insert_at(self, index: int, file_path: Path, title: str = "") -> None:
        """Insert Queue content at a clamped position.

        Queue owns content only. Shuffle/repeat/navigation are exclusively
        PlaybackSessionService concerns (KCR-001).
        """
        if self._state.count >= self._max_tracks:
            raise QueueCapacityError(f"queue capacity {self._max_tracks} exceeded")
        index = max(0, min(index, self._state.count))
        self._state.tracks.insert(
            index,
            Track(file_path=file_path, title=title),
        )
        self._notify()

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._state.tracks):
            del self._state.tracks[index]
            self._notify()

    def move(self, from_index: int, to_index: int) -> None:
        """Reorder by exact Track identity (M4 original contract). Invalid
        and same-index moves are deterministic no-ops with no notification."""
        tracks = self._state.tracks
        if not (0 <= from_index < len(tracks)):
            return
        if not (0 <= to_index < len(tracks)):
            return
        if from_index == to_index:
            return
        track = tracks[from_index]
        reordered = list(tracks)
        del reordered[from_index]
        reordered.insert(to_index, track)
        self._state.tracks = reordered
        self._notify()

    def clear(self) -> None:
        """Clears Queue CONTENT only. NEVER stops playback (M4-R1 §28)."""
        self._state.tracks.clear()
        self._notify()

    def replace(self, tracks: list[Track]) -> None:
        """Atomic Queue content replacement (KCR-002).

        Capacity is a QueueService invariant and therefore applies to every
        mutation path — overflow raises BEFORE any mutation (no truncation,
        no silent no-op).
        """
        if len(tracks) > self._max_tracks:
            raise QueueCapacityError(
                f"queue capacity {self._max_tracks} exceeded"
            )
        self._state.tracks = list(tracks)
        self._notify()

    def restore_entries(self, tracks: list[Track]) -> None:
        """Startup Queue CONTENT restoration only — no repeat/shuffle/current
        playback index (those live in the Playback Session). Capacity guard
        first: a persisted queue larger than ``max_tracks`` restores a fresh
        empty queue (never truncated)."""
        if len(tracks) > self._max_tracks:
            logger.warning(
                "persisted queue %d exceeds max_tracks %d; "
                "restoring a fresh empty queue",
                len(tracks),
                self._max_tracks,
            )
            self._state.tracks.clear()
            self._notify()
            return
        self._state.tracks = list(tracks)
        self._notify()
