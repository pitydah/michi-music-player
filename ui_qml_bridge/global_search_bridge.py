"""GlobalSearchBridge — cross-domain search for QML."""
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
            if self._db and hasattr(self._db, 'get_all'):
                items = self._db.get_all() or []
                for item in items:
                    title = (getattr(item, 'title', '') or '').lower()
                    artist = (getattr(item, 'artist', '') or '').lower()
                    album = (getattr(item, 'album', '') or '').lower()
                    if query in title or query in artist or query in album:
                        results.append({
                            "type": "track",
                            "id": getattr(item, 'id', 0),
                            "title": getattr(item, 'title', '') or '',
                            "subtitle": f"{getattr(item, 'artist', '') or ''} · {getattr(item, 'album', '') or ''}",
                            "album_key": getattr(item, 'album_key', '') or getattr(item, 'album', '') or '',
                        })
                        if len(results) >= 30:
                            break
        except Exception:
            pass
        self._results = results
        self._is_searching = False
        self.resultsChanged.emit()
        return {"ok": True, "count": len(results)}
