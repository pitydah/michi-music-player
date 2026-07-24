from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

from core.connection_factory import LibraryConnectionFactory
from core.library_sources_service import LibrarySourcesService
from core.settings_manager import get as get_setting

logger = logging.getLogger("michi.library_query")

_local_conn = threading.local()


class LibraryQueryError(Exception):
    """Error raised when a library query cannot be completed safely."""

    def __init__(self, code: str, operation: str, safe_message: str = "") -> None:
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
    """Return the allowlisted SQL expression for a sort key."""
    if table == "albums":
        return _ALBUM_SORT.get(sort, "MIN(year)")
    if table == "artists":
        return _ARTIST_SORT.get(sort, "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))")
    return _TRACK_SORT.get(sort, "LOWER(COALESCE(title, ''))")


def _album_key_sql() -> str:
    """Return the canonical album identity SQL expression."""
    return "COALESCE(NULLIF(album_key, ''), album, '')"


def _artist_key_sql() -> str:
    """Return the canonical artist identity SQL expression."""
    return "COALESCE(NULLIF(albumartist, ''), artist, '')"


def _lib_sources() -> list[str]:
    """Return configured library roots, falling back to the legacy setting."""
    try:
        svc = LibrarySourcesService()
        return svc.root_paths()
    except Exception:
        pass
    try:
        folder = get_setting("general/music_folder")
        if folder and Path(folder).is_dir():
            return [folder]
    except Exception:
        pass
    return []


