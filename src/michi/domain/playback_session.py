"""Domain layer — active playback session (M4-R1).

Sole authority domain for the ACTIVE PLAYBACK CONTEXT: context type,
sequence, current position, Next/Previous, Repeat, Shuffle and EndOfMedia
navigation policy. This is deliberately SEPARATE from Queue content:
playing something never implies adding it to the Queue.

Pure business logic: no Qt, no backend objects, no TrackRef requirement,
no metadata database objects.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class PlaybackContextType(Enum):
    """The kind of active playback context (exactly ONE at a time)."""

    NONE = auto()
    SINGLE = auto()
    ALBUM = auto()
    PLAYLIST = auto()
    QUEUE = auto()


class RepeatMode(Enum):
    """Repeat policy of the PLAYBACK SESSION (moved out of Queue in M4-R1)."""

    NONE = auto()
    ONE = auto()
    ALL = auto()


@dataclass(frozen=True)
class PlaybackSequenceEntry:
    """A pure sequence value. Duplicates MUST be allowed: two entries with
    the same path may occupy different sequence positions."""

    file_path: Path
    title: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class PlaybackSessionState:
    """Immutable-published session projection (read-only by convention)."""

    context_type: PlaybackContextType = PlaybackContextType.NONE
    source_id: str | None = None
    entries: tuple[PlaybackSequenceEntry, ...] = ()
    current_index: int = -1
    repeat_mode: RepeatMode = RepeatMode.NONE
    shuffle_enabled: bool = False
    shuffle_seed: int = 0

    @property
    def current_entry(self) -> PlaybackSequenceEntry | None:
        if 0 <= self.current_index < len(self.entries):
            return self.entries[self.current_index]
        return None

    @property
    def has_next(self) -> bool:
        return self.current_index + 1 < len(self.entries)

    @property
    def has_previous(self) -> bool:
        return self.current_index > 0

    @property
    def count(self) -> int:
        return len(self.entries)


class ShuffleNavigator:
    """Pure shuffle navigation bookkeeping (M4-R1: owned by the Playback
    Session, not by Queue). No RNG stored: callers pass the random generator
    so tests can inject a seeded one. Deterministic seed, history, no random
    repeat inside a cycle, previous traversal, Repeat-ALL regeneration."""

    def __init__(self) -> None:
        self.pool: list[PlaybackSequenceEntry] = []
        self.history: list[PlaybackSequenceEntry] = []

    def reset(
        self,
        entries: list[PlaybackSequenceEntry],
        current: PlaybackSequenceEntry | None,
        rng,
    ) -> None:
        """Fresh cycle: shuffled pool of everything except `current`."""
        candidates = [e for e in entries if e is not current]
        self.pool = rng.sample(candidates, len(candidates)) if candidates else []
        self.history = [current] if current is not None else []

    def regenerate(
        self,
        entries: list[PlaybackSequenceEntry],
        last_played: PlaybackSequenceEntry | None,
        rng,
    ) -> None:
        """Repeat-ALL cycle restart: avoid the entry that just played."""
        candidates = [e for e in entries if e is not last_played]
        self.pool = rng.sample(candidates, len(candidates)) if candidates else []
        self.history = [last_played] if last_played is not None else []

    def pop_next(self, rng) -> PlaybackSequenceEntry | None:
        if not self.pool:
            return None
        index = rng.randrange(len(self.pool))
        return self.pool.pop(index)

    def record_commit(self, entry: PlaybackSequenceEntry) -> None:
        self.pool = [e for e in self.pool if e is not entry]
        if not self.history or self.history[-1] is not entry:
            self.history.append(entry)

    def previous_pick(self) -> PlaybackSequenceEntry | None:
        """Walk real history: current returns to the pool; target is the
        entry before it. None when history has fewer than two entries."""
        if len(self.history) < 2:
            return None
        current = self.history.pop()
        self.pool.append(current)
        return self.history[-1]

    def remove(self, entry: PlaybackSequenceEntry) -> None:
        self.pool = [e for e in self.pool if e is not entry]
        self.history = [e for e in self.history if e is not entry]

    def add(self, entry: PlaybackSequenceEntry) -> None:
        self.pool.append(entry)

    def clear(self) -> None:
        self.pool.clear()
        self.history.clear()
