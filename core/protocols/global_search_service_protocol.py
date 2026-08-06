from __future__ import annotations

from typing import Any, Callable, Protocol

from core.search.models import SearchRequest, SearchResponse


class GlobalSearchServiceProtocol(Protocol):
    """Canonical global search surface (Slice 6).

    ``search`` accepts either a domain-based ``SearchRequest`` (returns a
    ``SearchResponse`` — worker-thread core) or a legacy plain query string
    (returns the legacy dict). Async execution routes through QueryExecutor:
    an inoperative executor yields ``INFRASTRUCTURE_UNAVAILABLE`` instead of
    inline execution.
    """

    def search(
        self,
        request_or_query: SearchRequest | str,
        owner: str = "global_search",
        timeout_ms: int = 5000,
    ) -> SearchResponse | dict[str, Any]: ...
    def search_request(
        self,
        request: SearchRequest,
        cancel_check: Callable[[], None] | None = None,
    ) -> SearchResponse: ...
    def search_async(
        self,
        request_or_query: SearchRequest | str,
        owner: str = "global_search",
        timeout_ms: int = 5000,
        on_result: Callable | None = None,
        on_error: Callable | None = None,
    ) -> int: ...
    def cancel(self, owner: str = "global_search") -> None: ...
    def cancel_request(self, request_id: int) -> bool: ...
    def search_available(self) -> dict: ...
