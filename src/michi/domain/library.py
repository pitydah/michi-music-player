"""Library domain state — pure, no Qt/infra dependencies."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TrackRef:
    file_path: Path
    display_name: str = ""

    def __post_init__(self) -> None:
        if not self.display_name:
            object.__setattr__(self, "display_name", self.file_path.stem)


@dataclass
class LibraryState:
    tracks: list[TrackRef] = field(default_factory=list)
    query: str = ""
    current_directory: str = ""

    @property
    def visible_tracks(self) -> list[TrackRef]:
        if not self.query:
            return self.tracks
        q = self.query.lower()
        return [t for t in self.tracks if q in t.display_name.lower()]
