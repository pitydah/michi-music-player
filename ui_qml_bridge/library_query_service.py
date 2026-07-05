"""LibraryQueryService — paginated DB queries for scalable QML models.

Uses LibraryDB + FTS5 directly. No full-table loads.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("michi.library_query")


class LibraryQueryService:
    """Provides paginated, filtered, sorted queries from LibraryDB."""

    def __init__(self, db):
        self._db = db

    def count_tracks(self, search: str = "", artist: str = "", album: str = "",
                     genre: str = "", fmt: str = "") -> int:
        if not self._db:
            return 0
        try:
            where, params = self._build_where(search, artist, album, genre, fmt)
            sql = f"SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL {where}"
            row = self._db.conn.execute(sql, params).fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.debug("count_tracks failed: %s", e)
            return 0

    def fetch_tracks(self, offset: int = 0, limit: int = 100,
                     search: str = "", artist: str = "", album: str = "",
                     genre: str = "", fmt: str = "", sort: str = "title",
                     ascending: bool = True) -> list[dict[str, Any]]:
        if not self._db:
            return []
        try:
            where, params = self._build_where(search, artist, album, genre, fmt)
            order = "ASC" if ascending else "DESC"
            sort_col = self._sort_column(sort)
            sql = (
                f"SELECT id, filepath, filename, ext, duration, title, artist, album, "
                f"albumartist, year, genre, track_number, bitrate, sample_rate, "
                f"bit_depth, channels, play_count, last_played, track_uid, album_key "
                f"FROM media_items WHERE deleted_at IS NULL {where} "
                f"ORDER BY {sort_col} {order} LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._db.conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.debug("fetch_tracks failed: %s", e)
            return []

    def count_albums(self, search: str = "") -> int:
        if not self._db:
            return 0
        try:
            where, params = self._build_where(search)
            sql = f"SELECT COUNT(DISTINCT COALESCE(album_key, album, '')) FROM media_items WHERE deleted_at IS NULL AND COALESCE(album, '') != '' {where}"
            row = self._db.conn.execute(sql, params).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def fetch_albums(self, offset: int = 0, limit: int = 100, search: str = "",
                     sort: str = "year", ascending: bool = False) -> list[dict[str, Any]]:
        if not self._db:
            return []
        try:
            where, params = self._build_where(search)
            order = "ASC" if ascending else "DESC"
            sql = (
                f"SELECT album_key, album, COALESCE(NULLIF(albumartist,''), artist, '') as album_artist, "
                f"MIN(year) as year, COUNT(*) as track_count, SUM(duration) as duration, "
                f"MAX(genre) as genre "
                f"FROM media_items WHERE deleted_at IS NULL AND COALESCE(album, '') != '' {where} "
                f"GROUP BY COALESCE(album_key, album, '') "
                f"ORDER BY {sort} {order} LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._db.conn.execute(sql, params).fetchall()
            return [self._album_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.debug("fetch_albums failed: %s", e)
            return []

    def count_artists(self, search: str = "") -> int:
        if not self._db:
            return 0
        try:
            where, params = self._build_where(search)
            sql = f"SELECT COUNT(DISTINCT COALESCE(NULLIF(albumartist,''), artist, '')) FROM media_items WHERE deleted_at IS NULL {where}"
            row = self._db.conn.execute(sql, params).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def fetch_artists(self, offset: int = 0, limit: int = 100, search: str = "",
                      sort: str = "name", ascending: bool = True) -> list[dict[str, Any]]:
        if not self._db:
            return []
        try:
            where, params = self._build_where(search)
            order = "ASC" if ascending else "DESC"
            sql = (
                f"SELECT COALESCE(NULLIF(albumartist,''), artist, '') as artist_name, "
                f"COUNT(*) as track_count, COUNT(DISTINCT COALESCE(album, '')) as album_count, "
                f"SUM(duration) as duration "
                f"FROM media_items WHERE deleted_at IS NULL AND COALESCE(artist, '') != '' {where} "
                f"GROUP BY artist_name ORDER BY artist_name {order} LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._db.conn.execute(sql, params).fetchall()
            return [self._artist_row_to_dict(r) for r in rows]
        except Exception as e:
            logger.debug("fetch_artists failed: %s", e)
            return []

    def _build_where(self, search: str = "", artist: str = "", album: str = "",
                     genre: str = "", fmt: str = "") -> tuple[str, list]:
        clauses = []
        params: list = []
        if search:
            # Try FTS5 first
            if hasattr(self._db, 'conn'):
                try:
                    fts_test = self._db.conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='virtual_table' AND name='media_fts'"
                    ).fetchone()
                    if fts_test:
                        clauses.append("(rowid IN (SELECT rowid FROM media_fts WHERE media_fts MATCH ?))")
                        params.append(f"*{search}*")
                    else:
                        clauses.append("(title LIKE ? OR artist LIKE ? OR album LIKE ? COLLATE NOCASE)")
                        p = f"%{search}%"
                        params.extend([p, p, p])
                except Exception:
                    clauses.append("(title LIKE ? OR artist LIKE ? OR album LIKE ? COLLATE NOCASE)")
                    p = f"%{search}%"
                    params.extend([p, p, p])
            else:
                clauses.append("(title LIKE ? OR artist LIKE ? OR album LIKE ? COLLATE NOCASE)")
                p = f"%{search}%"
                params.extend([p, p, p])
        if artist:
            clauses.append("(COALESCE(NULLIF(albumartist,''), artist, '') = ? OR artist = ?)")
            params.extend([artist, artist])
        if album:
            clauses.append("(COALESCE(album_key, album, '') = ? OR album = ?)")
            params.extend([album, album])
        if genre:
            clauses.append("genre = ?")
            params.append(genre)
        if fmt:
            clauses.append("LOWER(ext) = ?")
            params.append(f".{fmt.lower()}")
        where = "AND " + " AND ".join(clauses) if clauses else ""
        return where, params

    _TRACK_SORT_COLUMNS = {
        "title": "LOWER(COALESCE(title, ''))",
        "artist": "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))",
        "album": "LOWER(COALESCE(album, ''))",
        "year": "COALESCE(year, 0)",
        "duration": "COALESCE(duration, 0)",
        "format": "LOWER(COALESCE(ext, ''))",
        "name": "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))",
        "added": "COALESCE(created_at, 0)",
        "play_count": "COALESCE(play_count, 0)",
    }

    _ALBUM_SORT_COLUMNS = {
        "year": "MIN(year)",
        "title": "LOWER(COALESCE(MIN(album), ''))",
        "artist": "LOWER(COALESCE(MIN(NULLIF(albumartist,'')), MIN(artist), ''))",
        "duration": "SUM(COALESCE(duration, 0))",
        "track_count": "COUNT(*)",
    }

    _ARTIST_SORT_COLUMNS = {
        "name": "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))",
        "track_count": "COUNT(*)",
        "album_count": "COUNT(DISTINCT COALESCE(album, ''))",
    }

    def _sort_column(self, sort: str, table: str = "tracks") -> str:
        if table == "albums":
            return self._ALBUM_SORT_COLUMNS.get(sort, "MIN(year)")
        if table == "artists":
            return self._ARTIST_SORT_COLUMNS.get(sort, "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))")
        return self._TRACK_SORT_COLUMNS.get(sort, "LOWER(COALESCE(title, ''))")

    @property
    def search_backend(self) -> str:
        if not self._db:
            return "none"
        try:
            if hasattr(self._db, 'conn'):
                row = self._db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='virtual_table' AND name='media_fts'"
                ).fetchone()
                return "fts5" if row else "like"
        except Exception:
            pass
        return "none"

    def _row_to_dict(self, r) -> dict:
        return {
            "track_id": r[0], "filepath": r[1], "filename": r[2], "ext": r[3],
            "duration": r[4] or 0, "title": r[5] or "", "artist": r[6] or "",
            "album": r[7] or "", "album_key": r[19] or r[7] or "",
            "track_uid": r[18] or "",
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
