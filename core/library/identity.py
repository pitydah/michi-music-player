from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackIdentity:
    track_id: int
    track_uid: str
    source_id: int | None = None
    filepath_hash: str | None = None

    @classmethod
    def from_filepath(cls, track_id: int, filepath: str) -> TrackIdentity:
        fp_hash = hashlib.sha256(filepath.encode()).hexdigest()[:16]
        return cls(track_id=track_id, track_uid=f"fp:{fp_hash}", filepath_hash=fp_hash)

    @classmethod
    def from_row(cls, row) -> TrackIdentity:
        return cls(
            track_id=row[0],
            track_uid=row[1] or "",
            source_id=row[2] if len(row) > 2 else None,
            filepath_hash=row[3] if len(row) > 3 else None,
        )


@dataclass(frozen=True)
class AlbumIdentity:
    album_key: str
    album_artist: str
    album_title: str


@dataclass(frozen=True)
class ArtistIdentity:
    artist_name: str
    artist_sort: str = ""