class LibraryQueryService:
    """Provide read-only, parameterized access to the canonical music library."""

    def __init__(self, db: Any | None = None, db_path: str = "") -> None:
        self._db = db
        self._db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Return the current thread's library connection."""
        if self._db_path:
            if not hasattr(_local_conn, "conn") or _local_conn.conn is None:
                factory = LibraryConnectionFactory(self._db_path)
                _local_conn.conn = factory.get_connection()
            return _local_conn.conn
        if self._db and hasattr(self._db, 'conn'):
            return self._db.conn
        raise LibraryQueryError("NO_DB", "query", "Base de datos no disponible")

    def _check_db(self) -> None:
        """Fail fast when no database source was configured."""
        if not self._db and not self._db_path:
            raise LibraryQueryError("NO_DB", "query", "Base de datos no disponible")

    def _build_where(self, search: str = "", artist: str = "", album: str = "",
                     genre: str = "", fmt: str = "", folder: str = "",
                     year: str = "", quality: str = "",
                      missing_artist: bool = False, missing_album: bool = False,
                      missing_file: bool = False,
                      _use_fts: bool = False) -> tuple[str, list[Any]]:
        """Build parameterized predicates shared by library aggregate queries."""
        clauses: list[str] = []
        params: list[Any] = []
        if search and _use_fts and self.search_backend == "fts5":
            fts_query = " OR ".join(f"{w}*" for w in search.split() if w)
            clauses.append("id IN (SELECT rowid FROM media_fts WHERE media_fts MATCH ?)")
            params.append(fts_query)
        elif search:
            clauses.append(
                "(title LIKE ? COLLATE NOCASE OR artist LIKE ? COLLATE NOCASE "
                "OR album LIKE ? COLLATE NOCASE)"
            )
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
        if missing_file:
            clauses.append(
                "LOWER(COALESCE(scan_status, '')) IN "
                "('missing', 'not_found', 'offline', 'unavailable')"
            )
        where = "AND " + " AND ".join(clauses) if clauses else ""
        return where, params

    def _exec(
        self, sql: str, params: list[Any] | tuple[Any, ...] | None = None
    ) -> sqlite3.Cursor:
        """Execute a parameterized query on the service connection."""
        conn = self._get_conn()
        return conn.execute(sql, params or [])

    def count_tracks(self, **kwargs) -> int:
        self._check_db()
        try:
            use_fts = bool(kwargs.get("search")) and self.search_backend == "fts5"
            kwargs["_use_fts"] = use_fts
            where, params = self._build_where(**kwargs)
            row = self._exec(
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
            sort = _sort_col(kwargs.pop("sort", "title"), "tracks")
            order = "ASC" if kwargs.pop("asc", True) else "DESC"
            use_fts = bool(kwargs.get("search")) and self.search_backend == "fts5"
            kwargs["_use_fts"] = use_fts
            where, params = self._build_where(**kwargs)
            sql = (
                f"SELECT id, filepath, filename, ext, duration, title, artist, album, "
                f"albumartist, year, genre, track_number, track_total, disc_number, disc_total, "
                f"bitrate, sample_rate, bit_depth, channels, play_count, last_played, "
                f"album_key, track_uid, created_at "
                f"FROM media_items WHERE deleted_at IS NULL {where} "
                f"ORDER BY {sort} {order} LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._exec(sql, params).fetchall()
            return [self._row_to_public(r) for r in rows]
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_tracks", str(e)) from e

    def count_albums(self, **kwargs) -> int:
        self._check_db()
        try:
            where, params = self._build_where(**kwargs)
            row = self._exec(
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
            sort = _sort_col(kwargs.pop("sort", "year"), "albums")
            order = "ASC" if kwargs.pop("asc", False) else "DESC"
            where, params = self._build_where(**kwargs)
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
            rows = self._exec(sql, params).fetchall()
            return [self._album_row_to_dict(r) for r in rows]
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_albums", str(e)) from e

    def count_artists(self, **kwargs) -> int:
        self._check_db()
        try:
            where, params = self._build_where(**kwargs)
            row = self._exec(
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
            sort = _sort_col(kwargs.pop("sort", "name"), "artists")
            order = "ASC" if kwargs.pop("asc", True) else "DESC"
            where, params = self._build_where(**kwargs)
            sql = (
                f"SELECT {_artist_key_sql()} as artist_name, "
                f"COUNT(*) as track_count, COUNT(DISTINCT COALESCE(album, '')) as album_count, "
                f"SUM(duration) as duration "
                f"FROM media_items WHERE deleted_at IS NULL AND COALESCE(artist, '') != '' {where} "
                f"GROUP BY artist_name ORDER BY {sort} {order} LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._exec(sql, params).fetchall()
            return [self._artist_row_to_dict(r) for r in rows]
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_artists", str(e)) from e

    def count_folders(self, parent_path: str = "") -> int:
        self._check_db()
        roots = _lib_sources()
        try:
            if parent_path:
                like = f"{parent_path}/%"
                where = "directory LIKE ? AND directory NOT LIKE ?"
                params = [like, f"{parent_path}/%/%"]
            elif roots:
                clauses = " OR ".join(["directory LIKE ?" for _ in roots])
                wheres = [f"({clauses})"]
                params = [f"{r}/%" for r in roots]
                where = " AND ".join(wheres) if wheres else ""
            else:
                where = "directory IS NOT NULL AND directory != ''"
                params = []
            row = self._exec(
                f"SELECT COUNT(DISTINCT directory) FROM media_items "
                f"WHERE deleted_at IS NULL AND {where}", params
            ).fetchone()
            return row[0] if row else 0
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "count_folders", str(e)) from e

    def fetch_folders(self, parent_path: str = "", offset: int = 0,
                      limit: int = 100) -> list[dict[str, Any]]:
        self._check_db()
        roots = _lib_sources()
        try:
            if parent_path:
                like = f"{parent_path}/%"
                where = "directory LIKE ? AND directory NOT LIKE ?"
                params = [like, f"{parent_path}/%/%"]
            elif roots:
                clauses = " OR ".join(["directory LIKE ?" for _ in roots])
                wheres = [f"({clauses})"]
                params = [f"{r}/%" for r in roots]
                where = " AND ".join(wheres) if wheres else ""
            else:
                where = "directory IS NOT NULL AND directory != ''"
                params = []
            sql = (
                f"SELECT directory, COUNT(*) as cnt FROM media_items "
                f"WHERE deleted_at IS NULL AND {where} "
                f"GROUP BY directory ORDER BY directory LIMIT ? OFFSET ?"
            )
            params.extend([limit, offset])
            rows = self._exec(sql, params).fetchall()
            return [{"path": r[0] or "", "name": (r[0] or "").rsplit("/", 1)[-1] if "/" in (r[0] or "") else r[0] or "",
                     "track_count": r[1], "is_expandable": True, "expanded": False}
                    for r in rows]
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_folders", str(e)) from e

    def fetch_track_internal(self, track_id: int) -> dict | None:
        self._check_db()
        try:
            row = self._exec(
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

    def fetch_track_by_filepath(self, filepath: str) -> dict[str, Any] | None:
        """Return queue-safe metadata for an indexed filepath."""
        self._check_db()
        try:
            row = self._exec(
                "SELECT id, filepath, title, artist, album, duration, track_uid, album_key "
                "FROM media_items WHERE filepath=? AND deleted_at IS NULL",
                (filepath,),
            ).fetchone()
            if not row:
                return None
            return {
                "track_id": row[0], "filepath": row[1], "title": row[2] or "",
                "artist": row[3] or "", "album": row[4] or "",
                "duration": row[5] or 0, "track_uid": row[6] or "",
                "album_key": row[7] or "",
            }
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_track_by_filepath", str(e)) from e

    def list_composers(self) -> list[str]:
        """Return non-empty composers in display order."""
        self._check_db()
        try:
            rows = self._exec(
                "SELECT DISTINCT composer FROM media_items "
                "WHERE deleted_at IS NULL AND COALESCE(composer, '') != '' "
                "ORDER BY composer COLLATE NOCASE"
            ).fetchall()
            return [str(row[0]) for row in rows]
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "list_composers", str(e)) from e

    def list_years(self) -> list[int]:
        """Return positive release years in ascending order."""
        self._check_db()
        try:
            rows = self._exec(
                "SELECT DISTINCT year FROM media_items "
                "WHERE deleted_at IS NULL AND year IS NOT NULL AND year > 0 ORDER BY year"
            ).fetchall()
            return [int(row[0]) for row in rows]
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "list_years", str(e)) from e

    def fetch_album_tracks_internal(self, album_key: str) -> list[dict]:
        self._check_db()
        try:
            rows = self._exec(
                "SELECT id, filepath, title, artist, album, albumartist, duration, "
                "track_number, track_uid, year, genre, ext, sample_rate, bit_depth, album_key "
                f"FROM media_items WHERE deleted_at IS NULL AND {_album_key_sql()}=? "
                "ORDER BY COALESCE(track_number, 999), title", (album_key,)
            ).fetchall()
            return [{"track_id": r[0], "filepath": r[1], "title": r[2] or "",
                     "artist": r[3] or "", "album": r[4] or "",
                     "album_artist": r[5] or "", "duration": r[6] or 0,
                     "track_number": r[7] or 0, "track_uid": r[8] or "",
                     "year": r[9] or 0, "genre": r[10] or "", "format": r[11] or "",
                     "sample_rate": r[12] or 0, "bit_depth": r[13] or 0,
                     "album_key": r[14] or album_key, "cover_key": r[14] or album_key}
                    for r in rows]
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_album_tracks_internal", str(e)) from e

    def fetch_artist_tracks_internal(self, artist_name: str) -> list[dict]:
        self._check_db()
        try:
            rows = self._exec(
                "SELECT id, filepath, title, artist, album, albumartist, duration, "
                "track_number, track_uid, album_key, year, genre, ext, sample_rate, bit_depth "
                f"FROM media_items WHERE deleted_at IS NULL AND "
                f"({_artist_key_sql()}=? OR artist=?) "
                "ORDER BY COALESCE(album, ''), COALESCE(track_number, 999), title",
                (artist_name, artist_name)
            ).fetchall()
            return [{"track_id": r[0], "filepath": r[1], "title": r[2] or "",
                     "artist": r[3] or "", "album": r[4] or "", "album_artist": r[5] or "",
                     "duration": r[6] or 0, "track_number": r[7] or 0, "track_uid": r[8] or "",
                     "album_key": r[9] or "", "year": r[10] or 0, "genre": r[11] or "",
                     "format": r[12] or "", "sample_rate": r[13] or 0,
                     "bit_depth": r[14] or 0, "cover_key": r[9] or ""} for r in rows]
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_artist_tracks_internal", str(e)) from e

    def fetch_folder_tracks_internal(self, folder_path: str) -> list[dict]:
        self._check_db()
        try:
            rows = self._exec(
                "SELECT id, filepath, title, artist, album, duration, track_uid "
                "FROM media_items WHERE deleted_at IS NULL AND directory LIKE ? "
                "ORDER BY title", (f"{folder_path}%",)
            ).fetchall()
            return [{"track_id": r[0], "filepath": r[1], "title": r[2] or "",
                     "artist": r[3] or "", "album": r[4] or "", "duration": r[5] or 0,
                     "track_uid": r[6] or ""} for r in rows]
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_folder_tracks_internal", str(e)) from e

    def fetch_filtered_tracks_internal(self, filters: dict,
                                       limit: int = 500) -> list[dict]:
        """Return metadata-rich tracks matching exact library filters."""
        self._check_db()
        clauses = ["deleted_at IS NULL"]
        params = []
        for field in ("artist", "album", "genre", "composer", "format", "year"):
            value = filters.get(field)
            if value:
                clauses.append(f"{field}=?")
                params.append(value)
        if filters.get("folder"):
            clauses.append("(directory=? OR instr(directory, ? || '/')=1)")
            params.extend([filters["folder"], filters["folder"]])
        if filters.get("favorites"):
            clauses.append("filepath IN (SELECT track_id FROM favorites)")
        if filters.get("unplayed"):
            clauses.append(
                "(filepath NOT IN (SELECT track_id FROM play_history "
                "WHERE played_at IS NOT NULL) OR last_played IS NULL)"
            )
        params.append(limit)
        rows = self._exec(
            "SELECT id, track_uid, filepath, title, artist, album, duration "
            f"FROM media_items WHERE {' AND '.join(clauses)} "
            "ORDER BY title LIMIT ?",
            params,
        ).fetchall()
        return [{
            "track_id": row[0], "track_uid": row[1] or "",
            "filepath": row[2], "title": row[3] or "",
            "artist": row[4] or "", "album": row[5] or "",
            "duration": row[6] or 0,
        } for row in rows if row[2]]

    def fetch_album_detail(self, album_key: str) -> dict | None:
        try:
            internal = self.fetch_album_tracks_internal(album_key)
            if not internal:
                return None
            first = internal[0]
            return {"album_key": album_key, "title": first.get("album", ""),
                    "artist": first.get("album_artist") or first.get("artist", ""),
                    "year": first.get("year", 0), "genre": first.get("genre", ""),
                    "cover_key": first.get("cover_key", album_key), "track_count": len(internal),
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
            genres = next((t.get("genre", "") for t in internal if t.get("genre")), "")
            return {"artist": artist_name, "track_count": len(internal),
                    "album_count": len(albums),
                    "genre": genres,
                    "tracks": [{k: v for k, v in t.items() if k != "filepath"} for t in internal]}
        except LibraryQueryError:
            raise
        except Exception as e:
            raise LibraryQueryError("QUERY_FAILED", "fetch_artist_detail", str(e)) from e

    def _row_to_public(self, r: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
        """Convert a canonical track row to the public QML representation."""
        album_key = r[21] or r[7] or ""
        composer = (r[24] or "") if len(r) > 24 else ""
        favorite = bool(r[25]) if len(r) > 25 else False
        missing = bool(r[26]) if len(r) > 26 else False
        return {
            "track_id": r[0], "track_uid": r[22] or "", "public_ref": f"track_{r[0]}",
            "filename": r[2] or "", "format": (r[3] or "").lstrip(".").upper(),
            "duration": r[4] or 0, "title": r[5] or "", "artist": r[6] or "",
            "album": r[7] or "", "albumartist": r[8] or "", "album_key": album_key,
            "year": r[9] or 0, "genre": r[10] or "", "track_number": r[11] or 0,
            "track_total": r[12] or 0, "disc_number": r[13] or 0, "disc_total": r[14] or 0,
            "bitrate": r[15] or 0, "sample_rate": r[16] or 0, "bit_depth": r[17] or 0,
            "channels": r[18] or 0, "play_count": r[19] or 0, "last_played": r[20] or 0,
            "cover_key": album_key, "composer": composer, "favorite": favorite,
            "missing": missing, "date_added": r[23] or 0, "source_type": "local_file",
        }

    def _album_row_to_dict(self, r: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
        """Convert an aggregate album row to a dictionary."""
        year = r[3] or 0
        decade = (year // 10 * 10) if year else 0
        return {
            "album_key": r[0] or "", "title": r[1] or "", "artist": r[2] or "",
            "year": year, "track_count": r[4] or 0, "duration": r[5] or 0,
            "genre": r[6] or "", "cover_key": r[0] or "", "decade": decade,
        }

    def _artist_row_to_dict(self, r: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
        """Convert an aggregate artist row to a dictionary."""
        return {
            "name": r[0] or "", "track_count": r[1] or 0,
            "album_count": r[2] or 0, "duration": r[3] or 0,
        }

    @property
    def search_backend(self) -> str:
        if not self._db and not self._db_path:
            return "none"
        try:
            row = self._exec(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='media_fts'"
            ).fetchone()
            return "fts5" if row else "like"
        except Exception:
            return "none"

    def search_fts(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        if self.search_backend != "fts5":
            raise LibraryQueryError("NO_FTS5", "search_fts", "FTS5 no disponible")
        try:
            fts_query = " OR ".join(f"{w}*" for w in query.split() if w)
            sql = (
                "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.duration, m.album_key, m.track_uid "
                "FROM media_items m JOIN media_fts fts ON m.id = fts.rowid "
                "WHERE media_fts MATCH ? AND m.deleted_at IS NULL "
                "ORDER BY rank LIMIT ?"
            )
            rows = self._exec(sql, (fts_query, limit)).fetchall()
            return [{"track_id": r[0], "filepath": r[1], "title": r[2] or "",
                     "artist": r[3] or "", "album": r[4] or "", "duration": r[5] or 0,
                     "album_key": r[6] or "", "track_uid": r[7] or ""} for r in rows]
        except Exception as e:
            raise LibraryQueryError("FTS5_FAILED", "search_fts", str(e)) from e

    # ==================== Métodos para MixService ====================

    def recently_played(self, limit: int = 30) -> list[dict]:
        """Obtiene canciones reproducidas recientemente."""
        try:
            rows = self._exec(
                "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.duration, "
                "m.track_uid, m.album_key, h.played_at "
                "FROM media_items m JOIN play_history h "
                "ON h.track_id = m.filepath OR h.track_id = CAST(m.id AS TEXT) "
                "WHERE m.deleted_at IS NULL ORDER BY h.played_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [{
                "track_id": row[0], "filepath": row[1], "title": row[2] or "",
                "artist": row[3] or "", "album": row[4] or "",
                "duration": row[5] or 0, "track_uid": row[6] or "",
                "album_key": row[7] or "", "played_at": row[8] or 0,
            } for row in rows]
        except Exception as e:
            logger.debug("recently_played failed: %s", e)
            return []
