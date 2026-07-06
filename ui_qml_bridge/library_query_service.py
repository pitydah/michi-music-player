"""LibraryQueryService — paginated DB queries with full role set and typed errors."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("michi.library_query")


class LibraryQueryError(Exception):
    def __init__(self, code: str, operation: str, safe_message: str = ""):
        self.code = code
        self.operation = operation
        self.safe_message = safe_message or code
        super().__init__(self.safe_message)


_TRACK_SORT = {
    "title": "LOWER(COALESCE(title, ''))",
    "artist": "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))",
    "album": "LOWER(COALESCE(album, ''))",
    "year": "COALESCE(year, 0)",
    "duration": "COALESCE(duration, 0)",
    "format": "LOWER(COALESCE(ext, ''))",
    "added": "COALESCE(created_at, 0)",
    "play_count": "COALESCE(play_count, 0)",
}

_ALBUM_SORT = {
    "year": "MIN(year)", "title": "LOWER(COALESCE(MIN(album), ''))",
    "artist": "LOWER(COALESCE(MIN(NULLIF(albumartist,'')), MIN(artist), ''))",
    "duration": "SUM(COALESCE(duration, 0))", "track_count": "COUNT(*)",
}

_ARTIST_SORT = {
    "name": "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))",
    "track_count": "COUNT(*)", "album_count": "COUNT(DISTINCT COALESCE(album, ''))",
}


def _sort_col(sort: str, table: str = "tracks") -> str:
    if table == "albums":
        return _ALBUM_SORT.get(sort, "MIN(year)")
    if table == "artists":
        return _ARTIST_SORT.get(sort, "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))")
    return _TRACK_SORT.get(sort, "LOWER(COALESCE(title, ''))")


def _album_key_sql() -> str:
    return "COALESCE(NULLIF(album_key, ''), album, '')"


def _artist_key_sql() -> str:
    return "COALESCE(NULLIF(albumartist, ''), artist, '')"


class LibraryQueryService:
    def __init__(self, db):
        self._db = db

    def _check_db(self):
        if not self._db:
            raise LibraryQueryError("NO_DB", "query", "Base de datos no disponible")

    def _build_where(self, search: str = "", artist: str = "", album: str = "",
                     genre: str = "", fmt: str = "", folder: str = "",
                     year: str = "", quality: str = "",
                     missing_artist: bool = False, missing_album: bool = False,
                     missing_file: bool = False) -> tuple[str, list]:
        clauses = []
        params: list = []
        if search:
            clauses.append("(title LIKE ? OR artist LIKE ? OR album LIKE ? COLLATE NOCASE)")
            p = f"%{search}%"
            params.extend([p, p, p])
        if artist:
            clauses.append(f"({_artist_key_sql()} = ? OR artist = ?)")
            params.extend([artist, artist])
        if album:
            clauses.append(f"({_album_key_sql()} = ? OR album = ?)")
            params.extend([album, album])
        if genre:
            clauses.append("genre = ?")
            params.append(genre)
        if fmt:
            clauses.append("LOWER(ext) = ?")
            params.append(f".{fmt.lower()}")
        if folder:
            clauses.append("directory LIKE ?")
            params.append(f"{folder}%")
        if year:
            clauses.append("year = ?")
            params.append(int(year))
        if missing_artist:
            clauses.append(f"({_artist_key_sql()} = '' OR {_artist_key_sql()} IS NULL)")
        if missing_album:
            clauses.append("(album = '' OR album IS NULL)")
        where = "AND " + " AND ".join(clauses) if clauses else ""
        return where, params

    def count_tracks(self, **kwargs) -> int:
        self._check_db()
        try:
            where, params = self._build_where(**kwargs)
            row = self._db.conn.execute(
                f"SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL {where}", params
            ).fetchone()
            return row[0] if row else 0
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "count_tracks", str(e)) from e

    def fetch_tracks(self, offset: int = 0, limit: int = 100, **kwargs) -> list[dict[str, Any]]:
        self._check_db()
        try:
            where, params = self._build_where(**kwargs)
            sort = _sort_col(kwargs.get("sort", "title"), "tracks")
            order = "ASC" if kwargs.get("asc", True) else "DESC"
            sql = (
                f"SELECT id, filepath, filename, ext, duration, title, artist, album, "
                f"albumartist, year, genre, track_number, track_total, disc_number, disc_total, "
                f"bitrate, sample_rate, bit_depth, channels, play_count, last_played, "
                f"album_key, track_uid, created_at "
                f"FROM media_items WHERE deleted_at IS NULL {where} "
                f"ORDER BY {sort} {order} LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._db.conn.execute(sql, params).fetchall()
            return [self._row_to_public(r) for r in rows]
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_tracks", str(e)) from e

    def count_albums(self, **kwargs) -> int:
        self._check_db()
        try:
            where, params = self._build_where(**kwargs)
            row = self._db.conn.execute(
                f"SELECT COUNT(DISTINCT {_album_key_sql()}) FROM media_items WHERE deleted_at IS NULL "
                f"AND COALESCE(album, '') != '' {where}", params
            ).fetchone()
            return row[0] if row else 0
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "count_albums", str(e)) from e

    def fetch_albums(self, offset: int = 0, limit: int = 100, **kwargs) -> list[dict[str, Any]]:
        self._check_db()
        try:
            where, params = self._build_where(**kwargs)
            sort = _sort_col(kwargs.get("sort", "year"), "albums")
            order = "ASC" if kwargs.get("asc", False) else "DESC"
            sql = (
                f"SELECT {_album_key_sql()} as album_key, album, "
                f"COALESCE(NULLIF(albumartist,''), artist, '') as album_artist, "
                f"MIN(year) as year, COUNT(*) as track_count, SUM(duration) as duration, "
                f"MAX(genre) as genre "
                f"FROM media_items WHERE deleted_at IS NULL AND COALESCE(album, '') != '' {where} "
                f"GROUP BY {_album_key_sql()} "
                f"ORDER BY {sort} {order} LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._db.conn.execute(sql, params).fetchall()
            return [self._album_row_to_dict(r) for r in rows]
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_albums", str(e)) from e

    def count_artists(self, **kwargs) -> int:
        self._check_db()
        try:
            where, params = self._build_where(**kwargs)
            row = self._db.conn.execute(
                f"SELECT COUNT(DISTINCT {_artist_key_sql()}) FROM media_items WHERE deleted_at IS NULL "
                f"AND COALESCE(artist, '') != '' {where}", params
            ).fetchone()
            return row[0] if row else 0
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "count_artists", str(e)) from e

    def fetch_artists(self, offset: int = 0, limit: int = 100, **kwargs) -> list[dict[str, Any]]:
        self._check_db()
        try:
            where, params = self._build_where(**kwargs)
            sort = _sort_col(kwargs.get("sort", "name"), "artists")
            order = "ASC" if kwargs.get("asc", True) else "DESC"
            sql = (
                f"SELECT {_artist_key_sql()} as artist_name, "
                f"COUNT(*) as track_count, COUNT(DISTINCT COALESCE(album, '')) as album_count, "
                f"SUM(duration) as duration "
                f"FROM media_items WHERE deleted_at IS NULL AND COALESCE(artist, '') != '' {where} "
                f"GROUP BY artist_name ORDER BY {sort} {order} LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._db.conn.execute(sql, params).fetchall()
            return [self._artist_row_to_dict(r) for r in rows]
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_artists", str(e)) from e

    # ── Internal methods (return filepath) ──

    def fetch_track_internal(self, track_id: int) -> dict | None:
        self._check_db()
        try:
            row = self._db.conn.execute(
                "SELECT id, filepath, title, artist, album, duration, track_uid, album_key "
                "FROM media_items WHERE id=? AND deleted_at IS NULL", (track_id,)
            ).fetchone()
            if row:
                return {"track_id": row[0], "filepath": row[1], "title": row[2] or "",
                        "artist": row[3] or "", "album": row[4] or "", "duration": row[5] or 0,
                        "track_uid": row[6] or "", "album_key": row[7] or ""}
            return None
        except Exception as e:
            raise LibraryQueryError("NOT_FOUND", "fetch_track_internal", str(e)) from e

    def fetch_album_tracks_internal(self, album_key: str) -> list[dict]:
        self._check_db()
        try:
            rows = self._db.conn.execute(
                "SELECT id, filepath, title, artist, duration, track_number, track_uid "
                f"FROM media_items WHERE deleted_at IS NULL AND {_album_key_sql()}=? "
                "ORDER BY COALESCE(track_number, 999), title", (album_key,)
            ).fetchall()
            return [{"track_id": r[0], "filepath": r[1], "title": r[2] or "",
                     "artist": r[3] or "", "duration": r[4] or 0,
                     "track_number": r[5] or 0, "track_uid": r[6] or ""} for r in rows]
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_album_tracks_internal", str(e)) from e

    def fetch_artist_tracks_internal(self, artist_name: str) -> list[dict]:
        self._check_db()
        try:
            rows = self._db.conn.execute(
                "SELECT id, filepath, title, album, duration, track_number, track_uid, album_key "
                f"FROM media_items WHERE deleted_at IS NULL AND "
                f"({_artist_key_sql()}=? OR artist=?) "
                "ORDER BY COALESCE(album, ''), COALESCE(track_number, 999), title",
                (artist_name, artist_name)
            ).fetchall()
            return [{"track_id": r[0], "filepath": r[1], "title": r[2] or "", "album": r[3] or "",
                     "duration": r[4] or 0, "track_number": r[5] or 0, "track_uid": r[6] or "",
                     "album_key": r[7] or ""} for r in rows]
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_artist_tracks_internal", str(e)) from e

    def fetch_folder_tracks_internal(self, folder_path: str) -> list[dict]:
        self._check_db()
        try:
            rows = self._db.conn.execute(
                "SELECT id, filepath, title, artist, album, duration, track_uid "
                "FROM media_items WHERE deleted_at IS NULL AND directory LIKE ? "
                "ORDER BY title", (f"{folder_path}%",)
            ).fetchall()
            return [{"track_id": r[0], "filepath": r[1], "title": r[2] or "",
                     "artist": r[3] or "", "album": r[4] or "", "duration": r[5] or 0,
                     "track_uid": r[6] or ""} for r in rows]
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_folder_tracks_internal", str(e)) from e

    # ── Public detail methods (no filepath) ──

    def fetch_album_detail(self, album_key: str) -> dict | None:
        try:
            internal = self.fetch_album_tracks_internal(album_key)
            if not internal:
                return None
            return {"album_key": album_key, "track_count": len(internal),
                    "tracks": [{k: v for k, v in t.items() if k != "filepath"} for t in internal]}
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_album_detail", str(e)) from e

    def fetch_artist_detail(self, artist_name: str) -> dict | None:
        try:
            internal = self.fetch_artist_tracks_internal(artist_name)
            if not internal:
                return None
            albums: set = set()
            for t in internal:
                if t.get("album"):
                    albums.add(t["album"])
            return {"artist": artist_name, "track_count": len(internal),
                    "album_count": len(albums),
                    "tracks": [{k: v for k, v in t.items() if k != "filepath"} for t in internal]}
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_artist_detail", str(e)) from e

    # ── Row converters ──

    def _row_to_public(self, r) -> dict[str, Any]:
        album_key = r[21] or r[7] or ""
        return {
            "track_id": r[0], "track_uid": r[22] or "", "public_ref": f"track_{r[0]}",
            "filename": r[2] or "", "format": (r[3] or "").lstrip(".").upper(),
            "duration": r[4] or 0, "title": r[5] or "", "artist": r[6] or "",
            "album": r[7] or "", "albumartist": r[8] or "", "album_key": album_key,
            "year": r[9] or 0, "genre": r[10] or "", "track_number": r[11] or 0,
            "track_total": r[12] or 0, "disc_number": r[13] or 0, "disc_total": r[14] or 0,
            "bitrate": r[15] or 0, "sample_rate": r[16] or 0, "bit_depth": r[17] or 0,
            "channels": r[18] or 0, "play_count": r[19] or 0, "last_played": r[20] or 0,
            "cover_key": album_key, "missing": False, "source_type": "local_file",
        }

    def _album_row_to_dict(self, r) -> dict:
        return {
            "album_key": r[0] or "", "title": r[1] or "", "artist": r[2] or "",
            "year": r[3] or 0, "track_count": r[4] or 0, "duration": r[5] or 0,
            "genre": r[6] or "", "cover_key": r[0] or "",
        }

    def _artist_row_to_dict(self, r) -> dict:
        return {
            "name": r[0] or "", "track_count": r[1] or 0,
            "album_count": r[2] or 0, "duration": r[3] or 0,
        }

    @property
    def search_backend(self) -> str:
        if not self._db:
            return "none"
        try:
            row = self._db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='virtual_table' AND name='media_fts'"
            ).fetchone()
            return "fts5" if row else "like"
        except Exception:
            return "none"
