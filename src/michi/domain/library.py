"""Library domain state — pure, no Qt/infra dependencies."""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from michi.domain.search import SearchProjection  # M7: derived search state

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
    compilation + technical audio facts: codec/container/sample_rate/bit
    depth/channels/bitrate/file_size — M6-PRODUCTION-INTEGRATION retains the
    technical carrier so canonical runtime projections can show facts)"""

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
    sort_title: str = ""
    codec: str = ""
    container: str = ""
    sample_rate_hz: int = 0
    bit_depth: int = 0
    channels: int = 0
    bitrate_bps: int = 0
    file_size: int = 0

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


class LibraryScanStatus(Enum):
    """Async scan lifecycle (M6.4). The scan-state contract arms on
    start_scan and lands on a terminal status (COMPLETED/CANCELLED/FAILED)
    on the owner thread; the synchronous scan() fallback never touches it."""

    IDLE = auto()
    DISCOVERING = auto()
    INDEXING = auto()
    EXTRACTING = auto()
    COMMITTING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    FAILED = auto()


class AlbumTechnicalState(Enum):
    """Structured album technical state (M6-FINAL-CROSS-PERSISTENCE-GATE)."""

    EXACT = auto()
    MIXED = auto()
    PARTIAL = auto()
    UNKNOWN = auto()


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
    disc_count: int = 0
    genres: tuple[str, ...] = ()
    composers: tuple[str, ...] = ()
    technical_summary: str = ""


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
class ComposerRef:
    """Canonical composer reference derived from library tracks (M6.1)."""

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
    composers: tuple[ComposerRef, ...] = ()


def _normalize_key(s: str) -> str:
    """Canonical grouping key: casefolded, whitespace runs collapsed, stripped."""
    return " ".join(s.casefold().split())


_UNKNOWN_ALBUM = "Unknown Album"
_UNKNOWN_ARTIST = "Unknown Artist"
_UNKNOWN_GENRE = "Unknown Genre"
_UNKNOWN_COMPOSER = "Unknown Composer"
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


def make_track_id(file_path) -> str:
    """Canonical track identity (M6.1): the serialized path itself.

    Paths are case-sensitive on the local filesystem — NO casefold (a
    different case is a different file). Deterministic and serializable."""
    return str(Path(file_path))


def make_genre_key(genre_name: str) -> str:
    """Canonical genre identity (M6.1): normalized name."""
    return _normalize_key(genre_name)


def make_composer_key(composer_name: str) -> str:
    """Canonical composer identity (M6.1): normalized name."""
    return _normalize_key(composer_name)


def _resolve_album_artist(track) -> str:
    """Resolved album-level artist (LOCAL-META-02.2c): an explicit
    ``album_artist`` wins; a compilation without one groups under
    "Various Artists"; otherwise the track's own artist."""
    if track.album_artist:
        return track.album_artist
    if track.compilation:
        return _VARIOUS_ARTISTS
    return track.artist


def _canonical_track_sort_key(track) -> tuple:
    """Canonical per-album track ordering (M6.1): (disc>0 or 10**6,
    track>0 or 10**6, casefolded sort title or title, path). UNKNOWN (0)
    sorts deterministically LAST within its dimension — never invented as 1."""
    return (
        track.disc_number if track.disc_number > 0 else 10**6,
        track.track_number if track.track_number > 0 else 10**6,
        (track.sort_title or track.title or "").casefold(),
        str(track.file_path),
    )


def render_technical_label(codec, bit_depth, sample_rate_hz, bitrate_bps) -> str:
    """Honest technical-quality label (facts only — never marketing).

    - Lossless (bit_depth > 0 and sample_rate_hz > 0):
      "FLAC · 24-bit · 96 kHz" (kHz with up to 1 decimal).
    - Lossy (bit_depth == 0 and bitrate_bps > 0): "MP3 · 320 kbps".
    - Bare codec when only the codec is known; "" when nothing is known."""
    if bit_depth > 0 and sample_rate_hz > 0:
        khz = sample_rate_hz / 1000
        return f"{codec} · {bit_depth}-bit · {khz:g} kHz"
    if bit_depth == 0 and bitrate_bps > 0:
        return f"{codec} · {bitrate_bps // 1000} kbps"
    return codec or ""


