"""GlobalSearchBridge — multidomain async search via GlobalSearchService (NO direct db.conn)."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.global_search")

_MAX_TOTAL = 50


class GlobalSearchBridge(QObject):
    resultsChanged = Signal()
    searchingChanged = Signal()

    def __init__(self, search_service=None, parent=None):
        super().__init__(parent)
        self._svc = search_service
        self._query = ""
        self._results: list[dict] = []
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

    @Slot(str, result=dict)
    def search(self, query: str):
        self._query = query
        self._search_gen += 1
        gen = self._search_gen
        q = query.strip()
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

        def _on_done(result: dict):
            if gen != self._search_gen:
                return
            if result.get("ok"):
                self._results = result.get("results", [])[:_MAX_TOTAL]
                self._is_searching = False
                self.searchingChanged.emit()
                self.resultsChanged.emit()
            else:
                self._error_code = result.get("error_code", "SEARCH_FAILED")
                self._error_message = result.get("message", "Search failed")
                self._is_searching = False
                self.searchingChanged.emit()
                self.resultsChanged.emit()

        def _on_error(err: str):
            if gen != self._search_gen:
                return
            self._error_code = "SEARCH_FAILED"
            self._error_message = str(err)
            self._is_searching = False
            self.searchingChanged.emit()
            self.resultsChanged.emit()

        if self._svc and callable(getattr(self._svc, 'search', None)) or self._svc and callable(getattr(self._svc, 'search_async', None)):
            try:
                result = self._svc.search(q, owner="global_search", timeout_ms=5000)
                _on_done(result)
                return result
            except Exception as e:
                _on_error(str(e))
                return {"ok": False, "error": str(e)}
        else:
            self._results = []
            self._is_searching = False
            self.resultsChanged.emit()
            self.searchingChanged.emit()
            return {"ok": True, "count": 0}

    @Slot(result=dict)
    def cancel(self):
        if self._svc and hasattr(self._svc, 'cancel'):
            self._svc.cancel(owner="global_search")
        self._is_searching = False
        self.searchingChanged.emit()
        return {"ok": True}
