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


@dataclass(frozen=True)
class AlbumRef:
    """Canonical album reference derived from library tracks (LOCAL-01)."""

    key: str
    title: str
    artist: str
    track_count: int
    duration_ms: int
    track_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ArtistRef:
    """Canonical artist reference derived from library tracks (LOCAL-01)."""

    key: str
    name: str
    track_count: int
    album_count: int


@dataclass(frozen=True)
class MusicModel:
    """Pure, deterministic view of the library grouped into albums and artists."""

    albums: tuple[AlbumRef, ...] = ()
    artists: tuple[ArtistRef, ...] = ()


def _normalize_key(s: str) -> str:
    """Canonical grouping key: casefolded and stripped."""
    return s.casefold().strip()


_UNKNOWN_ALBUM = "Unknown Album"
_UNKNOWN_ARTIST = "Unknown Artist"


def build_music_model(tracks) -> MusicModel:
    """Derive albums and artists from tracks (pure, deterministic by key).

    Albums are grouped by the normalized (album, primary-artist) pair where
    the primary artist is the first track's artist within that album. Display
    title/artist come from the first member. Empty album -> "Unknown Album",
    empty artist -> "Unknown Artist". Album duration is the sum of members and
    ``track_paths`` preserves library order. Artists are grouped by normalized
    name with total track count and distinct-album count.
    """
    album_entries: dict[str, dict] = {}
    artist_entries: dict[str, dict] = {}
    for track in tracks:
        album_title = track.album.strip() or _UNKNOWN_ALBUM
        artist_name = track.artist.strip() or _UNKNOWN_ARTIST
        album_key = f"{_normalize_key(album_title)}::{_normalize_key(artist_name)}"
        album = album_entries.get(album_key)
        if album is None:
            album = {
                "title": album_title,
                "artist": artist_name,
                "duration_ms": 0,
                "paths": [],
            }
            album_entries[album_key] = album
        album["duration_ms"] += track.duration_ms
        album["paths"].append(track.file_path)

        artist_key = _normalize_key(artist_name)
        artist = artist_entries.get(artist_key)
        if artist is None:
            artist = {"name": artist_name, "track_count": 0, "albums": set()}
            artist_entries[artist_key] = artist
        artist["track_count"] += 1
        artist["albums"].add(_normalize_key(album_title))

    albums = tuple(
        sorted(
            (
                AlbumRef(
                    key=key,
                    title=entry["title"],
                    artist=entry["artist"],
                    track_count=len(entry["paths"]),
                    duration_ms=entry["duration_ms"],
                    track_paths=tuple(entry["paths"]),
                )
                for key, entry in album_entries.items()
            ),
            key=lambda a: a.key,
        )
    )
    artists = tuple(
        sorted(
            (
                ArtistRef(
                    key=key,
                    name=entry["name"],
                    track_count=entry["track_count"],
                    album_count=len(entry["albums"]),
                )
                for key, entry in artist_entries.items()
            ),
            key=lambda a: a.key,
        )
    )
    return MusicModel(albums=albums, artists=artists)


@dataclass
class LibraryState:
    tracks: list[TrackRef] = field(default_factory=list)
    query: str = ""
    current_directory: str = ""
    diagnostic: LibraryDiagnostic | None = None
    albums: tuple[AlbumRef, ...] = ()
    artists: tuple[ArtistRef, ...] = ()

    @property
    def visible_tracks(self) -> list[TrackRef]:
        if not self.query:
            return self.tracks
        q = self.query.lower()
        return [t for t in self.tracks if q in t.display_name.lower()]
