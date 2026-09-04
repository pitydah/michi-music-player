"""Application-owned query state for canonical Library track sorting."""

from collections.abc import Iterable
from dataclasses import dataclass

from michi.application.library_format import normalize_track_format
from michi.domain.library import AlbumRef, TrackRef, make_genre_key


@dataclass(frozen=True, slots=True)
class TrackSortState:
    column: str = ""
    descending: bool = False


class LibraryTrackQueryService:
    """Owns session-lived sorting policy without mutating domain collections.

    LIB-A §14/15: columnas sortables con comparación TIPADA (texto vs
    numérica) y tie-break estable por TrackId SIEMPRE. La dirección es
    explícita (set_sort_state) — el menú contextual nunca emula
    'Sort Descending' con dos toggles.
    """

    _SORTABLE = frozenset(
        {
            "title",
            "artist",
            "album",
            "format",
            "duration",
            "year",
            "genre",
            "composer",
            "sampleRate",
            "bitDepth",
            "bitrate",
            "channels",
            "fileSize",
        }
    )
    _TEXT_COLUMNS = frozenset(
        {"title", "artist", "album", "format", "genre", "composer"}
    )

    def __init__(self) -> None:
        self._state = TrackSortState()

    @property
    def state(self) -> TrackSortState:
        return self._state

    def set_sort(self, column: str) -> None:
        """Left-click toggle (legacy semantics) — Songs keeps its toggle."""
        if column not in self._SORTABLE:
            return
        descending = self._state.column == column and not self._state.descending
        next_state = TrackSortState(column, descending)
        if next_state == self._state:
            return
        self._state = next_state

    def set_sort_state(self, column: str, descending: bool) -> bool:
        """LIB-A §15: dirección EXPLÍCITA — nunca simular con toggles."""
        if column not in self._SORTABLE:
            return False
        next_state = TrackSortState(column, bool(descending))
        if next_state == self._state:
            return False
        self._state = next_state
        return True

    def _text_value(self, column: str, ref: TrackRef) -> str:
        if column == "title":
            return ref.sort_title or ref.title or ref.display_name
        if column == "artist":
            return ref.artist
        if column == "album":
            return ref.album
        if column == "format":
            return normalize_track_format(
                ref.codec, ref.container, ref.file_path, ref.sample_rate_hz
            ).label
        if column == "genre":
            return ref.genre
        if column == "composer":
            return ref.composer
        return ""

    def _numeric_value(self, column: str, ref: TrackRef):
        if column == "duration":
            return ref.duration_ms
        if column == "year":
            return ref.year
        if column == "sampleRate":
            return ref.sample_rate_hz
        if column == "bitDepth":
            return ref.bit_depth
        if column == "bitrate":
            return ref.bitrate_bps
        if column == "channels":
            return ref.channels
        if column == "fileSize":
            return ref.file_size
        return 0

    def sort_tracks(self, tracks: Iterable[TrackRef]) -> list[TrackRef]:
        rows = list(tracks)
        column = self._state.column
        if not column:
            return rows

        # Comparación TIPADA con tie-break SIEMPRE por TrackId.
        text = column in self._TEXT_COLUMNS

        def key(ref: TrackRef):
            primary = (
                self._text_value(column, ref).casefold()
                if text
                else self._numeric_value(column, ref)
            )
            # Stable tie-break: TrackId (legacy-path:: fallback only for
            # pre-catalog records) — M6-EXT-R4-F.
            tiebreak = ref.track_id or f"legacy-path::{ref.file_path}"
            if text:
                return (primary, tiebreak.casefold())
            return (primary, (ref.track_id or f"legacy-path::{ref.file_path}"))

        return sorted(rows, key=key, reverse=self._state.descending)

    @staticmethod
    def filter_genre(tracks: Iterable[TrackRef], genre_key: str) -> list[TrackRef]:
        if not genre_key:
            return list(tracks)
        return [
            ref
            for ref in tracks
            if make_genre_key(ref.genre.strip() or "Unknown Genre") == genre_key
        ]


@dataclass(frozen=True, slots=True)
class AlbumQueryState:
    sort_mode: str = "title"
    descending: bool = False
    filter_mode: str = "all"


class LibraryAlbumQueryService:
    """Own sorting/filtering for every Library album projection."""

    _SORT_MODES = frozenset({"title", "artist", "year", "tracks", "duration"})
    _FILTER_MODES = frozenset({"all", "artwork", "missingArtwork", "dated", "undated"})

    def __init__(self) -> None:
        self._state = AlbumQueryState()

    @property
    def state(self) -> AlbumQueryState:
        return self._state

    def set_sort_mode(self, mode: str) -> bool:
        if mode not in self._SORT_MODES or mode == self._state.sort_mode:
            return False
        self._state = AlbumQueryState(
            mode, self._state.descending, self._state.filter_mode
        )
        return True

    def set_sort_descending(self, descending: bool) -> bool:
        if descending == self._state.descending:
            return False
        self._state = AlbumQueryState(
            self._state.sort_mode, descending, self._state.filter_mode
        )
        return True

    def set_filter_mode(self, mode: str) -> bool:
        if mode not in self._FILTER_MODES or mode == self._state.filter_mode:
            return False
        self._state = AlbumQueryState(
            self._state.sort_mode, self._state.descending, mode
        )
        return True

    def project(self, albums: Iterable[AlbumRef]) -> list[AlbumRef]:
        mode = self._state.filter_mode
        rows = [
            album
            for album in albums
            if mode == "all"
            or (mode == "artwork" and album.has_artwork)
            or (mode == "missingArtwork" and not album.has_artwork)
            or (mode == "dated" and album.year > 0)
            or (mode == "undated" and album.year <= 0)
        ]

        def key(album: AlbumRef):
            if self._state.sort_mode == "artist":
                primary = album.artist.casefold()
            elif self._state.sort_mode == "year":
                primary = album.year
            elif self._state.sort_mode == "tracks":
                primary = album.track_count
            elif self._state.sort_mode == "duration":
                primary = album.duration_ms
            else:
                primary = album.title.casefold()
            return (primary, album.title.casefold(), album.key)

        return sorted(rows, key=key, reverse=self._state.descending)
