"""Filter-safe and index-aware query facade for the QML library.

This facade owns the complete QML filter contract and uses the normalized
metadata columns introduced by migration 6.  The legacy delegate remains the
canonical connection/error boundary and supplies unrelated domain methods.
"""
from __future__ import annotations

from typing import Any

from library.metadata_normalizer import normalize_sort_text

_NORM_TITLE = "COALESCE(NULLIF(m.normalized_title, ''), LOWER(COALESCE(m.title, '')))"
_NORM_ARTIST = (
    "COALESCE(NULLIF(m.normalized_albumartist, ''), "
    "NULLIF(m.normalized_artist, ''), "
    "LOWER(COALESCE(NULLIF(m.albumartist, ''), m.artist, '')))"
)
_NORM_ALBUM = "COALESCE(NULLIF(m.normalized_album, ''), LOWER(COALESCE(m.album, '')))"
_ARTIST_DISPLAY = "COALESCE(NULLIF(m.albumartist, ''), m.artist, '')"
_ALBUM_KEY = "COALESCE(NULLIF(m.album_key, ''), m.album, '')"
_MISSING_STATUSES = "('missing', 'not_found', 'offline', 'unavailable')"

_TRACK_SORT = {
    "title": _NORM_TITLE,
    "artist": _NORM_ARTIST,
    "album": _NORM_ALBUM,
    "year": "COALESCE(m.year, 0)",
    "duration": "COALESCE(m.duration, 0)",
    "format": "LOWER(LTRIM(COALESCE(m.ext, ''), '.'))",
    "added": "COALESCE(m.created_at, m.date_added, 0)",
    "play_count": "COALESCE(m.play_count, 0)",
    "track_number": "COALESCE(m.disc_number, 0), COALESCE(m.track_number, 0)",
    "metadata": "COALESCE(m.metadata_completeness, 0)",
}

_ALBUM_SORT = {
    "title": "MIN(" + _NORM_ALBUM + ")",
    "artist": "MIN(" + _NORM_ARTIST + ")",
    "year": "COALESCE(MIN(NULLIF(m.year, 0)), 0)",
    "track_count": "COUNT(*)",
    "duration": "SUM(COALESCE(m.duration, 0))",
    "metadata": "AVG(COALESCE(m.metadata_completeness, 0))",
}

