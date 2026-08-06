"""Search domain models — canonical contracts for the Global Search slice (S6).

The service consumes ``SearchRequest`` and returns ``SearchResponse``; the UI
bridge never rewrites the query text with domain prefixes — domains travel in
``SearchRequest.domains`` and the query is always literal text.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class SearchDomain(str, enum.Enum):
    """A searchable domain. The registry owns one provider per domain."""

    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"
    RADIO = "radio"
    GENRE = "genre"
    FOLDER = "folder"
    DEVICE = "device"
    CONNECTION = "connection"
    ACTION = "action"
    SETTINGS = "settings"

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.value


# Result types exposed to the UI (QML section names are derived in the bridge).
RESULT_TYPE_BY_DOMAIN = {
    SearchDomain.TRACK: "track",
    SearchDomain.ALBUM: "album",
    SearchDomain.ARTIST: "artist",
    SearchDomain.PLAYLIST: "playlist",
    SearchDomain.RADIO: "radio",
    SearchDomain.GENRE: "genre",
    SearchDomain.FOLDER: "folder",
    SearchDomain.DEVICE: "device",
    SearchDomain.CONNECTION: "server",
    SearchDomain.ACTION: "action",
    SearchDomain.SETTINGS: "setting",
}

# Stable per-domain status codes. A per-domain failure never aborts the whole
# search: the response records it in ``status_codes``/``domains_failed``.
STATUS_OK = "OK"
FTS_AVAILABLE = "FTS_AVAILABLE"
FTS_UNAVAILABLE = "FTS_UNAVAILABLE"
FTS_SCHEMA_MISMATCH = "FTS_SCHEMA_MISMATCH"
FTS_FAILED = "FTS_FAILED"
LIKE_FALLBACK_USED = "LIKE_FALLBACK_USED"
DATABASE_BUSY = "DATABASE_BUSY"
DATABASE_LOCKED = "DATABASE_LOCKED"
DATABASE_CORRUPT = "DATABASE_CORRUPT"
QUERY_TIMEOUT = "QUERY_TIMEOUT"
QUERY_CANCELLED = "QUERY_CANCELLED"
PROVIDER_MISSING = "PROVIDER_MISSING"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
INFRASTRUCTURE_UNAVAILABLE = "INFRASTRUCTURE_UNAVAILABLE"
SEARCH_FAILED = "SEARCH_FAILED"

FAILURE_STATUSES = frozenset({
    DATABASE_BUSY, DATABASE_LOCKED, DATABASE_CORRUPT,
    QUERY_TIMEOUT, QUERY_CANCELLED, PROVIDER_MISSING,
    SERVICE_UNAVAILABLE, INFRASTRUCTURE_UNAVAILABLE, SEARCH_FAILED,
})


@dataclass(frozen=True)
class SearchRequest:
    """One search intent: literal query text + explicit domains.

    The query is NEVER interpreted for ``track:``/``album:`` style prefixes by
    the service; prefix parsing lives in the QML bridge layer, which converts
    user intent into a ``domains`` set.
    """

    query: str = ""
    domains: frozenset[SearchDomain] = field(default_factory=frozenset)
    limit_per_domain: int = 10
    total_limit: int = 50
    owner: str = "global_search"
    request_id: str = ""


@dataclass(frozen=True)
class SearchResultItem:
    """One search result with an explicit, actionable reference.

    ``public_ref`` follows the library convention (e.g. ``track_42``) and is
    the UI-facing identity; actions built from this item must carry
    result_id/result_type/public_ref, never a global selection.
    """

    result_id: str = ""
    result_type: str = ""
    public_ref: str = ""
    title: str = ""
    subtitle: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Aggregate result for one SearchRequest.

    ``error`` is non-empty only for terminal failures (e.g.
    INFRASTRUCTURE_UNAVAILABLE). Per-domain problems are recorded in
    ``status_codes`` and ``domains_failed`` and never abort the response.
    """

    items: list[SearchResultItem] = field(default_factory=list)
    domains_queried: set[SearchDomain] = field(default_factory=set)
    domains_failed: set[SearchDomain] = field(default_factory=set)
    status_codes: dict[str, str] = field(default_factory=dict)
    request_id: str = ""
    error: str = ""
    warnings: list[str] = field(default_factory=list)
