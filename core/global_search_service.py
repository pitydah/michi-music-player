"""GlobalSearchService — thread-safe search across all domains using FTS5 + LIKE fallback.
Each task opens its own read-only SQLite connection."""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import Any

logger = logging.getLogger("michi.global_search")

_MAX_PER_DOMAIN = 10
_MAX_TOTAL = 50
_DEFAULT_TIMEOUT_MS = 5000


class SearchError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class SearchCancelledError(SearchError):
    def __init__(self):
        super().__init__("CANCELLED", "Search cancelled")


class SearchStaleError(SearchError):
    def __init__(self):
        super().__init__("STALE", "Search result superseded by newer request")


class SearchRequest:
    __slots__ = ("request_id", "query", "generation", "cancelled", "finished")

    def __init__(self, request_id: int, query: str, generation: int):
        self.request_id = request_id
        self.query = query
        self.generation = generation
        self.cancelled = False
        self.finished = False


class GlobalSearchService:
    def __init__(self, db_path: str = ""):
        self._db_path = db_path
        self._counter = 0
        self._counter_lock = threading.Lock()
        self._generation: dict[str, int] = {}
        self._gen_lock = threading.Lock()
        self._active: dict[str, SearchRequest] = {}
        self._active_lock = threading.Lock()

    def _next_id(self) -> int:
        with self._counter_lock:
            self._counter += 1
            return self._counter

    def _next_gen(self, owner: str) -> int:
        with self._gen_lock:
            self._generation[owner] = self._generation.get(owner, 0) + 1
            return self._generation[owner]

    def _is_stale(self, owner: str, generation: int) -> bool:
        with self._gen_lock:
            return generation != self._generation.get(owner, 0)

    def search(self, query: str, owner: str = "global_search",
               timeout_ms: int = _DEFAULT_TIMEOUT_MS) -> dict[str, Any]:
        request_id = self._next_id()
        gen = self._next_gen(owner)
        q = query.strip()
        if not q:
            return {"ok": True, "request_id": request_id, "results": [], "count": 0}

        req = SearchRequest(request_id, q, gen)
        with self._active_lock:
            prev = self._active.get(owner)
            if prev and not prev.cancelled:
                prev.cancelled = True
            self._active[owner] = req

        try:
            results = self._execute_search(q, owner, gen, timeout_ms)
            if self._is_stale(owner, gen):
                raise SearchStaleError()
            with self._active_lock:
                if self._active.get(owner) is req:
                    req.finished = True
            return {"ok": True, "request_id": request_id, "results": results, "count": len(results)}
        except SearchError:
            raise
        except Exception as e:
            raise SearchError("SEARCH_FAILED", str(e)) from e

    def search_async(self, query: str, owner: str = "global_search",
                     timeout_ms: int = _DEFAULT_TIMEOUT_MS,
                     on_result=None, on_error=None):
        from PySide6.QtCore import QTimer
        def _run():
            try:
                result = self.search(query, owner=owner, timeout_ms=timeout_ms)
                if on_result:
                    on_result(result)
            except SearchCancelledError:
                pass
            except SearchStaleError:
                pass
            except Exception as e:
                if on_error:
                    on_error(str(e))
        QTimer.singleShot(0, _run)

    def cancel(self, owner: str = "global_search"):
        with self._active_lock:
            req = self._active.get(owner)
            if req and not req.cancelled:
                req.cancelled = True

    def cancel_request(self, request_id: int):
        with self._active_lock:
            for req in self._active.values():
                if req.request_id == request_id and not req.cancelled:
                    req.cancelled = True
                    return True
        return False

    def _execute_search(self, query: str, owner: str, gen: int,
                        timeout_ms: int) -> list[dict[str, Any]]:
        deadline = time.time() + timeout_ms / 1000.0

        def _check():
            if time.time() > deadline:
                raise SearchCancelledError()
            with self._active_lock:
                req = self._active.get(owner)
                if req and req.cancelled:
                    raise SearchCancelledError()
            if self._is_stale(owner, gen):
                raise SearchStaleError()

        conn = self._open_connection()
        try:
            _check()
            results = []
            results.extend(self._search_tracks(conn, query))
            _check()
            results.extend(self._search_albums(conn, query))
            _check()
            results.extend(self._search_artists(conn, query))
            _check()
            results.extend(self._search_playlists(conn, query))
            _check()
            results.extend(self._search_radio(conn, query))
            _check()
            results.sort(key=lambda r: r.get("score", 0), reverse=True)
            return results[:_MAX_TOTAL]
        finally:
            conn.close()

    def _open_connection(self) -> sqlite3.Connection:
        if not self._db_path:
            raise SearchError("NO_DB_PATH", "Database path not configured")
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.execute("PRAGMA query_only = 1")
        conn.row_factory = sqlite3.Row
        return conn

    def _search_tracks(self, conn: sqlite3.Connection, query: str) -> list[dict]:
        results = []
        try:
            rows = conn.execute(
                "SELECT id, title, artist, album, album_key, duration, track_uid "
                "FROM media_items WHERE media_items MATCH ? "
                "AND deleted_at IS NULL ORDER BY rank LIMIT ?",
                (query, _MAX_PER_DOMAIN)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "track", "id": r["id"], "title": r["title"] or "",
                    "subtitle": f"{r['artist'] or ''} · {r['album'] or ''}",
                    "section": "Canciones", "score": 1.0,
                    "album_key": r["album_key"] or "", "duration": r["duration"] or 0,
                    "track_uid": r["track_uid"] or "",
                })
            if results:
                return results
        except Exception:
            pass
        try:
            p = f"%{query}%"
            rows = conn.execute(
                "SELECT id, title, artist, album, album_key, duration, track_uid "
                "FROM media_items WHERE deleted_at IS NULL AND "
                "(title LIKE ? OR artist LIKE ? OR album LIKE ?) LIMIT ?",
                (p, p, p, _MAX_PER_DOMAIN)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "track", "id": r["id"], "title": r["title"] or "",
                    "subtitle": f"{r['artist'] or ''} · {r['album'] or ''}",
                    "section": "Canciones", "score": 1.0,
                    "album_key": r["album_key"] or "", "duration": r["duration"] or 0,
                    "track_uid": r["track_uid"] or "",
                })
        except Exception:
            pass
        return results

    def _search_albums(self, conn: sqlite3.Connection, query: str) -> list[dict]:
        results = []
        try:
            rows = conn.execute(
                "SELECT DISTINCT album_key, album, COALESCE(NULLIF(albumartist,''), artist, ''), year "
                "FROM media_items WHERE media_items MATCH ? "
                "AND deleted_at IS NULL AND COALESCE(album, '') != '' "
                "AND album_key IS NOT NULL AND album_key != '' "
                "ORDER BY rank LIMIT ?",
                (query, _MAX_PER_DOMAIN)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "album", "id": r["album_key"] or "",
                    "title": r["album"] or "",
                    "subtitle": r[2] or "",
                    "section": "Álbumes", "score": 0.9,
                    "year": r["year"] or 0,
                })
            if results:
                return results
        except Exception:
            pass
        try:
            p = f"%{query}%"
            rows = conn.execute(
                "SELECT DISTINCT album_key, album, COALESCE(NULLIF(albumartist,''), artist, ''), year "
                "FROM media_items WHERE deleted_at IS NULL AND album LIKE ? "
                "AND COALESCE(album, '') != '' AND album_key IS NOT NULL AND album_key != '' LIMIT ?",
                (p, _MAX_PER_DOMAIN)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "album", "id": r["album_key"] or "",
                    "title": r["album"] or "",
                    "subtitle": r[2] or "",
                    "section": "Álbumes", "score": 0.9,
                    "year": r["year"] or 0,
                })
        except Exception:
            pass
        return results

    def _search_artists(self, conn: sqlite3.Connection, query: str) -> list[dict]:
        results = []
        try:
            rows = conn.execute(
                "SELECT DISTINCT COALESCE(NULLIF(albumartist,''), artist, '') as artist_name "
                "FROM media_items WHERE media_items MATCH ? "
                "AND deleted_at IS NULL AND artist_name != '' "
                "ORDER BY rank LIMIT ?",
                (query, _MAX_PER_DOMAIN)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "artist", "id": r["artist_name"] or "",
                    "title": r["artist_name"] or "",
                    "subtitle": "Artista",
                    "section": "Artistas", "score": 0.8,
                })
            if results:
                return results
        except Exception:
            pass
        try:
            p = f"%{query}%"
            rows = conn.execute(
                "SELECT DISTINCT COALESCE(NULLIF(albumartist,''), artist, '') "
                "FROM media_items WHERE deleted_at IS NULL AND "
                "COALESCE(NULLIF(albumartist,''), artist, '') LIKE ? "
                "AND COALESCE(artist, '') != '' LIMIT ?",
                (p, _MAX_PER_DOMAIN)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "artist", "id": r[0] or "",
                    "title": r[0] or "",
                    "subtitle": "Artista",
                    "section": "Artistas", "score": 0.8,
                })
        except Exception:
            pass
        return results

    def _search_playlists(self, conn: sqlite3.Connection, query: str) -> list[dict]:
        results = []
        try:
            p = f"%{query}%"
            rows = conn.execute(
                "SELECT id, name, track_count FROM playlists "
                "WHERE name LIKE ? ORDER BY track_count DESC LIMIT ?",
                (p, _MAX_PER_DOMAIN)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "playlist", "id": r["id"],
                    "title": r["name"] or "",
                    "subtitle": f"{r['track_count'] or 0} canciones",
                    "section": "Playlists", "score": 0.7,
                })
        except Exception:
            pass
        return results

    def _search_radio(self, conn: sqlite3.Connection, query: str) -> list[dict]:
        results = []
        try:
            p = f"%{query}%"
            rows = conn.execute(
                "SELECT id, name, url, codec, country FROM radio_stations "
                "WHERE name LIKE ? OR url LIKE ? OR country LIKE ? LIMIT ?",
                (p, p, p, _MAX_PER_DOMAIN)
            ).fetchall()
            for r in rows:
                results.append({
                    "type": "radio", "id": r["id"],
                    "title": r["name"] or "",
                    "subtitle": f"{r['country'] or ''} · {r['codec'] or ''}",
                    "section": "Radio", "score": 0.6,
                    "url": r["url"] or "",
                })
        except Exception:
            pass
        return results