def _album_technical_state(tracks) -> "AlbumTechnicalState":
    """Structured album technical state (M6-FINAL-CROSS-PERSISTENCE-GATE):
    EXACT — every member has facts and renders the same label; MIXED —
    every member has facts but renders differently; PARTIAL — some members
    lack technical facts (a definitive album-wide claim would fabricate
    information); UNKNOWN — no member has facts."""
    known = [t for t in tracks if t.codec]
    if not known:
        return AlbumTechnicalState.UNKNOWN
    if any(not t.codec for t in tracks):
        return AlbumTechnicalState.PARTIAL
    labels = {
        render_technical_label(t.codec, t.bit_depth, t.sample_rate_hz, t.bitrate_bps)
        for t in known
    }
    if len(labels) == 1:
        return AlbumTechnicalState.EXACT
    return AlbumTechnicalState.MIXED


def _album_technical_summary(tracks) -> str:
    """Honest album-level technical summary (facts only — never marketing).

    EXACT -> the exact facts-only label; MIXED -> "Mixed formats";
    PARTIAL -> "" (known + unknown must NEVER report a definitive album-wide
    label — UNKNOWN stays UNKNOWN); UNKNOWN -> ""."""
    state = _album_technical_state(tracks)
    if state is AlbumTechnicalState.EXACT:
        first = next(t for t in tracks if t.codec)
        return render_technical_label(
            first.codec, first.bit_depth, first.sample_rate_hz, first.bitrate_bps
        )
    if state is AlbumTechnicalState.MIXED:
        return "Mixed formats"
    return ""


