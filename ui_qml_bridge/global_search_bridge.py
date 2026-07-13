"""GlobalSearchBridge — multidomain async search via QueryExecutor."""
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
        self._error_code = ""
        self._error_message = ""

    @Property(str, notify=resultsChanged)
    def query(self):
        return self._query

    @Property("QVariantList", notify=resultsChanged)
    def results(self):
        return self._results

    @Property(bool, notify=searchingChanged)
    def isSearching(self):
        return self._is_searching

    @Property(str, notify=resultsChanged)
    def errorCode(self):
        return self._error_code

    @Property(str, notify=resultsChanged)
    def errorMessage(self):
        return self._error_message

    @property
    def query_executor(self):
        return self._qe

    def _do_search(self, query: str, gen: int) -> list[dict]:
        results = []
        if not self._db:
            return results
        try:
            sql = "SELECT id, title, artist, album, album_key FROM media_items WHERE deleted_at IS NULL AND (title LIKE ? OR artist LIKE ? OR album LIKE ?) LIMIT ?"
            p = f"%{query}%"
            for r in self._db.conn.execute(sql, (p, p, p, _MAX_PER_DOMAIN)).fetchall():
                results.append({"type": "track", "id": r[0], "title": r[1] or "",
                                "subtitle": f"{r[2] or ''} · {r[3] or ''}",
                                "section": "Canciones", "score": 1.0})
            sql = "SELECT DISTINCT album_key, album, COALESCE(NULLIF(albumartist,''), artist, ''), year FROM media_items WHERE deleted_at IS NULL AND album LIKE ? AND COALESCE(album, '') != '' LIMIT ?"
            for r in self._db.conn.execute(sql, (f"%{query}%", _MAX_PER_DOMAIN)).fetchall():
                results.append({"type": "album", "id": r[0] or "", "title": r[1] or "",
                                "subtitle": r[2] or "", "section": "Álbumes", "score": 0.9})
            sql = "SELECT DISTINCT COALESCE(NULLIF(albumartist,''), artist, '') FROM media_items WHERE deleted_at IS NULL AND COALESCE(NULLIF(albumartist,''), artist, '') LIKE ? AND COALESCE(artist, '') != '' LIMIT ?"
            for r in self._db.conn.execute(sql, (f"%{query}%", _MAX_PER_DOMAIN)).fetchall():
                results.append({"type": "artist", "id": r[0] or "", "title": r[0] or "",
                                "subtitle": "Artista", "section": "Artistas", "score": 0.8})
        except Exception as e:
            logger.debug("Search failed: %s", e)
        return results

    @Slot(str, result=dict)
    def search(self, query: str):
        self._query = query
        self._search_gen += 1
        gen = self._search_gen
        q = query.strip().lower()
        if not q:
            self._results = []
            self._is_searching = False
            self._error_code = ""
            self._error_message = ""
            self.resultsChanged.emit()
            self.searchingChanged.emit()
            return {"ok": True, "count": 0}

        self._is_searching = True
        self._error_code = ""
        self._error_message = ""
        self.searchingChanged.emit()

        def _task():
            return self._do_search(q, gen)

        def _on_done(results):
            if gen != self._search_gen:
                return
            self._results = results[:_MAX_TOTAL]
            self._is_searching = False
            self.searchingChanged.emit()
            self.resultsChanged.emit()

        if self._qe and hasattr(self._qe, 'submit'):
            self._qe.submit("global_search", _task, on_success=_on_done,
                            on_error=lambda c, m: (_on_done([]),
                                                    setattr(self, '_error_code', c) or
                                                    setattr(self, '_error_message', m)),
                            supersede=True, cancellable=True)
            return {"ok": True, "queued": True}
        else:
            results = _task()
            _on_done(results)
            return {"ok": True, "count": len(results)}
