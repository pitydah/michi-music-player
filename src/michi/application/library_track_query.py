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
    """Owns session-lived sorting policy without mutating domain collections."""

    _SORTABLE = frozenset({"title", "artist", "album", "format"})

    def __init__(self) -> None:
        self._state = TrackSortState()

    @property
    def state(self) -> TrackSortState:
        return self._state

    def set_sort(self, column: str) -> None:
        if column not in self._SORTABLE:
            return
        descending = self._state.column == column and not self._state.descending
        next_state = TrackSortState(column, descending)
        if next_state == self._state:
            return
        self._state = next_state

    def sort_tracks(self, tracks: Iterable[TrackRef]) -> list[TrackRef]:
        rows = list(tracks)
        column = self._state.column
        if not column:
            return rows

        def key(ref: TrackRef) -> tuple[str, str]:
            if column == "title":
                value = ref.sort_title or ref.title or ref.display_name
            elif column == "artist":
                value = ref.artist
            elif column == "album":
                value = ref.album
            else:
                value = normalize_track_format(
                    ref.codec, ref.container, ref.file_path, ref.sample_rate_hz
                ).label
            # Stable tie-break: TrackId (legacy-path:: fallback only for
            # pre-catalog records) — M6-EXT-R4-F.
            tiebreak = ref.track_id or f"legacy-path::{ref.file_path}"
            return (value.casefold(), tiebreak)

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
