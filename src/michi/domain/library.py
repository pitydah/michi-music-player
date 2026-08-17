"""Library domain state — pure, no Qt/infra dependencies."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

HISTORY_CAP = 50
RECENT_CAP = 50


@dataclass(frozen=True)
class TrackMetadata:
    """Rich canonical metadata (LOCAL-META-02): musical + technical fields;
    0/'' mean UNKNOWN honestly — never fabricated."""

    title: str = ""
    artist: str = ""
    album: str = ""
    duration_ms: int = 0
    genre: str = ""
    year: int = 0
    album_artist: str = ""
    track_number: int = 0
    track_total: int = 0
    disc_number: int = 0
    disc_total: int = 0
    composer: str = ""
    date: str = ""
    compilation: bool = False
    sort_title: str = ""
    sort_artist: str = ""
    sort_album: str = ""
    sort_album_artist: str = ""
    codec: str = ""
    container: str = ""
    sample_rate_hz: int = 0
    bit_depth: int = 0
    channels: int = 0
    bitrate_bps: int = 0
    file_size: int = 0


@dataclass(frozen=True)
class TrackRef:
    """model projection of TrackMetadata (album_artist/track/disc/composer/
    compilation); technical audio properties live in TrackMetadata"""

    file_path: Path
    display_name: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    duration_ms: int = 0
    genre: str = ""
    year: int = 0
    album_artist: str = ""
    track_number: int = 0
    disc_number: int = 0
    composer: str = ""
    compilation: bool = False

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
class Artwork:
    """Embedded cover art extracted from a media file (LOCAL-02).

    ``data`` is the raw image payload and ``mime_type`` its content type
    (e.g. "image/jpeg", "image/png") as reported by the tag format.
    """

    data: bytes
    mime_type: str


@dataclass(frozen=True)
class AlbumRef:
    """Canonical album reference derived from library tracks (LOCAL-01)."""

    key: str
    title: str
    artist: str
    track_count: int
    duration_ms: int
    track_paths: tuple[Path, ...] = ()
    has_artwork: bool = False
    year: int = 0


@dataclass(frozen=True)
class ArtistRef:
    """Canonical artist reference derived from library tracks (LOCAL-01)."""

    key: str
    name: str
    track_count: int
    album_count: int


@dataclass(frozen=True)
class GenreRef:
    """Canonical genre reference derived from library tracks (LOCAL-03)."""

    key: str
    name: str
    track_count: int


@dataclass(frozen=True)
class FolderRef:
    """Directory reference derived from library tracks (LOCAL-03)."""

    key: str
    path: str
    track_count: int


@dataclass(frozen=True)
class MusicModel:
    """Pure, deterministic view of the library grouped into albums and artists."""

    albums: tuple[AlbumRef, ...] = ()
    artists: tuple[ArtistRef, ...] = ()
    genres: tuple[GenreRef, ...] = ()


def _normalize_key(s: str) -> str:
    """Canonical grouping key: casefolded, whitespace runs collapsed, stripped."""
    return " ".join(s.casefold().split())


_UNKNOWN_ALBUM = "Unknown Album"
_UNKNOWN_ARTIST = "Unknown Artist"
_UNKNOWN_GENRE = "Unknown Genre"
_VARIOUS_ARTISTS = "Various Artists"


def make_album_key(album_title: str, album_artist: str) -> str:
    """Canonical album identity (LOCAL-META-02.2c): length-prefixed so a
    '::' inside the title can never collide with the artist segment."""
    title = _normalize_key(album_title)
    artist = _normalize_key(album_artist)
    return f"{len(title)}::{title}::{artist}"


def make_artist_key(artist_name: str) -> str:
    """Canonical artist identity (LOCAL-META-02.2c)."""
    return _normalize_key(artist_name)


def _resolve_album_artist(track) -> str:
    """Resolved album-level artist (LOCAL-META-02.2c): an explicit
    ``album_artist`` wins; a compilation without one groups under
    "Various Artists"; otherwise the track's own artist."""
    if track.album_artist:
        return track.album_artist
    if track.compilation:
        return _VARIOUS_ARTISTS
    return track.artist


