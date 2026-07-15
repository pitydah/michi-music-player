"""GlobalSearchBridge — async QML search via QueryExecutor/WorkerManager.

Architecture:
  QML debounce → search(query) → request generation → stale guard →
  QueryExecutor/WorkerManager → service connection → partial results → QML.

No direct DB access. Integrates with JobService, ActionRegistry,
NavigationBridge, PageStateStore, CapabilityBridge, AccessibilityBridge.
"""
from __future__ import annotations



from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.global_search")

_MAX_TOTAL = 50
_STALE_MS = 60000

DOMAIN_MAP = {
    "tracks": "track",
    "albums": "album",
    "artists": "artist",
    "playlists": "playlist",
    "folders": "folder",
    "genres": "genre",
    "radio": "radio",
    "devices": "device",
    "connections": "server",
    "actions": "action",
    "settings": "setting",
}


class GlobalSearchBridge(QObject):
    resultsChanged = Signal()
    searchingChanged = Signal()
    partialResults = Signal(str, "QVariantList")
    staleResultDropped = Signal(str)

    def __init__(self, search_service=None, query_executor=None,
                 action_registry=None, navigation_bridge=None,
                 page_state_store=None, capability_bridge=None,
                 accessibility_bridge=None, notification_bridge=None,
                 parent=None):
        super().__init__(parent)
        self._svc = search_service
        self._qe = query_executor
        self._action_registry = action_registry
        self._navigation = navigation_bridge
        self._page_state = page_state_store
        self._capability = capability_bridge
        self._accessibility = accessibility_bridge
        self._notifications = notification_bridge
        self._query = ""
        self._results: list[dict] = []
        self._is_searching = False
        self._search_gen = 0
        self._error_code = ""
        self._error_message = ""
        self._active_request_id = 0
        self._request_counter = 0
        self._owner = "global_search"

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

    def _is_stale(self, request_id: int) -> bool:
        return request_id != self._active_request_id

    def _notify(self, text: str, kind: str = "info"):
        if self._notifications:
            self._notifications.showMessage(text, kind=kind)

    def _run_search(self, query: str, request_id: int) -> dict:
        if self._is_stale(request_id):
            return {"ok": False, "error": "STALE"}
        if self._svc and callable(getattr(self._svc, 'search', None)):
            try:
                result = self._svc.search(query, owner=self._owner, timeout_ms=5000)
                if self._is_stale(request_id):
                    self.staleResultDropped.emit(query)
                    return {"ok": False, "error": "STALE"}
                return result
            except Exception as e:
                return {"ok": False, "error_code": "SEARCH_FAILED", "message": str(e)}
        return {"ok": False, "error_code": "SERVICE_UNAVAILABLE", "message": "No search service"}

    def _on_search_done(self, result: dict, request_id: int):
        if self._is_stale(request_id):
            self.staleResultDropped.emit(self._query)
            return
        if result.get("ok"):
            raw_results = result.get("results", [])
            grouped: dict[str, list] = {}
            for r in raw_results:
                section = r.get("section", r.get("type", "unknown"))
                grouped.setdefault(section, []).append(r)
            for section, items in grouped.items():
                self.partialResults.emit(section, items[:_MAX_TOTAL])
            self._results = raw_results[:_MAX_TOTAL]
            self._is_searching = False
            self._error_code = ""
            self._error_message = ""
        else:
            self._error_code = result.get("error_code", "SEARCH_FAILED")
            self._error_message = result.get("message", "Search failed")
            self._results = []
            self._is_searching = False
        self.searchingChanged.emit()
        self.resultsChanged.emit()

    @Slot(str, result=dict)
    def search(self, query: str):
        self._request_counter += 1
        request_id = self._request_counter
        self._active_request_id = request_id
        self._query = query
        self._search_gen += 1
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

        if self._qe and hasattr(self._qe, 'submit'):
            self._qe.submit(
                owner=self._owner,
                callable_fn=lambda: self._run_search(q, request_id),
                on_success=lambda res: self._on_search_done(res, request_id),
                on_error=lambda code, msg: self._on_search_done(
                    {"ok": False, "error_code": code, "message": msg}, request_id),
                supersede=True,
                cancellable=True,
            )
            return {"ok": True, "async": True, "request_id": request_id}

        result = self._run_search(q, request_id)
        self._on_search_done(result, request_id)
        return result

    @Slot(result=dict)
    def cancel(self):
        self._active_request_id = 0
        if self._qe and hasattr(self._qe, 'cancel_owner'):
            self._qe.cancel_owner(self._owner)
        if self._svc and hasattr(self._svc, 'cancel'):
            import contextlib
            with contextlib.suppress(Exception):
                self._svc.cancel(owner=self._owner)
        self._is_searching = False
        self._search_gen += 1
        self._results = []
        self.searchingChanged.emit()
        self.resultsChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def searchDomain(self, domain: str, query: str):
        mapped = DOMAIN_MAP.get(domain, domain)
        return self.search(f"{mapped}:{query}")

    @Slot(result=dict)
    def searchScore(self) -> dict:
        score = 0
        if self._svc:
            score += 30
        if self._qe:
            score += 25
        if self._action_registry:
            score += 15
        if self._notifications:
            score += 10
        score += min(10, len(self._results) * 2)
        return {
            "score": min(100, score),
            "has_service": self._svc is not None,
            "has_query_executor": self._qe is not None,
            "results_count": len(self._results),
            "is_searching": self._is_searching,
            "error_code": self._error_code or "",
        }
