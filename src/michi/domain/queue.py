"""Domain layer — Queue state. Pure business logic, no Qt/infrastructure."""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


@dataclass
class Track:
    file_path: Path
    title: str = ""

    def __post_init__(self) -> None:
        if not self.title:
            self.title = self.file_path.stem


class RepeatMode(Enum):
    NONE = auto()
    ONE = auto()
    ALL = auto()


class QueueCapacityError(RuntimeError):
    """Raised when add() would exceed the configured max_tracks; the queue
    is left unchanged."""


@dataclass
class QueueState:
    """Single canonical authority for the playback queue."""

    tracks: list[Track] = field(default_factory=list)
    current_index: int = -1
    repeat_mode: RepeatMode = RepeatMode.NONE
    shuffle_enabled: bool = False

    @property
    def current_track(self) -> Track | None:
        if 0 <= self.current_index < len(self.tracks):
            return self.tracks[self.current_index]
        return None

    @property
    def has_next(self) -> bool:
        return self.current_index + 1 < len(self.tracks)

    @property
    def has_previous(self) -> bool:
        return self.current_index > 0

    @property
    def count(self) -> int:
        return len(self.tracks)


class ShuffleNavigator:
    """Pure shuffle navigation bookkeeping. No RNG stored: callers pass the
    random generator so tests can inject a seeded one."""

    def __init__(self) -> None:
        self.pool: list[Track] = []
        self.history: list[Track] = []

    def reset(self, tracks: list[Track], current: Track | None, rng) -> None:
        """Fresh cycle: shuffled pool of everything except `current`."""
        candidates = [t for t in tracks if t is not current]
        self.pool = rng.sample(candidates, len(candidates)) if candidates else []
        self.history = [current] if current is not None else []

    def regenerate(self, tracks: list[Track], last_played: Track | None, rng) -> None:
        """Repeat-ALL cycle restart: avoid the track that just played."""
        candidates = [t for t in tracks if t is not last_played]
        self.pool = rng.sample(candidates, len(candidates)) if candidates else []
        self.history = [last_played] if last_played is not None else []

    def pop_next(self, rng) -> Track | None:
        if not self.pool:
            return None
        index = rng.randrange(len(self.pool))
        return self.pool.pop(index)

    def record_commit(self, track: Track) -> None:
        self.pool = [t for t in self.pool if t is not track]
        if not self.history or self.history[-1] is not track:
            self.history.append(track)

    def previous_pick(self) -> Track | None:
        """Walk real history: current returns to the pool; target is the
        entry before it. None when history has fewer than two entries."""
        if len(self.history) < 2:
            return None
        current = self.history.pop()
        self.pool.append(current)
        return self.history[-1]

    def remove(self, track: Track) -> None:
        self.pool = [t for t in self.pool if t is not track]
        self.history = [t for t in self.history if t is not track]

    def add(self, track: Track) -> None:
        self.pool.append(track)

    def clear(self) -> None:
        self.pool.clear()
        self.history.clear()
