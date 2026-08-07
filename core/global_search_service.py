"""GlobalSearchService — canonical cross-domain search (Slice 6).

Contract
--------
- ``search(request: SearchRequest) -> SearchResponse`` is the SYNCHRONOUS core.
  It dispatches per domain through the ``SearchProviderRegistry`` on the
  caller's thread — providers open their own read-only connections, so this
  must only run on worker threads, never on the QML thread.
- ``search_async(...)`` routes through ``QueryExecutor`` (backed by
  ``WorkerManager``). It never schedules work via the Qt event loop and never falls back
  to inline execution: when the executor is missing or not operative the
  caller receives ``INFRASTRUCTURE_UNAVAILABLE``.
- Every FTS/fallback failure is recorded with a typed status code per domain
  (``status_codes`` / ``domains_failed``) — nothing is swallowed.

The legacy ``search(query_str, ...)`` / ``search_async(query_str, ...)``
signatures are kept for backward compatibility and delegate to the same core.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import Any, Callable

from core.search.models import (
    INFRASTRUCTURE_UNAVAILABLE,
    PROVIDER_MISSING,
    SEARCH_FAILED,
    SearchDomain,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from core.search.providers import (
    SearchProviderRegistry,
    build_default_registry,
)

logger = logging.getLogger("michi.global_search")

_MAX_PER_DOMAIN = 10
_MAX_TOTAL = 50
_DEFAULT_TIMEOUT_MS = 5000

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

# Stable dispatch order (matches the QML section order).
_DOMAIN_ORDER = (
    SearchDomain.TRACK,
    SearchDomain.ALBUM,
    SearchDomain.ARTIST,
    SearchDomain.PLAYLIST,
    SearchDomain.FOLDER,
    SearchDomain.GENRE,
    SearchDomain.RADIO,
    SearchDomain.DEVICE,
    SearchDomain.CONNECTION,
    SearchDomain.ACTION,
    SearchDomain.SETTINGS,
)

_DEFAULT_DOMAINS = frozenset(SearchDomain)


class SearchError(Exception):
    """Typed legacy error raised by the synchronous legacy search path."""

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


def _db_path_of(conn_source: Any) -> str:
    if isinstance(conn_source, str):
        return conn_source
    return str(getattr(conn_source, "db_path", "") or "")


class GlobalSearchService:
    """Thread-safe global search with per-domain provider dispatch."""

    def __init__(
        self,
        db_path: str = "",
        connection_factory: Any = None,
        provider_registry: SearchProviderRegistry | None = None,
        query_executor: Any = None,
        worker_manager: Any = None,
    ):
        self._db_path = db_path or _db_path_of(connection_factory)
        self._query_executor = query_executor
        self._worker_manager = worker_manager
        self._registry = provider_registry or build_default_registry(self._db_path)

        # Legacy cancellation bookkeeping (per owner, sync path).
        self._counter = 0
        self._counter_lock = threading.Lock()
        self._generation: dict[str, int] = {}
        self._gen_lock = threading.Lock()
        self._active: dict[str, dict] = {}
        self._active_lock = threading.Lock()

    # ── Legacy helpers ────────────────────────────────────────────────────

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

    # ── Public API ────────────────────────────────────────────────────────

    def search(
        self,
        request_or_query: SearchRequest | str,
        owner: str = "global_search",
        timeout_ms: int = _DEFAULT_TIMEOUT_MS,
    ) -> SearchResponse | dict[str, Any]:
        """Canonical synchronous core.

        With a ``SearchRequest`` returns a ``SearchResponse`` (worker-thread
        use). With a legacy ``str`` query returns the legacy dict shape
        (``ok``/``results``/``count``/``request_id``) and raises
        ``SearchStaleError``/``SearchCancelledError`` on supersession/cancel.
        """
        if isinstance(request_or_query, SearchRequest):
            return self.search_request(request_or_query)
        return self._search_legacy(request_or_query, owner, timeout_ms)

    def search_request(
        self,
        request: SearchRequest,
        cancel_check: Callable[[], None] | None = None,
    ) -> SearchResponse:
        """Dispatch a SearchRequest through the provider registry.

        Per-domain failures are recorded (typed status codes) and never abort
        the response. ``cancel_check`` raises ``SearchCancelledError`` /
        ``SearchStaleError`` at domain boundaries (legacy sync path only).
        """
        query = (request.query or "").strip()
        if not query:
            return SearchResponse(
                items=[], domains_queried=set(), domains_failed=set(),
                status_codes={}, request_id=request.request_id,
                error="", warnings=[],
            )

        domains = request.domains or _DEFAULT_DOMAINS
        limit_per = max(1, request.limit_per_domain or _MAX_PER_DOMAIN)
        total = max(1, request.total_limit or _MAX_TOTAL)

        items: list[SearchResultItem] = []
        domains_queried: set[SearchDomain] = set()
        domains_failed: set[SearchDomain] = set()
        status_codes: dict[str, str] = {}
        warnings: list[str] = []

        for domain in _DOMAIN_ORDER:
            if domain not in domains:
                continue
            provider = self._registry.provider(domain)
            if provider is None:
                domains_failed.add(domain)
                status_codes[domain.name] = PROVIDER_MISSING
                warnings.append(f"{domain.name}: no provider registered")
                continue
            if cancel_check:
                cancel_check()
            domains_queried.add(domain)
            try:
                domain_items, status = provider(request, limit_per)
            except (SearchCancelledError, SearchStaleError):
                raise
            except sqlite3.DatabaseError as exc:
                status = self._map_sqlite_status(exc)
                domains_failed.add(domain)
                status_codes[domain.name] = status
                warnings.append(f"{domain.name}: {status}")
                continue
            except Exception as exc:  # noqa: BLE001 — typed, never swallowed
                status = SEARCH_FAILED
                domains_failed.add(domain)
                status_codes[domain.name] = status
                warnings.append(f"{domain.name}: {status}: {exc}")
                logger.warning("Search domain %s failed: %s", domain, exc)
                continue
            status_codes[domain.name] = status
            if status in (
                "DATABASE_BUSY", "DATABASE_LOCKED", "DATABASE_CORRUPT",
                "QUERY_TIMEOUT", "QUERY_CANCELLED", "SERVICE_UNAVAILABLE",
                "INFRASTRUCTURE_UNAVAILABLE", "SEARCH_FAILED",
            ):
                domains_failed.add(domain)
                warnings.append(f"{domain.name}: {status}")
            items.extend(domain_items)
            if cancel_check:
                cancel_check()
            if len(items) >= total:
                warnings.append("total_limit reached")
                break

        items.sort(
            key=lambda i: float((i.extra or {}).get("score", 0.5)), reverse=True
        )
        return SearchResponse(
            items=items[:total],
            domains_queried=domains_queried,
            domains_failed=domains_failed,
            status_codes=status_codes,
            request_id=request.request_id,
            error="",
            warnings=warnings,
        )

    def search_async(
        self,
        request_or_query: SearchRequest | str,
        owner: str = "global_search",
        timeout_ms: int = _DEFAULT_TIMEOUT_MS,
        on_result: Callable | None = None,
        on_error: Callable | None = None,
    ) -> int:
        """Async search through QueryExecutor/WorkerManager.

        New-style: ``search_async(request, on_result=cb)`` — cb receives the
        ``SearchResponse``. Legacy: ``search_async(query, owner, timeout_ms,
        on_result, on_error)`` — cb receives the legacy dict.

        Never schedules via the Qt event loop, never inline: without an operative
        executor the caller immediately receives ``INFRASTRUCTURE_UNAVAILABLE``.
        """
        if isinstance(request_or_query, SearchRequest):
            callback = owner if callable(owner) else on_result
            return self._submit_search(request_or_query, callback)
        return self._submit_legacy_search(
            request_or_query, owner, timeout_ms, on_result, on_error
        )

    def cancel(self, owner: str = "global_search") -> None:
        """Legacy cancellation marker for the synchronous path."""
        with self._active_lock:
            req = self._active.get(owner)
            if req and not req.get("cancelled"):
                req["cancelled"] = True

    def cancel_request(self, request_id: int) -> bool:
        with self._active_lock:
            for req in self._active.values():
                if req.get("request_id") == request_id and not req.get("cancelled"):
                    req["cancelled"] = True
                    return True
        return False

    def search_available(self) -> dict:
        """Truthful capability: available only when the whole chain works.

        Conditions: service registered (self), query executor operative (has a
        live WorkerManager), WorkerManager active (not shutdown), database
        readable (quick probe), and at least one provider registered. Returns
        reasons when unavailable.
        """
        reasons: list[str] = []
        if self._registry.count() == 0:
            reasons.append("no search providers registered")
        qe = self._query_executor
        if qe is None or not callable(getattr(qe, "submit", None)):
            reasons.append("query_executor missing")
        else:
            operative = getattr(qe, "operative", None)
            if not callable(operative):
                reasons.append("query_executor without operative probe")
            elif not bool(operative()):
                reasons.append("query_executor not operative "
                               "(needs an active WorkerManager)")
        wm = self._worker_manager
        if wm is not None:
            is_down = getattr(wm, "is_shutdown", None)
            if callable(is_down):
                if bool(is_down()):
                    reasons.append("worker_manager shutdown")
            elif is_down:
                reasons.append("worker_manager shutdown")
        if not self._db_path:
            reasons.append("no database path")
        else:
            if not self._probe_db():
                reasons.append("database not readable")
        ok = not reasons
        return {"ok": ok, "reasons": reasons, "code": "; ".join(reasons)}

    # ── Internal ──────────────────────────────────────────────────────────

    def _probe_db(self) -> bool:
        try:
            conn = sqlite3.connect(self._db_path, timeout=2.0)
            try:
                conn.execute("PRAGMA query_only = 1")
                conn.execute("SELECT 1").fetchone()
            finally:
                conn.close()
            return True
        except sqlite3.Error:
            return False

    def _executor_operative(self) -> bool:
        qe = self._query_executor
        if qe is None or not callable(getattr(qe, "submit", None)):
            return False
        operative = getattr(qe, "operative", None)
        if not callable(operative):
            return False
        try:
            return bool(operative())
        except Exception:
            return False

    def _submit_search(self, request: SearchRequest, on_result: Callable | None) -> int:
        if not self._executor_operative():
            response = SearchResponse(
                items=[], domains_queried=set(), domains_failed=set(),
                status_codes={}, request_id=request.request_id,
                error=INFRASTRUCTURE_UNAVAILABLE,
                warnings=["QueryExecutor/WorkerManager not operative; "
                          "async search unavailable"],
            )
            self._safe_callback(on_result, response)
            return 0
        return self._query_executor.submit(
            owner=request.owner or "global_search",
            callable_fn=lambda: self.search_request(request),
            on_success=(lambda r: self._safe_callback(on_result, r))
            if on_result else None,
            on_error=None,
            on_cancelled=None,
            request_context={"kind": "global_search",
                             "request_id": request.request_id},
            supersede=True,
            cancellable=True,
        )

    def _submit_legacy_search(
        self,
        query: str,
        owner: str,
        timeout_ms: int,
        on_result: Callable | None,
        on_error: Callable | None,
    ) -> int:
        if not self._executor_operative():
            result = {
                "ok": False,
                "error_code": INFRASTRUCTURE_UNAVAILABLE,
                "message": "QueryExecutor/WorkerManager not operative",
                "request_id": 0,
            }
            self._safe_callback(on_result, result)
            return 0

        def _run() -> dict:
            try:
                return self.search(query, owner=owner, timeout_ms=timeout_ms)
            except SearchStaleError:
                return {"ok": False, "error": "STALE"}
            except SearchCancelledError:
                return {"ok": False, "error": "CANCELLED"}
            except SearchError as exc:
                return {"ok": False, "error_code": exc.code, "message": exc.message}

        def _done(result: dict) -> None:
            if not on_result:
                return
            if result.get("error") in ("STALE", "CANCELLED"):
                return  # legacy semantics: silently drop
            self._safe_callback(on_result, result)

        legacy_on_error = on_error

        def _failed(code: str, message: str) -> None:
            if legacy_on_error:
                self._safe_callback(legacy_on_error, f"{code}: {message}")

        self._query_executor.submit(
            owner=owner or "global_search",
            callable_fn=_run,
            on_success=_done,
            on_error=_failed,
            on_cancelled=None,
            request_context={"kind": "global_search_legacy"},
            supersede=True,
            cancellable=True,
        )
        return 0

    def _search_legacy(
        self, query: str, owner: str, timeout_ms: int
    ) -> dict[str, Any]:
        q = (query or "").strip()
        request_id = self._next_id()
        if not q:
            return {"ok": True, "request_id": request_id, "results": [], "count": 0}

        gen = self._next_gen(owner)
        with self._active_lock:
            prev = self._active.get(owner)
            if prev and not prev.get("cancelled"):
                prev["cancelled"] = True
            self._active[owner] = {"request_id": request_id, "cancelled": False}

        deadline = time.time() + timeout_ms / 1000.0

        def _check() -> None:
            if time.time() > deadline:
                raise SearchCancelledError()
            with self._active_lock:
                req = self._active.get(owner)
                if req and req.get("cancelled"):
                    raise SearchCancelledError()
            if self._is_stale(owner, gen):
                raise SearchStaleError()

        try:
            request = SearchRequest(
                query=q,
                domains=_DEFAULT_DOMAINS,
                limit_per_domain=_MAX_PER_DOMAIN,
                total_limit=_MAX_TOTAL,
                owner=owner,
                request_id=str(request_id),
            )
            response = self.search_request(request, cancel_check=_check)
            if self._is_stale(owner, gen):
                raise SearchStaleError()
            if (response.domains_queried
                    and response.domains_queried.issubset(response.domains_failed)
                    and not response.items):
                raise SearchError(
                    "SERVICE_UNAVAILABLE",
                    "No search domain was queryable: "
                    + "; ".join(sorted(response.status_codes.values())),
                )
            with self._active_lock:
                if self._active.get(owner, {}).get("request_id") == request_id:
                    self._active[owner]["cancelled"] = False
            results = [self._legacy_item(i) for i in response.items]
            return {
                "ok": True,
                "request_id": request_id,
                "results": results,
                "count": len(results),
            }
        except (SearchCancelledError, SearchStaleError):
            raise
        except Exception as exc:
            raise SearchError("SEARCH_FAILED", str(exc)) from exc

    @staticmethod
    def _legacy_item(item: SearchResultItem) -> dict[str, Any]:
        extra = dict(item.extra or {})
        base = {
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
        base.update(extra)
        return base

    @staticmethod
    def _map_sqlite_status(exc: sqlite3.DatabaseError) -> str:
        msg = str(exc).lower()
        if "busy" in msg:
            return "DATABASE_BUSY"
        if "locked" in msg:
            return "DATABASE_LOCKED"
        if "corrupt" in msg:
            return "DATABASE_CORRUPT"
        return SEARCH_FAILED

    @staticmethod
    def _safe_callback(callback: Callable | None, *args: Any) -> None:
        if not callback:
            return
        try:
            callback(*args)
        except Exception:
            logger.exception("Search callback failed")