def build_music_model(tracks) -> MusicModel:
    """Derive albums and artists from tracks (pure, deterministic by key).

    Albums are grouped by ``make_album_key(track.album, resolved_album_artist)``
    where the resolved album artist (LOCAL-META-02.2c) is the explicit
    ``album_artist``, else "Various Artists" for compilations, else the track
    artist. Display title/artist come from the first member. Empty album ->
    "Unknown Album", empty artist -> "Unknown Artist". Album duration is the
    sum of members and ``track_paths`` preserves library order. Artists are
    grouped by normalized track artist (``make_artist_key``) with total track
    count and distinct-album count. Genres are grouped by normalized name
    with per-genre track count; empty genre -> "Unknown Genre" and the sum of
    genre counts equals the total track count.
    """
    album_entries: dict[str, dict] = {}
    artist_entries: dict[str, dict] = {}
    genre_entries: dict[str, dict] = {}
    for track in tracks:
        album_title = track.album.strip() or _UNKNOWN_ALBUM
        resolved_artist = _resolve_album_artist(track).strip() or _UNKNOWN_ARTIST
        album_key = make_album_key(album_title, resolved_artist)
        album = album_entries.get(album_key)
        if album is None:
            album = {
                "key": album_key,
                "title": album_title,
                "album_artist": resolved_artist,
                "duration_ms": 0,
                "paths": [],
            }
            album_entries[album_key] = album
        album.setdefault("year", track.year)  # first member wins
        album["duration_ms"] += track.duration_ms
        album["paths"].append(track.file_path)

        artist_name = track.artist.strip() or _UNKNOWN_ARTIST
        artist_key = make_artist_key(artist_name)
        artist = artist_entries.get(artist_key)
        if artist is None:
            artist = {"name": artist_name, "track_count": 0, "albums": set()}
            artist_entries[artist_key] = artist
        artist["track_count"] += 1
        artist["albums"].add(_normalize_key(album_title))

        genre_name = track.genre.strip() or _UNKNOWN_GENRE
        genre_key = _normalize_key(genre_name)
        genre = genre_entries.get(genre_key)
        if genre is None:
            genre = {"name": genre_name, "track_count": 0}
            genre_entries[genre_key] = genre
        genre["track_count"] += 1

    albums = tuple(
        sorted(
            (
                AlbumRef(
                    key=entry["key"],
                    title=entry["title"],
                    artist=entry["album_artist"],
                    track_count=len(entry["paths"]),
                    duration_ms=entry["duration_ms"],
                    track_paths=tuple(entry["paths"]),
                    year=entry["year"],
                )
                for entry in album_entries.values()
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
    genres = tuple(
        sorted(
            (
                GenreRef(
                    key=key,
                    name=entry["name"],
                    track_count=entry["track_count"],
                )
                for key, entry in genre_entries.items()
            ),
            key=lambda g: g.key,
        )
    )
    return MusicModel(albums=albums, artists=artists, genres=genres)


def build_folder_model(tracks) -> tuple[FolderRef, ...]:
    """Group tracks by parent directory (pure, deterministic by key).

    Key is the casefolded parent path; ``path`` is the display path; counts
    are per parent directory. Result is sorted by key so the output does not
    depend on input order.
    """
    folder_entries: dict[str, dict] = {}
    for track in tracks:
        parent = track.file_path.parent
        key = str(parent).casefold()
        folder = folder_entries.get(key)
        if folder is None:
            folder = {"path": str(parent), "track_count": 0}
            folder_entries[key] = folder
        folder["track_count"] += 1
    return tuple(
        sorted(
            (
                FolderRef(
                    key=key,
                    path=entry["path"],
                    track_count=entry["track_count"],
                )
                for key, entry in folder_entries.items()
            ),
            key=lambda f: f.key,
        )
    )


def merge_recently_added(
    new_paths,
    previous_recent,
    current_library_paths,
    cap,
) -> tuple[str, ...]:
    """Canonical recently-added merge (LOCAL-STABILIZATION-01.6.5).

    New tracks from the current successful scan come first (most recent
    scan order, reversed), then previous recently-added entries that still
    exist in the library; deduplicated, capped at ``cap``. An unchanged
    rescan must NOT erase recently added; removed tracks fall out once they
    leave the library.
    """
    seen = set()
    merged = []
    for path in reversed(new_paths):
        if path not in seen:
            seen.add(path)
            merged.append(path)
    for path in previous_recent:
        if path in seen:
            continue
        if path not in current_library_paths:
            continue
        seen.add(path)
        merged.append(path)
        if len(merged) >= cap:
            break
    return tuple(merged[:cap])


@dataclass(frozen=True)
class LibraryPrefs:
    """Persisted library preferences: favorites, play history, recently added.

    Paths are stored as plain strings (best-effort persistence; the
    repository may drop or corrupt them and the library keeps working)."""

    favorite_paths: tuple[str, ...] = ()
    history_paths: tuple[str, ...] = ()
    recently_added_paths: tuple[str, ...] = ()


@dataclass
class LibraryState:
    tracks: list[TrackRef] = field(default_factory=list)
    query: str = ""
    current_directory: str = ""
    diagnostic: LibraryDiagnostic | None = None
    albums: tuple[AlbumRef, ...] = ()
    artists: tuple[ArtistRef, ...] = ()
    genres: tuple[GenreRef, ...] = ()
    folders: tuple[FolderRef, ...] = ()
    favorite_paths: tuple[str, ...] = ()
    history_paths: tuple[str, ...] = ()
    recently_added_paths: tuple[str, ...] = ()

    @property
    def visible_tracks(self) -> list[TrackRef]:
        if not self.query:
            return self.tracks
        q = self.query.lower()
        return [t for t in self.tracks if q in t.display_name.lower()]
