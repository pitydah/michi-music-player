"""MusicSource — abstract base for unified music source access."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class TrackRef:
    """Minimal track reference, source-agnostic."""
    uri: str
    title: str = ""
    artist: str = ""
    album: str = ""
    duration: float = 0.0
    cover_path: str = ""
    track_number: int = 0
    year: int = 0
    genre: str = ""
    source_type: str = "local_file"
    source_label: str = ""


class MusicSource(ABC):
    """Abstract source: local / radio / subsonic / folders."""

    @abstractmethod
    def list_tracks(self) -> list[TrackRef]:
        """List all tracks from this source."""
        ...

    @abstractmethod
    def search(self, query: str) -> list[TrackRef]:
        """Search tracks by query."""
        ...

    def get_artwork(self, track: TrackRef) -> Optional[str]:
        """Return artwork path for a track. Override if source can provide one."""
        return track.cover_path or None

    def can_stream(self, track: TrackRef) -> bool:
        """Whether this source can stream `track.uri` directly (e.g. radio, subsonic)."""
        return False
