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


@dataclass
class QueueState:
    """Single canonical authority for the playback queue."""

    tracks: list[Track] = field(default_factory=list)
    current_index: int = -1
    repeat_mode: RepeatMode = RepeatMode.NONE

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
