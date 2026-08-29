"""Domain layer — Queue content state (M4-R1).

Queue is TEMPORARY user-created CONTENT ONLY: entries, ordering, add/
remove/move/clear/replace. It is NOT the playback authority — the active
sequence, current position, repeat, shuffle and EndOfMedia navigation
belong to ``michi.domain.playback_session`` (PlaybackSessionState).

Canonical ownership of Repeat/Shuffle is ``michi.domain.playback_session``.
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Track:
    """A Queue entry. ``entry_id`` is the opaque RUNTIME identity.

    Unique per Queue insertion, immutable for the lifetime of that entry,
    preserved by move(), removed by remove()/clear(). Two entries with the
    same file_path MUST have different entry_ids — file_path is payload,
    NOT identity. Runtime-only: never persisted (restart creates fresh ids).

    ``library_track_id`` (M6-EXT-R4-I) is the OPTIONAL stable Library
    entity identity — different from ``entry_id``: two queue entries may
    share a library_track_id (same song queued twice) with distinct
    entry_ids.
    """

    file_path: Path
    title: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    library_track_id: str | None = None

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
