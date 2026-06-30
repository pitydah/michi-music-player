"""SongsQueryService — query, filter, and search songs from the library.

Reuses LibraryDB, SearchEngine, and search_advanced.
No UI dependency.
"""

from __future__ import annotations

from library.media_item import MediaItem


class SongsQueryService:
    """Encapsulates song queries with combined filters.

    Supports format, quality, genre, year range, bitrate, sample rate,
    favorites, metadata status, and file status filters.
    """

    def __init__(self, db):
        self._db = db

    def fetch_all(self) -> list[MediaItem]:
        """Return all non-deleted media items."""
        return self._db.get_all() if self._db else []

    def search(self, query: str = "", limit: int = 5000) -> list[MediaItem]:
        """Search using advanced FTS5 engine."""
        if not query or not self._db:
            return self.fetch_all()
        return self._db.search_advanced(query, limit=limit)

    def filter(self, items: list[MediaItem], *,
               formats: set[str] | None = None,
               qualities: set[str] | None = None,
               genres: set[str] | None = None,
               year_min: int | None = None,
               year_max: int | None = None,
               bitrate_min: int | None = None,
               sample_rate_min: int | None = None,
               fav_ids: set[int] | None = None,
               only_favorites: bool = False,
               only_missing_metadata: bool = False,
               only_missing_cover: bool = False,
               text_filter: str = "",
               ) -> list[MediaItem]:
        """Apply multiple filters in-memory over a list of MediaItems."""
        if not items:
            return []

        result = list(items)
        fav_set = set(fav_ids or [])

        if formats:
            result = [i for i in result if (i.ext or "").lstrip(".").upper() in formats]
        if qualities:
            result = [i for i in result if _match_quality(i, qualities)]
        if genres:
            result = [i for i in result if (i.genre or "").lower() in {g.lower() for g in genres}]
        if year_min is not None:
            result = [i for i in result if (i.year or 0) >= year_min]
        if year_max is not None:
            result = [i for i in result if (i.year or 0) <= year_max]
        if bitrate_min is not None:
            result = [i for i in result if (i.bitrate or 0) >= bitrate_min]
        if sample_rate_min is not None:
            result = [i for i in result if (i.sample_rate or 0) >= sample_rate_min]
        if only_favorites and fav_set:
            result = [i for i in result if getattr(i, 'id', 0) in fav_set
                      or getattr(i, 'filepath', '') in fav_set]
        if only_missing_metadata:
            result = [i for i in result if _is_missing_metadata(i)]
        if only_missing_cover:
            result = [i for i in result if _is_missing_cover(i)]
        if text_filter:
            q = text_filter.lower()
            result = [i for i in result
                      if q in (i.title or "").lower()
                      or q in (i.artist or "").lower()
                      or q in (i.album or "").lower()
                      or q in (i.genre or "").lower()
                      or q in (i.filepath or "").lower()]

        return result

    def distinct_genres(self, items: list[MediaItem] | None = None) -> list[str]:
        """Return distinct genre list, optionally filtered to a subset."""
        if items is None:
            items = self.fetch_all()
        genres: set[str] = set()
        for i in items:
            g = (i.genre or "").strip()
            if g:
                genres.add(g)
        return sorted(genres)

    def distinct_formats(self, items: list[MediaItem] | None = None) -> list[str]:
        if items is None:
            items = self.fetch_all()
        fmts: set[str] = set()
        for i in items:
            f = (i.ext or "").lstrip(".").upper()
            if f:
                fmts.add(f)
        return sorted(fmts)


def _is_missing_metadata(item: MediaItem) -> bool:
    """Check if a MediaItem has incomplete core metadata."""
    return not (item.title and item.artist and item.album and item.genre)


def _is_missing_cover(item: MediaItem) -> bool:
    """Check if a MediaItem likely lacks cover art."""
    from library.cover_art_service import CoverArtService
    if not item.filepath:
        return True
    return CoverArtService.find_cover(item.filepath) is None


_LOSSLESS_EXTS = {"flac", "alac", "wav", "aiff", "ape", "wv"}
_LOSSY_EXTS = {"mp3", "aac", "ogg", "wma", "opus", "m4a"}
_DSD_EXTS = {"dsf", "dff", "dsd"}


def _classify(item: MediaItem) -> str:
    """Return quality category: hires, lossless, lossy, dsd, unknown."""
    ext = (item.ext or "").lower().lstrip(".")
    if ext in _DSD_EXTS:
        return "dsd"
    if ext in _LOSSLESS_EXTS:
        sr = item.sample_rate or 0
        bd = item.bit_depth or 0
        if sr >= 96000 and bd >= 24:
            return "hires"
        return "lossless"
    if ext in _LOSSY_EXTS:
        return "lossy"
    return "unknown"


def _match_quality(item: MediaItem, qualities: set[str]) -> bool:
    return _classify(item) in qualities
