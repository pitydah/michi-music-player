"""Library domain state — pure, no Qt/infra dependencies."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


@dataclass(frozen=True)
class TrackMetadata:
    """Extracted metadata for a library entry (canonical minimal model)."""

    title: str = ""
    artist: str = ""
    album: str = ""
    duration_ms: int = 0


@dataclass(frozen=True)
class TrackRef:
    file_path: Path
    display_name: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    duration_ms: int = 0

    def __post_init__(self) -> None:
        if not self.display_name:
            object.__setattr__(self, "display_name", self.file_path.stem)


class LibraryDiagnosticCode(Enum):
    """Filesystem degradation taxonomy for the library."""

    TRACK_MISSING = "track_missing"
    DIRECTORY_MISSING = "directory_missing"
    ACCESS_FAILURE = "access_failure"
    IO_FAILURE = "io_failure"
    UNKNOWN_FAILURE = "unknown_failure"
    STALE_ENTRIES_REMOVED = "stale_entries_removed"


@dataclass(frozen=True)
class LibraryDiagnostic:
    code: LibraryDiagnosticCode
    message: str
    path: Path | None = None
    affected_count: int = 0


@dataclass
class LibraryState:
    tracks: list[TrackRef] = field(default_factory=list)
    query: str = ""
    current_directory: str = ""
    diagnostic: LibraryDiagnostic | None = None

    @property
    def visible_tracks(self) -> list[TrackRef]:
        if not self.query:
            return self.tracks
        q = self.query.lower()
        return [t for t in self.tracks if q in t.display_name.lower()]
