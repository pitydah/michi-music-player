from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrackAdded:
    track_id: int
    track_uid: str
    source_id: int | None = None


@dataclass(frozen=True)
class TrackUpdated:
    track_id: int
    fields_changed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TrackRemoved:
    track_id: int


@dataclass(frozen=True)
class TrackMissingChanged:
    track_id: int
    is_missing: bool = True


@dataclass(frozen=True)
class FavoriteChanged:
    track_id: int
    is_favorite: bool = True


@dataclass(frozen=True)
class PlayCountChanged:
    track_id: int
    play_count: int = 0


@dataclass(frozen=True)
class AlbumChanged:
    album_key: str
    fields_changed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArtistChanged:
    artist_name: str
    fields_changed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceChanged:
    source_id: int
    status: str = ""


@dataclass(frozen=True)
class ScanStarted:
    source_id: int


@dataclass(frozen=True)
class ScanProgress:
    source_id: int
    progress: float = 0.0
    current_file: str = ""


@dataclass(frozen=True)
class ScanFinished:
    source_id: int
    tracks_added: int = 0
    tracks_removed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MetadataWritten:
    track_ids: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class ArtworkChanged:
    track_id: int


@dataclass(frozen=True)
class PlaylistChanged:
    playlist_id: int


@dataclass(frozen=True)
class QueueChanged:
    action: str = ""
    track_id: int | None = None
