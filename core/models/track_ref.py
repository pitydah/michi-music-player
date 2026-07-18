"""Canonical TrackRef — frozen dataclass for track identity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TrackRef:
    track_id: int | None = None
    track_uid: str = ""
    filepath: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    albumartist: str = ""
    duration: float = 0.0
    bitrate: int = 0
    sample_rate: int = 0
    format: str = ""
    genre: str = ""
    year: int = 0
    track_number: int = 0
    disc_number: int = 0
    cover_path: str = ""
    source_type: str = "local_file"
    source_label: str = ""
    play_count: int = 0
    favorite: bool = False
    has_artwork: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "track_uid": self.track_uid,
            "filepath": self.filepath,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "albumartist": self.albumartist,
            "duration": self.duration,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "format": self.format,
            "genre": self.genre,
            "year": self.year,
            "track_number": self.track_number,
            "disc_number": self.disc_number,
            "cover_path": self.cover_path,
            "source_type": self.source_type,
            "source_label": self.source_label,
            "play_count": self.play_count,
            "favorite": self.favorite,
            "has_artwork": self.has_artwork,
        }
