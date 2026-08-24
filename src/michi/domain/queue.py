"""Domain layer — Queue content state (M4-R1).

Queue is TEMPORARY user-created CONTENT ONLY: entries, ordering, add/
remove/move/clear/replace. It is NOT the playback authority — the active
sequence, current position, repeat, shuffle and EndOfMedia navigation
belong to ``michi.domain.playback_session`` (PlaybackSessionState).

This module keeps a compatibility re-export of RepeatMode for callers
still migrating; canonical ownership is playback_session.
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from michi.domain.playback_session import RepeatMode  # noqa: F401  (re-export)


@dataclass
class Track:
    """A Queue entry. ``entry_id`` is the opaque RUNTIME identity.

    Unique per Queue insertion, immutable for the lifetime of that entry,
    preserved by move(), removed by remove()/clear(). Two entries with the
    same file_path MUST have different entry_ids — file_path is payload,
    NOT identity. Runtime-only: never persisted (restart creates fresh ids).
    """

    file_path: Path
    title: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        if not self.title:
            self.title = self.file_path.stem


class QueueCapacityError(RuntimeError):
    """Raised when add() would exceed the configured max_tracks; the queue
    is left unchanged."""


@dataclass
class QueueState:
    """Sole authority for Queue CONTENT (M4-R1: no playback fields).

    current_index / repeat_mode / shuffle_enabled live in
    PlaybackSessionState — QueueState must not contain canonical playback
    navigation state.
    """

    tracks: list[Track] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.tracks)
