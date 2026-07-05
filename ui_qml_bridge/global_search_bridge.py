"""GlobalSearchBridge — cross-domain search for QML using FTS5 search engine."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class GlobalSearchBridge(QObject):
    resultsChanged = Signal()

    def __init__(self, db=None, search_engine=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._search_engine = search_engine
        self._query = ""
        self._results = []
        self._is_searching = False

    @Property(str, notify=resultsChanged)
    def query(self):
        return self._query

    @Property("QVariantList", notify=resultsChanged)
    def results(self):
        return self._results

    @Property(bool, notify=resultsChanged)
    def isSearching(self):
        return self._is_searching

    @Slot(str, result=dict)
    def search(self, query: str):
        self._query = query
        self._is_searching = True
        self.resultsChanged.emit()
        query = query.strip().lower()
        if not query:
            self._results = []
            self._is_searching = False
            self.resultsChanged.emit()
            return {"ok": True, "count": 0}
        results = []
        try:
            if self._search_engine and hasattr(self._search_engine, 'search'):
                items = self._search_engine.search(query) or []
                for item in items[:30]:
                    results.append({
                        "type": "track",
                        "id": getattr(item, 'id', 0),
                        "title": getattr(item, 'title', '') or '',
                        "subtitle": f"{getattr(item, 'artist', '') or ''} · {getattr(item, 'album', '') or ''}",
                        "album_key": getattr(item, 'album_key', '') or getattr(item, 'album', '') or '',
                    })
            elif self._db and hasattr(self._db, 'conn'):
                sql = "SELECT id, title, artist, album, album_key FROM media_items WHERE deleted_at IS NULL AND (title LIKE ? OR artist LIKE ? OR album LIKE ?) LIMIT 30"
                p = f"%{query}%"
                rows = self._db.conn.execute(sql, (p, p, p)).fetchall()
                for r in rows:
                    results.append({
                        "type": "track",
                        "id": r[0],
                        "title": r[1] or "",
                        "subtitle": f"{r[2] or ''} · {r[3] or ''}",
                        "album_key": r[4] or r[3] or "",
                    })
        except Exception:
            pass
        self._results = results
        self._is_searching = False
        self.resultsChanged.emit()
        return {"ok": True, "count": len(results)}
