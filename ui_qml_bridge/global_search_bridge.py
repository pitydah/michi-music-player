"""GlobalSearchBridge — multidomain async search using FTS5 + LIKE fallback."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.global_search")

_MAX_PER_DOMAIN = 10
_MAX_TOTAL = 50


class GlobalSearchBridge(QObject):
    resultsChanged = Signal()
    searchingChanged = Signal()

    def __init__(self, db=None, search_engine=None, query_executor=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._search_engine = search_engine
        self._qe = query_executor
        self._query = ""
        self._results = []
        self._is_searching = False
        self._search_gen = 0

    @Property(str, notify=resultsChanged)
    def query(self):
        return self._query

    @Property("QVariantList", notify=resultsChanged)
    def results(self):
        return self._results

    @Property(bool, notify=searchingChanged)
    def isSearching(self):
        return self._is_searching

    def _search_tracks(self, query: str, gen: int) -> list[dict]:
        if gen != self._search_gen or not self._db:
            return []
        results = []
        try:
            sql = "SELECT id, title, artist, album, album_key FROM media_items WHERE deleted_at IS NULL AND (title LIKE ? OR artist LIKE ? OR album LIKE ?) LIMIT ?"
            p = f"%{query}%"
            rows = self._db.conn.execute(sql, (p, p, p, _MAX_PER_DOMAIN)).fetchall()
            for r in rows:
                results.append({
                    "type": "track", "id": r[0], "title": r[1] or "",
                    "subtitle": f"{r[2] or ''} · {r[3] or ''}",
                    "section": "Canciones", "score": 1.0,
                })
        except Exception as e:
            logger.debug("Search tracks failed: %s", e)
        return results

    def _search_albums(self, query: str, gen: int) -> list[dict]:
        if gen != self._search_gen or not self._db:
            return []
        results = []
        try:
            sql = "SELECT DISTINCT album_key, album, COALESCE(NULLIF(albumartist,''), artist, ''), year FROM media_items WHERE deleted_at IS NULL AND album LIKE ? AND COALESCE(album, '') != '' LIMIT ?"
            rows = self._db.conn.execute(sql, (f"%{query}%", _MAX_PER_DOMAIN)).fetchall()
            for r in rows:
                results.append({
                    "type": "album", "id": r[0] or "", "title": r[1] or "",
                    "subtitle": r[2] or "", "section": "Álbumes", "score": 0.9,
                })
        except Exception as e:
            logger.debug("Search albums failed: %s", e)
        return results

    def _search_artists(self, query: str, gen: int) -> list[dict]:
        if gen != self._search_gen or not self._db:
            return []
        results = []
        try:
            sql = "SELECT DISTINCT COALESCE(NULLIF(albumartist,''), artist, '') FROM media_items WHERE deleted_at IS NULL AND COALESCE(NULLIF(albumartist,''), artist, '') LIKE ? AND COALESCE(artist, '') != '' LIMIT ?"
            rows = self._db.conn.execute(sql, (f"%{query}%", _MAX_PER_DOMAIN)).fetchall()
            for r in rows:
                results.append({
                    "type": "artist", "id": r[0] or "", "title": r[0] or "",
                    "subtitle": "Artista", "section": "Artistas", "score": 0.8,
                })
        except Exception as e:
            logger.debug("Search artists failed: %s", e)
        return results

    @Slot(str, result=dict)
    def search(self, query: str):
        self._query = query
        self._search_gen += 1
        gen = self._search_gen
        query = query.strip().lower()
        if not query:
            self._results = []
            self._is_searching = False
            self.resultsChanged.emit()
            return {"ok": True, "count": 0}
        self._is_searching = True
        self.searchingChanged.emit()
        results = []
        try:
            results.extend(self._search_tracks(query, gen))
            results.extend(self._search_albums(query, gen))
            results.extend(self._search_artists(query, gen))
        except Exception as e:
            logger.debug("Global search failed: %s", e)
            self._results = []
            self._is_searching = False
            self.searchingChanged.emit()
            self.resultsChanged.emit()
            return {"ok": False, "error_code": "SEARCH_FAILED", "message": "Error al buscar"}
        if gen != self._search_gen:
            return {"ok": True, "count": 0, "stale": True}
        self._results = results[:_MAX_TOTAL]
        self._is_searching = False
        self.searchingChanged.emit()
        self.resultsChanged.emit()
        return {"ok": True, "count": len(results)}