def build_music_model(tracks) -> MusicModel:
    """Derive albums and artists from tracks (pure, deterministic by key).

    Albums are grouped by ``make_album_key(track.album, resolved_album_artist)``
    where the resolved album artist (LOCAL-META-02.2c) is the explicit
    ``album_artist``, else "Various Artists" for compilations, else the track
    artist. Display title/artist come from the first member. Empty album ->
    "Unknown Album", empty artist -> "Unknown Artist". Album duration is the
    sum of members and ``track_paths`` is the CANONICAL member order (M6.1):
    (disc>0 or 10**6, track>0 or 10**6, casefolded sort title or title,
    path) — independent of the scan/insertion order, multi-disc albums are
    Disc 1 tracks then Disc 2 tracks, and UNKNOWN (0) sorts last within its
    dimension. AlbumRef V2 fields (M6.1): ``disc_count`` (distinct non-zero
    disc numbers, 1 when all unknown), ``genres`` and ``composers`` (distinct
    non-empty member values, sorted casefold). AlbumRef PRODUCTION fields
    (M6-PRODUCTION-INTEGRATION): ``year`` is the first canonical-sorted
    member with a known year (0 when none — deterministic under input
    permutation) and ``technical_summary`` is the exact facts-only label when
    every member renders the same one, else "Mixed formats". Artists are
    grouped by normalized track artist (``make_artist_key``) with total track
    count and distinct-album count over CANONICAL AlbumIds (same title under
    a different album artist is a different album). Genres are grouped by
    normalized name with per-genre track count; empty genre -> "Unknown
    Genre". Composers (M6.1) are grouped by normalized name with per-composer
    track count; empty composer -> "Unknown Composer"; the sum of genre counts
    and the sum of composer counts each equal the total track count.
    """
    album_entries: dict[str, dict] = {}
    artist_entries: dict[str, dict] = {}
    genre_entries: dict[str, dict] = {}
    composer_entries: dict[str, dict] = {}
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
                "tracks": [],
            }
            album_entries[album_key] = album
        album["duration_ms"] += track.duration_ms
        album["tracks"].append(track)

        artist_name = track.artist.strip() or _UNKNOWN_ARTIST
        artist_key = make_artist_key(artist_name)
        artist = artist_entries.get(artist_key)
        if artist is None:
            artist = {"name": artist_name, "track_count": 0, "albums": set()}
            artist_entries[artist_key] = artist
        artist["track_count"] += 1
        # M6-PRODUCTION-INTEGRATION: the album count uses the CANONICAL
        # AlbumId (title + resolved album artist), never the bare title —
        # same-title albums under different album artists count separately.
        artist["albums"].add(album_key)

        genre_name = track.genre.strip() or _UNKNOWN_GENRE
        genre_key = _normalize_key(genre_name)
        genre = genre_entries.get(genre_key)
        if genre is None:
            genre = {"name": genre_name, "track_count": 0}
            genre_entries[genre_key] = genre
        genre["track_count"] += 1

        composer_name = track.composer.strip() or _UNKNOWN_COMPOSER
        composer_key = make_composer_key(composer_name)
        composer = composer_entries.get(composer_key)
        if composer is None:
            composer = {"name": composer_name, "track_count": 0}
            composer_entries[composer_key] = composer
        composer["track_count"] += 1

    for entry in album_entries.values():
        tracks_sorted = sorted(entry["tracks"], key=_canonical_track_sort_key)
        entry["paths"] = tuple(t.file_path for t in tracks_sorted)
        # M6-PRODUCTION-INTEGRATION: the canonical album year is the first
        # canonical-sorted track with a known year; 0 when none. NEVER the
        # first member in input order (input-order-independent determinism).
        entry["year"] = next((t.year for t in tracks_sorted if t.year > 0), 0)
        entry["technical_summary"] = _album_technical_summary(tracks_sorted)
        entry["disc_count"] = (
            len({t.disc_number for t in entry["tracks"] if t.disc_number > 0}) or 1
        )
        entry["genres"] = tuple(
            sorted(
                {g for t in entry["tracks"] for g in [t.genre] if g},
                key=str.casefold,
            )
        )
        entry["composers"] = tuple(
            sorted(
                {c for t in entry["tracks"] for c in [t.composer] if c},
                key=str.casefold,
            )
        )

    albums = tuple(
        sorted(
            (
                AlbumRef(
                    key=entry["key"],
                    title=entry["title"],
                    artist=entry["album_artist"],
                    track_count=len(entry["paths"]),
                    duration_ms=entry["duration_ms"],
                    track_paths=entry["paths"],
                    year=entry["year"],
                    disc_count=entry["disc_count"],
                    genres=entry["genres"],
                    composers=entry["composers"],
                    technical_summary=entry["technical_summary"],
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
    composers = tuple(
        sorted(
            (
                ComposerRef(
                    key=key,
                    name=entry["name"],
                    track_count=entry["track_count"],
                )
                for key, entry in composer_entries.items()
            ),
            key=lambda c: c.key,
        )
    )
    return MusicModel(
        albums=albums,
        artists=artists,
        genres=genres,
        composers=composers,
    )


def timeline_decade(year: int) -> str:
    """Canonical timeline decade (M6.1): derived OUTSIDE Presentation."""
    return f"{year // 10 * 10}s" if year > 0 else "Unknown era"


@dataclass(frozen=True)
class TimelineAlbumProjection:
    album_key: str
    title: str
    artist: str
    year: int
    decade: str


def build_timeline_projection(albums) -> tuple[TimelineAlbumProjection, ...]:
    """Canonical timeline projection: sorted by (-year, key); the decade is
    derived here, never in the bridge or QML."""
    rows = [
        TimelineAlbumProjection(
            album_key=a.key,
            title=a.title,
            artist=a.artist,
            year=a.year,
            decade=timeline_decade(a.year),
        )
        for a in albums
    ]
    return tuple(sorted(rows, key=lambda r: (-r.year, r.album_key)))


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
    query: str = ""  # RAW query (presentation form — never normalized here)
    search_projection: SearchProjection | None = None  # M7: derived, inactive when None
    current_directory: str = ""
    diagnostic: LibraryDiagnostic | None = None
    albums: tuple[AlbumRef, ...] = ()
    artists: tuple[ArtistRef, ...] = ()
    genres: tuple[GenreRef, ...] = ()
    composers: tuple[ComposerRef, ...] = ()
    folders: tuple[FolderRef, ...] = ()
    favorite_paths: tuple[str, ...] = ()
    history_paths: tuple[str, ...] = ()
    recently_added_paths: tuple[str, ...] = ()
    scan_status: LibraryScanStatus = LibraryScanStatus.IDLE
    scan_generation: int = 0
    scan_processed: int = 0
    scan_total: int = 0
    scan_progress: float | None = None
    scan_current_path: str | None = None

    @property
    def search_active(self) -> bool:
        """M7: True only while a projection with tokens is active."""
        return (
            self.search_projection is not None
            and self.search_projection.query.active
        )

    @property
    def visible_tracks(self) -> list[TrackRef]:
        """M7: the unified search projection filters the Songs surface; the
        canonical tracks are the passthrough when search is inactive."""
        if not self.search_active:
            return self.tracks
        return list(self.search_projection.tracks)
