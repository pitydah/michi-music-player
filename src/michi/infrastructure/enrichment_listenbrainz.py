"""ListenBrainz supplemental provider (R4 §22C/§22AO).

POST-identity supplementary metadata only:
- MBID input only (never a resolver, never identity mutation);
- bounded requests, meaningful User-Agent;
- no user token required for the supported MBID metadata endpoints;
- no listens submitted, no telemetry.

If an endpoint ever starts requiring authentication, fail
optional-provider-only: core enrichment must stay usable.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from urllib.parse import quote

from michi.application.enrichment_ports import (
    EnrichmentProviderError,
    ListenBrainzSupplementalProviderPort,
)
from michi.domain.enrichment import (
    KnowledgeProvenance,
    SupplementalAlbumKnowledge,
    SupplementalArtistKnowledge,
)
from michi.infrastructure.enrichment_http import (
    HttpTransportPort,
    validate_provider_url,
)

logger = logging.getLogger(__name__)

LB_API_ROOT = "https://api.listenbrainz.org/1"


def _utc_now_iso() -> str:
    import datetime

    return datetime.datetime.now(datetime.UTC).isoformat()


def _provider_url(endpoint: str, mbid: str) -> str:
    """Allowlisted LB metadata URL (MBID-only input)."""
    validate_provider_url(LB_API_ROOT)
    return f"{LB_API_ROOT}/{endpoint}/{quote(mbid)}/metadata"


class ListenBrainzRateLimiter:
    """LB public API is permissive; keep a conservative 1 req/s window."""

    def __init__(
        self, min_interval_s: float = 1.0, clock: Callable[[], float] = time.monotonic
    ):
        self._min_interval_s = min_interval_s
        self._clock = clock
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            elapsed = now - self._last
            if elapsed < self._min_interval_s:
                time.sleep(self._min_interval_s - elapsed)
            self._last = self._clock()


def _parse_tags(payload: dict) -> tuple[str, ...]:
    """LB metadata payload: ``tags`` is a list of {tag, count} objects
    (community listening tags); tolerate any supported shape and return
    the sorted tag names."""
    raw = payload.get("tags")
    tags: list[str] = []
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict) and isinstance(entry.get("tag"), str):
                name = entry["tag"].strip()
            elif isinstance(entry, str):
                name = entry.strip()
            else:
                continue
            if name:
                tags.append(name.casefold())
    return tuple(sorted(set(tags)))


def _parse_popularity(payload: dict) -> int:
    """LB metadata may include community context; tolerate absence."""
    value = payload.get("popularity_percent")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(100, int(value)))


class ListenBrainzSupplementalProvider(ListenBrainzSupplementalProviderPort):
    """Metadata endpoint client with transport, cache and bounded reads.

    The provider is OPTIONAL: any failure surfaces as an exception the
    coordinator treats as optional-provider-only (never breaks core)."""

    def __init__(
        self,
        transport: HttpTransportPort,
        cache=None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], str] = _utc_now_iso,
    ) -> None:
        from michi.infrastructure.enrichment_knowledge import _CachedGetter

        self._transport = transport
        self._getter = _CachedGetter(
            transport,
            cache,
            limiter=ListenBrainzRateLimiter(),
            sleeper=sleeper,
            clock=clock,
        )

    def fetch_artist_metadata(self, artist_mbid: str) -> SupplementalArtistKnowledge:
        if not artist_mbid:
            raise EnrichmentProviderError("listenbrainz: MBID required")
        url = _provider_url("artist", artist_mbid)
        payload, is_stale, retrieved_at = self._getter.get_json(
            url, "listenbrainz_artist_metadata", allow_stale=True
        )
        tags = _parse_tags(payload)
        popularity = _parse_popularity(payload)
        return SupplementalArtistKnowledge(
            tags=tags,
            popularity_percent=popularity,
            provenance=KnowledgeProvenance(
                provider="listenbrainz",
                external_entity_id=artist_mbid,
                source_url=url,
                retrieved_at=retrieved_at,
                # POST-R4 P11: el fallback stale del cache se proyecta —
                # la provenance dice la verdad sobre la edad del dato.
                is_stale=is_stale,
            ),
        )

    def fetch_release_group_metadata(
        self, release_group_mbid: str
    ) -> SupplementalAlbumKnowledge:
        if not release_group_mbid:
            raise EnrichmentProviderError("listenbrainz: RG MBID required")
        url = _provider_url("release-group", release_group_mbid)
        payload, is_stale, retrieved_at = self._getter.get_json(
            url, "listenbrainz_release_group_metadata", allow_stale=True
        )
        tags = _parse_tags(payload)
        popularity = _parse_popularity(payload)
        return SupplementalAlbumKnowledge(
            tags=tags,
            popularity_percent=popularity,
            provenance=KnowledgeProvenance(
                provider="listenbrainz",
                external_entity_id=release_group_mbid,
                source_url=url,
                retrieved_at=retrieved_at,
                is_stale=is_stale,
            ),
        )
