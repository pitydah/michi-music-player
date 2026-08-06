"""GlobalSearchBridge — thin QML adapter for the canonical GlobalSearchService.

Architecture (ADR-003 / Slice 6):
  QML debounce -> search(query) -> QueryExecutor/WorkerManager ->
  GlobalSearchService (worker thread) -> partial results -> QML.

The bridge NEVER executes searches inline: without a QueryExecutor it returns
``INFRASTRUCTURE_UNAVAILABLE`` (no synchronous fallback). It is the ONLY layer
that parses domain intent (``searchDomain`` maps a domain key to a
``SearchDomain`` set — the service only ever sees the clean literal query plus
``SearchRequest.domains``). Result actions are executed with an explicit
``ActionContext`` (result_id/result_type/public_ref/selection_version), never
through the global selection.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.action_context import ActionContext
from core.search.models import SearchDomain, SearchRequest, SearchResultItem

logger = logging.getLogger("michi.global_search")

_MAX_TOTAL = 50

# Singular UI keys -> SearchDomain. Plural/legacy keys live in _DOMAIN_ALIASES.
DOMAIN_MAP = {
    "track": SearchDomain.TRACK,
    "album": SearchDomain.ALBUM,
    "artist": SearchDomain.ARTIST,
    "playlist": SearchDomain.PLAYLIST,
    "folder": SearchDomain.FOLDER,
    "genre": SearchDomain.GENRE,
    "device": SearchDomain.DEVICE,
    "server": SearchDomain.CONNECTION,
    "action": SearchDomain.ACTION,
    "setting": SearchDomain.SETTINGS,
}

_DOMAIN_ALIASES = {
    "tracks": SearchDomain.TRACK,
    "albums": SearchDomain.ALBUM,
    "artists": SearchDomain.ARTIST,
    "playlists": SearchDomain.PLAYLIST,
    "folders": SearchDomain.FOLDER,
    "genres": SearchDomain.GENRE,
    "radio": SearchDomain.RADIO,
    "devices": SearchDomain.DEVICE,
    "connection": SearchDomain.CONNECTION,
    "connections": SearchDomain.CONNECTION,
    "actions": SearchDomain.ACTION,
    "settings": SearchDomain.SETTINGS,
}

_SECTION_BY_TYPE = {
    "track": "Canciones",
    "album": "Álbumes",
    "artist": "Artistas",
    "playlist": "Playlists",
    "folder": "Carpetas",
    "genre": "Géneros",
    "radio": "Radio",
    "device": "Dispositivos",
    "server": "Servidores",
    "action": "Acciones",
    "setting": "Ajustes",
}

_ACTION_ID_BY_LEGACY_ACTION = {
    "play": "track_play_now",
    "add_to_queue": "track_add_to_queue",
}


class GlobalSearchBridge(QObject):
    resultsChanged = Signal()
    searchingChanged = Signal()
    partialResults = Signal(str, list)
    staleResultDropped = Signal(str)

    def __init__(
        self,
        search_service=None,
        query_executor=None,
        action_registry=None,
        navigation_bridge=None,
        page_state_store=None,
        capability_bridge=None,
        accessibility_bridge=None,
        notification_bridge=None,
        parent=None,
    ):
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

    def set_notification_bridge(self, notification) -> None:
        """Second-phase wiring for the NotificationBridge (Corrección 3)."""
        self._notifications = notification

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

    def _on_search_done(self, result, request_id: int):
        if self._is_stale(request_id):
            self.staleResultDropped.emit(self._query)
            return
        if isinstance(result, dict) and result.get("ok"):
            raw_results = result.get("results", [])
        else:
            self._error_code = (
                result.get("error_code", "SEARCH_FAILED")
                if isinstance(result, dict) else "SEARCH_FAILED"
            )
            self._error_message = (
                result.get("message", "Search failed")
                if isinstance(result, dict) else "Search failed"
            )
            self._results = []
            self._is_searching = False
            self.searchingChanged.emit()
            self.resultsChanged.emit()
            return
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
        self.searchingChanged.emit()
        self.resultsChanged.emit()

    # ── Search ────────────────────────────────────────────────────────────

    @Slot(str, result=dict)
    def search(self, query: str):
        """Full-domain search. Always async via QueryExecutor."""
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

        if not (self._svc and callable(getattr(self._svc, "search", None))):
            return self._fail_search("SERVICE_UNAVAILABLE", "No search service")
        if not (self._qe and hasattr(self._qe, "submit")):
            return self._fail_search(
                "INFRASTRUCTURE_UNAVAILABLE",
                "QueryExecutor not available; async search unavailable",
            )

        self._is_searching = True
        self._error_code = ""
        self._error_message = ""
        self.searchingChanged.emit()

        def _run():
            if self._is_stale(request_id):
                return {"ok": False, "error": "STALE"}
            try:
                result = self._svc.search(q, owner=self._owner, timeout_ms=5000)
                if self._is_stale(request_id):
                    self.staleResultDropped.emit(q)
                    return {"ok": False, "error": "STALE"}
                return result
            except Exception as e:
                return {"ok": False, "error_code": "SEARCH_FAILED", "message": str(e)}

        self._qe.submit(
            owner=self._owner,
            callable_fn=_run,
            on_success=lambda res: self._on_search_done(res, request_id),
            on_error=lambda code, msg: self._on_search_done(
                {"ok": False, "error_code": code, "message": msg}, request_id),
            supersede=True,
            cancellable=True,
        )
        return {"ok": True, "async": True, "request_id": request_id}

    @Slot(str, str, result=dict)
    def searchDomain(self, domain: str, query: str):
        """Domain-scoped search: maps the UI domain key to a SearchDomain set.

        The raw query text is never prefixed — the service receives the clean
        query plus explicit domains in the SearchRequest.
        """
        search_domain = DOMAIN_MAP.get(domain, _DOMAIN_ALIASES.get(domain))
        domains = {search_domain} if search_domain else frozenset(SearchDomain)
        return self._search_with_domains(query, domains)

    def _search_with_domains(self, query: str, domains):
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

        if not (self._svc and callable(getattr(self._svc, "search", None))):
            return self._fail_search("SERVICE_UNAVAILABLE", "No search service")
        if not (self._qe and hasattr(self._qe, "submit")):
            return self._fail_search(
                "INFRASTRUCTURE_UNAVAILABLE",
                "QueryExecutor not available; async search unavailable",
            )

        self._is_searching = True
        self._error_code = ""
        self._error_message = ""
        self.searchingChanged.emit()

        def _run():
            if self._is_stale(request_id):
                return {"ok": False, "error": "STALE"}
            try:
                request = SearchRequest(
                    query=q, domains=frozenset(domains),
                    limit_per_domain=10, total_limit=_MAX_TOTAL,
                    owner=self._owner, request_id=str(request_id),
                )
                response = self._svc.search(request)
                if self._is_stale(request_id):
                    self.staleResultDropped.emit(q)
                    return {"ok": False, "error": "STALE"}
                return self._response_to_legacy(response, request_id)
            except Exception as e:
                return {"ok": False, "error_code": "SEARCH_FAILED", "message": str(e)}

        self._qe.submit(
            owner=self._owner,
            callable_fn=_run,
            on_success=lambda res: self._on_search_done(res, request_id),
            on_error=lambda code, msg: self._on_search_done(
                {"ok": False, "error_code": code, "message": msg}, request_id),
            supersede=True,
            cancellable=True,
        )
        return {"ok": True, "async": True, "request_id": request_id}

    @staticmethod
    def _response_to_legacy(response, request_id: int) -> dict:
        """Convert a SearchResponse into the bridge's dict result shape."""
        results = []
        for item in response.items:
            if not isinstance(item, SearchResultItem):
                continue
            extra = dict(item.extra or {})
            entry = {
                "type": item.result_type,
                "id": item.result_id,
                "result_id": item.result_id,
                "result_type": item.result_type,
                "public_ref": item.public_ref,
                "title": item.title,
                "subtitle": item.subtitle,
                "section": _SECTION_BY_TYPE.get(item.result_type, "Otros"),
                "score": float(extra.pop("score", 0.5)),
            }
            entry.update(extra)
            results.append(entry)
        return {"ok": True, "request_id": request_id,
                "results": results, "count": len(results)}

    def _fail_search(self, code: str, message: str) -> dict:
        self._results = []
        self._is_searching = False
        self._error_code = code
        self._error_message = message
        self.searchingChanged.emit()
        self.resultsChanged.emit()
        return {"ok": False, "error": code, "error_code": code, "message": message}

    @Slot(result=dict)
    def cancel(self):
        self._active_request_id = 0
        if self._qe and hasattr(self._qe, "cancel_owner"):
            self._qe.cancel_owner(self._owner)
        if self._svc and hasattr(self._svc, "cancel"):
            import contextlib
            with contextlib.suppress(Exception):
                self._svc.cancel(owner=self._owner)
        self._is_searching = False
        self._search_gen += 1
        self._results = []
        self.searchingChanged.emit()
        self.resultsChanged.emit()
        return {"ok": True}

    # ── Result actions (explicit context — never global selection) ────────

    @Slot(str, str, result=dict)
    def executeResultAction(self, result_id: str, action: str):
        """Legacy slot (QML stability). Resolves the result item by id and
        executes with an explicit ActionContext built from that item."""
        item = self._find_result_item(result_id)
        if item is None:
            return {"ok": False, "error": "NOT_FOUND",
                    "result_id": result_id, "action": action}
        if action == "navigate":
            route = item.get("route", item.get("type", ""))
            if route and self._navigation:
                if self._page_state:
                    self._page_state.saveState("search", {
                        "query": self._query,
                        "results": self._results[:10],
                    })
                self._navigation.navigate(route)
                return {"ok": True, "route": route}
            return {"ok": False, "error": "NO_ROUTE"}
        action_id = _ACTION_ID_BY_LEGACY_ACTION.get(action)
        if not action_id:
            return {"ok": False, "error": "UNKNOWN_ACTION"}
        return self._execute_with_context(
            item, action_id, self._active_request_id, params={})

    @Slot(str, str, str, str, str, result=dict)
    @Slot(str, str, str, str, str, "QVariantMap", result=dict)
    def executeSearchResultAction(
        self,
        result_id: str,
        result_type: str,
        public_ref: str,
        action_id: str,
        request_id: str,
        params: dict | None = None,
    ):
        """Execute an action on an explicit search result.

        Builds an ActionContext(entity_type=result_type, entity_id=result_id,
        public_ref=public_ref, selection_version=request_id,
        source_route="search", source_component="global_search") and executes
        through the ActionRegistry. Never falls back to global selection.
        """
        if self._action_registry is None:
            return {"ok": False, "error": "NO_ACTION_REGISTRY"}
        try:
            selection_version = int(request_id or 0)
        except (TypeError, ValueError):
            selection_version = 0
        selected_ids = (int(result_id),) if str(result_id).isdigit() else ()
        context = ActionContext(
            entity_type=str(result_type or ""),
            entity_id=str(result_id or ""),
            public_ref=str(public_ref or ""),
            selection_version=selection_version,
            source_route="search",
            source_component="global_search",
            selected_ids=selected_ids,
            parameters=dict(params or {}),
        )
        try:
            result = self._action_registry.execute(str(action_id or ""), context)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return result if isinstance(result, dict) else {"ok": True}

    def _find_result_item(self, result_id: str) -> dict | None:
        needle = str(result_id)
        for r in self._results:
            if (str(r.get("id", "")) == needle
                    or str(r.get("result_id", "")) == needle):
                return r
        return None

    def _execute_with_context(
        self, item: dict, action_id: str, request_id: int, params: dict
    ) -> dict:
        if self._action_registry is None:
            return {"ok": False, "error": "NO_ACTION_REGISTRY"}
        result_id = str(item.get("id") or item.get("result_id") or "")
        result_type = str(item.get("type") or item.get("result_type") or "")
        public_ref = str(item.get("public_ref") or "")
        return self.executeSearchResultAction(
            result_id, result_type, public_ref, action_id, str(request_id), params,
        )

    @Slot(result=dict)
    def restoreLastSearch(self):
        if self._page_state and self._page_state.hasState("search"):
            state = self._page_state.restoreState("search")
            q = state.get("query", "")
            if q:
                return self.search(q)
        return {"ok": False, "error": "NO_SAVED_SEARCH"}

    @Slot(result="QVariantMap")
    def getCapabilities(self):
        caps = {}
        if self._svc:
            caps["has_service"] = True
        if self._qe:
            caps["has_query_executor"] = True
        if self._action_registry:
            caps["has_action_registry"] = True
        if self._navigation:
            caps["has_navigation"] = True
        if self._page_state:
            caps["has_page_state"] = True
        if self._capability:
            caps["has_capability"] = True
        if self._accessibility:
            caps["has_accessibility"] = True
        if self._notifications:
            caps["has_notifications"] = True
        return caps

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