_ARTIST_SORT = {
    "name": "MIN(" + _NORM_ARTIST + ")",
    "track_count": "COUNT(*)",
    "album_count": "COUNT(DISTINCT " + _ALBUM_KEY + ")",
    "duration": "SUM(COALESCE(m.duration, 0))",
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _fts_query(search: str) -> str:
    words = []
    for word in search.split():
        cleaned = word.replace('"', "").strip()
        if cleaned:
            words.append(f'"{cleaned}"*')
    return " OR ".join(words)


class LibraryFilteredQueryService:
    """Proxy that provides stable filters, deterministic order and fast grouping."""

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
            query = _fts_query(search)
            if query:
                clauses.append(
                    "m.id IN (SELECT rowid FROM media_fts WHERE media_fts MATCH ?)"
                )
                params.append(query)
        elif search:
            normalized = normalize_sort_text(search)
            pattern = f"%{_escape_like(normalized)}%"
            raw_pattern = f"%{_escape_like(search)}%"
            clauses.append(
                f"({_NORM_TITLE} LIKE ? ESCAPE '\\' OR "
                f"{_NORM_ARTIST} LIKE ? ESCAPE '\\' OR "
                f"{_NORM_ALBUM} LIKE ? ESCAPE '\\' OR "
                "m.composer LIKE ? ESCAPE '\\' COLLATE NOCASE)"
            )
            params.extend([pattern, pattern, pattern, raw_pattern])

        artist = str(filters.get("artist") or "").strip()
        if artist:
            normalized = normalize_sort_text(artist)
            clauses.append(
                f"({_NORM_ARTIST}=? OR m.artist=? COLLATE NOCASE "
                "OR m.albumartist=? COLLATE NOCASE)"
            )
            params.extend([normalized, artist, artist])

        album = str(filters.get("album") or "").strip()
        if album:
            normalized = normalize_sort_text(album)
            clauses.append(
                f"({_ALBUM_KEY}=? COLLATE NOCASE OR {_NORM_ALBUM}=?)"
            )
            params.extend([album, normalized])

        genre = str(filters.get("genre") or "").strip()
        if genre:
            clauses.append("m.genre=? COLLATE NOCASE")
            params.append(genre)

        composer = str(filters.get("composer") or "").strip()
        if composer:
            clauses.append("m.composer=? COLLATE NOCASE")
            params.append(composer)

        fmt = str(filters.get("fmt") or "").strip().lower().lstrip(".")
        if fmt:
            clauses.append("LOWER(LTRIM(m.ext, '.'))=?")
            params.append(fmt)

        folder = str(filters.get("folder") or "").strip().rstrip("/\\")
        if folder:
            clauses.append("(m.directory=? OR m.directory LIKE ? ESCAPE '\\')")
            params.extend([folder, f"{_escape_like(folder)}/%"])

        year = str(filters.get("year") or "").strip()
        if year:
            try:
                parsed_year = int(year)
            except (TypeError, ValueError):
                clauses.append("1=0")
            else:
                clauses.append("m.year=?")
                params.append(parsed_year)

        quality = str(filters.get("quality") or "").strip()
        if quality:
            clauses.append("m.quality=? COLLATE NOCASE")
            params.append(quality)

        if bool(filters.get("favorites")):
            clauses.append(
                "EXISTS (SELECT 1 FROM favorites f WHERE "
                "f.track_id=m.filepath OR f.track_id=CAST(m.id AS TEXT) "
                "OR f.track_id=m.track_uid)"
            )

        if bool(filters.get("unplayed")):
            clauses.append("COALESCE(m.play_count, 0)=0")

        if bool(filters.get("missing") or filters.get("missing_file")):
            clauses.append(
                f"LOWER(COALESCE(m.scan_status, '')) IN {_MISSING_STATUSES}"
            )

        if bool(filters.get("missing_artist")):
            clauses.append("COALESCE(m.artist, '')='' AND COALESCE(m.albumartist, '')=''")

        if bool(filters.get("missing_album")):
            clauses.append("COALESCE(m.album, '')=''")

        minimum_metadata = filters.get("metadata_min")
        if minimum_metadata not in (None, ""):
            try:
                minimum = max(0, min(100, int(minimum_metadata)))
            except (TypeError, ValueError):
                clauses.append("1=0")
            else:
                clauses.append("COALESCE(m.metadata_completeness, 0)>=?")
                params.append(minimum)

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
            "m.track_uid, COALESCE(m.created_at, m.date_added, 0), m.composer, "
            "EXISTS (SELECT 1 FROM favorites f WHERE f.track_id=m.filepath "
            "OR f.track_id=CAST(m.id AS TEXT) OR f.track_id=m.track_uid) AS favorite, "
            f"LOWER(COALESCE(m.scan_status, '')) IN {_MISSING_STATUSES} AS missing, "
            "m.metadata_completeness, m.metadata_confidence, m.metadata_source, "
            "m.metadata_issues, m.metadata_hash "
            "FROM media_items m "
            f"WHERE m.deleted_at IS NULL{where} "
            f"ORDER BY {sort_column} {order}, {_NORM_TITLE} ASC, m.id ASC "
            "LIMIT ? OFFSET ?"
        )
        params.extend([max(1, int(limit)), max(0, int(offset))])
        rows = self._delegate._exec(sql, params).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = self._delegate._row_to_public(row)
            item.update({
                "metadata_completeness": int(row[27] or 0),
                "metadata_confidence": float(row[28] or 0.0),
                "metadata_source": row[29] or "",
                "metadata_issues": row[30] or "[]",
                "metadata_hash": row[31] or "",
            })
            result.append(item)
        return result

    def count_albums(self, **filters) -> int:
        self._delegate._check_db()
        where, params = self._build_track_where(**filters)
        row = self._delegate._exec(
            f"SELECT COUNT(DISTINCT {_ALBUM_KEY}) FROM media_items m "
            "WHERE m.deleted_at IS NULL AND COALESCE(m.album, '')!=''"
            f"{where}",
            params,
        ).fetchone()
        return int(row[0]) if row else 0

    def fetch_albums(self, offset: int = 0, limit: int = 100,
                     **filters) -> list[dict[str, Any]]:
        self._delegate._check_db()
        sort_key = str(filters.pop("sort", "year"))
        ascending = bool(filters.pop("asc", False))
        sort_column = _ALBUM_SORT.get(sort_key, _ALBUM_SORT["year"])
        order = "ASC" if ascending else "DESC"
        where, params = self._build_track_where(**filters)
        sql = (
            f"SELECT {_ALBUM_KEY} AS album_key, MAX(m.album) AS album, "
            f"MAX({_ARTIST_DISPLAY}) AS album_artist, "
            "COALESCE(MIN(NULLIF(m.year, 0)), 0) AS year, "
            "COUNT(*) AS track_count, SUM(COALESCE(m.duration, 0)) AS duration, "
            "MAX(m.genre) AS genre, COUNT(DISTINCT COALESCE(m.disc_number, 0)) AS disc_count, "
            "GROUP_CONCAT(DISTINCT UPPER(LTRIM(COALESCE(m.ext, ''), '.'))) AS formats, "
            "MAX(COALESCE(m.sample_rate, 0)) AS max_sample_rate, "
            "MAX(COALESCE(m.bit_depth, 0)) AS max_bit_depth, "
            "ROUND(AVG(COALESCE(m.metadata_completeness, 0)), 1) AS metadata_completeness "
            "FROM media_items m WHERE m.deleted_at IS NULL "
            "AND COALESCE(m.album, '')!=''"
            f"{where} GROUP BY album_key "
            f"ORDER BY {sort_column} {order}, MIN({_NORM_ALBUM}) ASC, album_key ASC "
            "LIMIT ? OFFSET ?"
        )
        params.extend([max(1, int(limit)), max(0, int(offset))])
        rows = self._delegate._exec(sql, params).fetchall()
        result = []
        for row in rows:
            year = int(row[3] or 0)
            result.append({
                "album_key": row[0] or "",
                "title": row[1] or "",
                "artist": row[2] or "",
                "year": year,
                "track_count": int(row[4] or 0),
                "duration": float(row[5] or 0),
                "genre": row[6] or "",
                "cover_key": row[0] or "",
                "decade": (year // 10 * 10) if year else 0,
                "disc_count": int(row[7] or 0),
                "formats": row[8] or "",
                "max_sample_rate": int(row[9] or 0),
                "max_bit_depth": int(row[10] or 0),
                "metadata_completeness": float(row[11] or 0),
            })
        return result

    def count_artists(self, **filters) -> int:
        self._delegate._check_db()
        where, params = self._build_track_where(**filters)
        row = self._delegate._exec(
            f"SELECT COUNT(DISTINCT {_NORM_ARTIST}) FROM media_items m "
            "WHERE m.deleted_at IS NULL AND COALESCE(m.artist, m.albumartist, '')!=''"
            f"{where}",
            params,
        ).fetchone()
        return int(row[0]) if row else 0

    def fetch_artists(self, offset: int = 0, limit: int = 100,
                      **filters) -> list[dict[str, Any]]:
        self._delegate._check_db()
        sort_key = str(filters.pop("sort", "name"))
        ascending = bool(filters.pop("asc", True))
        sort_column = _ARTIST_SORT.get(sort_key, _ARTIST_SORT["name"])
        order = "ASC" if ascending else "DESC"
        where, params = self._build_track_where(**filters)
        sql = (
            f"SELECT MAX({_ARTIST_DISPLAY}) AS artist_name, COUNT(*) AS track_count, "
            f"COUNT(DISTINCT {_ALBUM_KEY}) AS album_count, "
            "SUM(COALESCE(m.duration, 0)) AS duration, "
            "ROUND(AVG(COALESCE(m.metadata_completeness, 0)), 1) "
            "FROM media_items m WHERE m.deleted_at IS NULL "
            "AND COALESCE(m.artist, m.albumartist, '')!=''"
            f"{where} GROUP BY {_NORM_ARTIST} "
            f"ORDER BY {sort_column} {order}, MIN({_NORM_ARTIST}) ASC "
            "LIMIT ? OFFSET ?"
        )
        params.extend([max(1, int(limit)), max(0, int(offset))])
        rows = self._delegate._exec(sql, params).fetchall()
        return [{
            "name": row[0] or "",
            "track_count": int(row[1] or 0),
            "album_count": int(row[2] or 0),
            "duration": float(row[3] or 0),
            "metadata_completeness": float(row[4] or 0),
        } for row in rows]

    def fetch_album_tracks_internal(self, album_key: str) -> list[dict]:
        self._delegate._check_db()
        rows = self._delegate._exec(
            "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.albumartist, "
            "m.duration, m.track_number, m.track_uid, m.year, m.genre, m.ext, "
            "m.sample_rate, m.bit_depth, m.album_key, m.disc_number, m.disc_total, "
            "m.track_total, m.metadata_completeness "
            f"FROM media_items m WHERE m.deleted_at IS NULL AND {_ALBUM_KEY}=? "
            f"ORDER BY COALESCE(m.disc_number, 0), COALESCE(m.track_number, 999), "
            f"{_NORM_TITLE}, m.id",
            (album_key,),
        ).fetchall()
        return [{
            "track_id": row[0], "filepath": row[1], "title": row[2] or "",
            "artist": row[3] or "", "album": row[4] or "",
            "album_artist": row[5] or "", "duration": row[6] or 0,
            "track_number": row[7] or 0, "track_uid": row[8] or "",
            "year": row[9] or 0, "genre": row[10] or "",
            "format": row[11] or "", "sample_rate": row[12] or 0,
            "bit_depth": row[13] or 0, "album_key": row[14] or album_key,
            "cover_key": row[14] or album_key, "disc_number": row[15] or 0,
            "disc_total": row[16] or 0, "track_total": row[17] or 0,
            "metadata_completeness": row[18] or 0,
        } for row in rows]

    def fetch_artist_tracks_internal(self, artist_name: str) -> list[dict]:
        self._delegate._check_db()
        normalized = normalize_sort_text(artist_name)
        rows = self._delegate._exec(
            "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.albumartist, "
            "m.duration, m.track_number, m.track_uid, m.album_key, m.year, m.genre, "
            "m.ext, m.sample_rate, m.bit_depth, m.disc_number "
            f"FROM media_items m WHERE m.deleted_at IS NULL AND {_NORM_ARTIST}=? "
            f"ORDER BY {_NORM_ALBUM}, COALESCE(m.disc_number, 0), "
            f"COALESCE(m.track_number, 999), {_NORM_TITLE}, m.id",
            (normalized,),
        ).fetchall()
        return [{
            "track_id": row[0], "filepath": row[1], "title": row[2] or "",
            "artist": row[3] or "", "album": row[4] or "",
            "album_artist": row[5] or "", "duration": row[6] or 0,
            "track_number": row[7] or 0, "track_uid": row[8] or "",
            "album_key": row[9] or "", "year": row[10] or 0,
            "genre": row[11] or "", "format": row[12] or "",
            "sample_rate": row[13] or 0, "bit_depth": row[14] or 0,
            "disc_number": row[15] or 0, "cover_key": row[9] or "",
        } for row in rows]

    def fetch_folder_tracks_internal(self, folder_path: str) -> list[dict]:
        self._delegate._check_db()
        folder = str(folder_path or "").rstrip("/\\")
        rows = self._delegate._exec(
            "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.duration, m.track_uid "
            "FROM media_items m WHERE m.deleted_at IS NULL "
            "AND (m.directory=? OR m.directory LIKE ? ESCAPE '\\') "
            f"ORDER BY {_NORM_ARTIST}, {_NORM_ALBUM}, {_NORM_TITLE}, m.id",
            (folder, f"{_escape_like(folder)}/%"),
        ).fetchall()
        return [{
            "track_id": row[0], "filepath": row[1], "title": row[2] or "",
            "artist": row[3] or "", "album": row[4] or "",
            "duration": row[5] or 0, "track_uid": row[6] or "",
        } for row in rows]

    def recently_played(self, limit: int = 30) -> list[dict]:
        """Return recent plays from the real media_items/play_history schema."""
        self._delegate._check_db()
        rows = self._delegate._exec(
            "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.duration, "
            "m.album_key, m.track_uid, MAX(h.played_at) AS played_at "
            "FROM play_history h JOIN media_items m ON "
            "h.track_id=CAST(m.id AS TEXT) OR h.track_id=m.track_uid "
            "OR h.track_id=m.filepath "
            "WHERE m.deleted_at IS NULL GROUP BY m.id "
            "ORDER BY played_at DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
        return [{
            "track_id": row[0], "filepath": row[1], "title": row[2] or "",
            "artist": row[3] or "", "album": row[4] or "",
            "duration": row[5] or 0, "album_key": row[6] or "",
            "track_uid": row[7] or "", "played_at": row[8] or 0,
        } for row in rows]

    def catalogue_metadata_summary(self) -> dict[str, Any]:
        """Return compact health metrics for Library Doctor and future UI badges."""
        self._delegate._check_db()
        row = self._delegate._exec(
            "SELECT COUNT(*), ROUND(AVG(COALESCE(metadata_completeness, 0)), 1), "
            "SUM(CASE WHEN COALESCE(metadata_completeness, 0)<50 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN COALESCE(artist, '')='' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN COALESCE(album, '')='' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN COALESCE(metadata_hash, '')='' THEN 1 ELSE 0 END) "
            "FROM media_items WHERE deleted_at IS NULL"
        ).fetchone()
        return {
            "track_count": int(row[0] or 0),
            "average_completeness": float(row[1] or 0),
            "low_quality_count": int(row[2] or 0),
            "missing_artist_count": int(row[3] or 0),
            "missing_album_count": int(row[4] or 0),
            "unhashed_count": int(row[5] or 0),
        } if row else {
            "track_count": 0, "average_completeness": 0.0,
            "low_quality_count": 0, "missing_artist_count": 0,
            "missing_album_count": 0, "unhashed_count": 0,
        }
