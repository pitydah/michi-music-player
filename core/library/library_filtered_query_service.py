"""Complete, filter-safe query facade for the QML library.

The legacy LibraryQueryService intentionally exposes a compact filter surface.  The
QML library has a richer contract (composer, favorites, unplayed and missing
content), so this facade adds those predicates while delegating every unrelated
method to the canonical service.
"""
from __future__ import annotations

from typing import Any


_TRACK_SORT = {
    "title": "LOWER(COALESCE(m.title, ''))",
    "artist": "LOWER(COALESCE(NULLIF(m.albumartist, ''), m.artist, ''))",
    "album": "LOWER(COALESCE(m.album, ''))",
    "year": "COALESCE(m.year, 0)",
    "duration": "COALESCE(m.duration, 0)",
    "format": "LOWER(COALESCE(m.ext, ''))",
    "added": "COALESCE(m.created_at, 0)",
    "play_count": "COALESCE(m.play_count, 0)",
    "track_number": "COALESCE(m.track_number, 0)",
}


class LibraryFilteredQueryService:
    """Proxy that provides a stable, complete track-filter contract."""

    def __init__(self, delegate):
        if delegate is None:
            raise ValueError("LibraryFilteredQueryService requires a delegate")
        self._delegate = delegate

    def __getattr__(self, name: str):
        return getattr(self._delegate, name)

    @property
    def search_backend(self) -> str:
        return self._delegate.search_backend

    def _build_track_where(self, **filters) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        search = str(filters.get("search") or "").strip()
        if search and self.search_backend == "fts5":
            fts_query = " OR ".join(f"{word}*" for word in search.split() if word)
            clauses.append("m.id IN (SELECT rowid FROM media_fts WHERE media_fts MATCH ?)")
            params.append(fts_query)
        elif search:
            pattern = f"%{search}%"
            clauses.append(
                "(m.title LIKE ? COLLATE NOCASE OR m.artist LIKE ? COLLATE NOCASE "
                "OR m.album LIKE ? COLLATE NOCASE OR m.composer LIKE ? COLLATE NOCASE)"
            )
            params.extend([pattern, pattern, pattern, pattern])

        artist = str(filters.get("artist") or "").strip()
        if artist:
            clauses.append(
                "(COALESCE(NULLIF(m.albumartist, ''), m.artist, '') = ? COLLATE NOCASE "
                "OR m.artist = ? COLLATE NOCASE)"
            )
            params.extend([artist, artist])

        album = str(filters.get("album") or "").strip()
        if album:
            clauses.append(
                "(COALESCE(NULLIF(m.album_key, ''), m.album, '') = ? COLLATE NOCASE "
                "OR m.album = ? COLLATE NOCASE)"
            )
            params.extend([album, album])

        genre = str(filters.get("genre") or "").strip()
        if genre:
            clauses.append("m.genre = ? COLLATE NOCASE")
            params.append(genre)

        composer = str(filters.get("composer") or "").strip()
        if composer:
            clauses.append("m.composer = ? COLLATE NOCASE")
            params.append(composer)

        fmt = str(filters.get("fmt") or "").strip().lower().lstrip(".")
        if fmt:
            clauses.append("LOWER(LTRIM(m.ext, '.')) = ?")
            params.append(fmt)

        folder = str(filters.get("folder") or "").strip()
        if folder:
            clauses.append("m.directory LIKE ?")
            params.append(f"{folder}%")

        year = str(filters.get("year") or "").strip()
        if year:
            try:
                parsed_year = int(year)
            except (TypeError, ValueError):
                clauses.append("1 = 0")
            else:
                clauses.append("m.year = ?")
                params.append(parsed_year)

        quality = str(filters.get("quality") or "").strip()
        if quality:
            clauses.append("m.quality = ? COLLATE NOCASE")
            params.append(quality)

        if bool(filters.get("favorites")):
            clauses.append(
                "EXISTS (SELECT 1 FROM favorites f "
                "WHERE f.track_id = m.filepath OR f.track_id = CAST(m.id AS TEXT))"
            )

        if bool(filters.get("unplayed")):
            clauses.append("COALESCE(m.play_count, 0) = 0")

        missing = bool(filters.get("missing") or filters.get("missing_file"))
        if missing:
            clauses.append(
                "LOWER(COALESCE(m.scan_status, '')) IN "
                "('missing', 'not_found', 'offline', 'unavailable')"
            )

        if bool(filters.get("missing_artist")):
            clauses.append(
                "COALESCE(NULLIF(m.albumartist, ''), m.artist, '') = ''"
            )

        if bool(filters.get("missing_album")):
            clauses.append("COALESCE(m.album, '') = ''")

        return (" AND " + " AND ".join(clauses) if clauses else "", params)

    def count_tracks(self, **filters) -> int:
        self._delegate._check_db()
        where, params = self._build_track_where(**filters)
        row = self._delegate._exec(
            f"SELECT COUNT(*) FROM media_items m "
            f"WHERE m.deleted_at IS NULL{where}",
            params,
        ).fetchone()
        return int(row[0]) if row else 0

    def fetch_tracks(self, offset: int = 0, limit: int = 100,
                     **filters) -> list[dict[str, Any]]:
        self._delegate._check_db()
        sort_key = str(filters.pop("sort", "title"))
        ascending = bool(filters.pop("asc", True))
        sort_column = _TRACK_SORT.get(sort_key, _TRACK_SORT["title"])
        order = "ASC" if ascending else "DESC"
        where, params = self._build_track_where(**filters)
        sql = (
            "SELECT m.id, m.filepath, m.filename, m.ext, m.duration, m.title, "
            "m.artist, m.album, m.albumartist, m.year, m.genre, m.track_number, "
            "m.track_total, m.disc_number, m.disc_total, m.bitrate, m.sample_rate, "
            "m.bit_depth, m.channels, m.play_count, m.last_played, m.album_key, "
            "m.track_uid, m.created_at "
            "FROM media_items m "
            f"WHERE m.deleted_at IS NULL{where} "
            f"ORDER BY {sort_column} {order} LIMIT ? OFFSET ?"
        )
        params.extend([max(1, int(limit)), max(0, int(offset))])
        rows = self._delegate._exec(sql, params).fetchall()
        return [self._delegate._row_to_public(row) for row in rows]
