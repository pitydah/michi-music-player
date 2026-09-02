"""MusicBrainz identity resolver + knowledge adapter (M6.9C/M6.9E).

MusicBrainz is the IDENTITY MASTER. Strict untrusted-JSON validation:
wrong types are never coerced into domain candidates; malformed top-
level payloads raise EnrichmentProviderError; malformed single
candidates are skipped; candidate order is deterministic (external ID
ascending) — provider score never influences identity.

Policy: central rate limiter (<= 1 request/sec), bounded retries only
for 429/502/503/504 (max 3 attempts; Retry-After honored; else 1s/2s),
provider response cache with TTLs (search 7d / lookup 30d), max 5
artist candidates and bounded release-group browse paging.

M6.9 REOPENED (provider contract completion): the release-group browse
endpoint never passes ``type=release-group`` (the endpoint entity is not
a valid value of the ``type`` filter). Lucene query syntax is escaped
separately from URL encoding; every request URL is built through the
central helpers so a request is auditable without re-interpolating.
"""

import json
import time
from urllib.parse import quote, urlencode

from michi.application.enrichment_ports import (
    EnrichmentProviderError,
    ExternalIdentityResolverPort,
    HttpRequest,
    HttpTransportPort,
    ProviderCachePort,
)
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    ArtistCandidate,
    ArtistIdentityEvidence,
    LocalAlbumEvidence,
    ReleaseEditionCandidate,
    ReleaseGroupCandidate,
    dedupe_identity_ids,
)
from michi.infrastructure.enrichment_http import (
    MusicBrainzRateLimiter,
    ProviderRequestExecutor,
)
from michi.infrastructure.enrichment_provider_cache import (
    DEFAULT_TTLS_SECONDS,
)

API_ROOT = "https://musicbrainz.org/ws/2"
MAX_ARTIST_CANDIDATES = 5
# M6.9 REOPENED: release-group browse pagination (bounded). A page that
# returns fewer than PAGE_SIZE items is the last one; never download a
# full discography by default.
RELEASE_GROUP_PAGE_SIZE = 100
MAX_RELEASE_GROUP_PAGES = 3
MAX_RELEASE_GROUPS_TOTAL = 300
_MAX_RELEASE_EDITION_LOOKUPS = 5
_RETRYABLE_STATUS = (429, 502, 503, 504)

# Lucene special characters in the MusicBrainz search syntax. These must
# be backslash-escaped INSIDE a field value — urllib.parse.quote() only
# handles URL encoding and does NOT make a value safe for Lucene.
_LUCENE_SPECIALS = set('+-&|!(){}[]^"~*?:\\/')


def _require_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EnrichmentProviderError(
            f"provider payload field {key!r} missing or not a non-blank str"
        )
    return value


def escape_musicbrainz_lucene(value: str) -> str:
    """M6.9 REOPENED: escape MusicBrainz Lucene query syntax.

    URL-encoding (quote) does NOT make a value safe inside a Lucene
    query: characters like ``:``, ``/``, ``+``, ``(``, ``)``, ``"`` are
    syntax in the search dialect. Every special character is prefixed
    with a backslash; the result is a valid literal for a field query.
    """
    return "".join(f"\\{ch}" if ch in _LUCENE_SPECIALS else ch for ch in value)


def _musicbrainz_query_url(
    endpoint: str, params: dict[str, str], ttl_category: str
) -> str:
    """M6.9 REOPENED: central request construction — one auditable place.

    ``params`` values are URL-encoded with urlencode (no manual
    interpolation of local input); the endpoint is a fixed allowlisted
    path under API_ROOT."""
    query = urlencode(params)
    return f"{API_ROOT}/{endpoint}?{query}"


def _require_list(payload: dict, key: str) -> list:
    value = payload.get(key)
    if not isinstance(value, list):
        raise EnrichmentProviderError(
            f"provider payload field {key!r} missing or not a list"
        )
    return value


def _optional_int(payload: dict, key: str) -> int:
    value = payload.get(key)
    if value is None or value == "":
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise EnrichmentProviderError(f"provider payload field {key!r} not an integer")
    return int(value)


def _optional_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise EnrichmentProviderError(f"provider payload field {key!r} not a str")
    return value


def _first_release_year(payload: dict) -> int:
    """first-release-date: 'YYYY' | 'YYYY-MM-DD' | 'YYYY-MM' | ''."""
    raw = _optional_str(payload, "first-release-date")
    if not raw:
        return 0
    digits = "".join(ch for ch in raw[:4] if ch.isdigit())
    if len(digits) == 4:
        return int(digits)
    return 0


class MusicBrainzIdentityResolver(ExternalIdentityResolverPort):
    """Strict, deterministic MusicBrainz identity candidate source."""

    def __init__(
        self,
        transport: HttpTransportPort,
        limiter: MusicBrainzRateLimiter,
        cache: ProviderCachePort | None = None,
        retry_sleeper=time.sleep,
    ) -> None:
        # R1: ONE shared bounded retry policy (ProviderRequestExecutor).
        self._executor = ProviderRequestExecutor(
            transport, limiter, sleeper=retry_sleeper
        )
        self._cache = cache

    # -- transport --------------------------------------------------------

    def _get_json(self, url: str, ttl_category: str) -> dict:
        # R1: IDENTITY resolution uses FRESH cache only — a cache hit
        # never consumes a rate-limit slot; a physical attempt always
        # goes through the limiter inside ProviderRequestExecutor.
        if self._cache is not None:
            cached = self._cache.get(ttl_category, url)
            if cached is not None:
                return self._parse_json(cached.body, url)
        response = self._executor.get(HttpRequest(url=url))
        payload = self._parse_json(response.body, url)
        if self._cache is not None:
            self._cache.put(
                ttl_category,
                url,
                response,
                ttl_seconds=DEFAULT_TTLS_SECONDS.get(
                    ttl_category, DEFAULT_TTLS_SECONDS["musicbrainz_search"]
                ),
                etag=response.headers.get("etag", ""),
                last_modified=response.headers.get("last-modified", ""),
            )
        return payload

    @staticmethod
    def _parse_json(body: bytes, url: str) -> dict:
        try:
            payload = json.loads(body)
        except ValueError as exc:
            raise EnrichmentProviderError(
                f"provider returned invalid JSON for {url}"
            ) from exc
        if not isinstance(payload, dict):
            raise EnrichmentProviderError(
                f"provider returned non-object JSON for {url}"
            )
        return payload

    # -- artist candidates -------------------------------------------------

    def find_artist_candidates(
        self, evidence: ArtistIdentityEvidence
    ) -> tuple[ArtistCandidate, ...]:
        escaped = escape_musicbrainz_lucene(evidence.local_artist_name)
        url = _musicbrainz_query_url(
            "artist/",
            {"query": f"artist:{escaped}", "fmt": "json", "limit": "25"},
            "musicbrainz_search",
        )
        payload = self._get_json(url, "musicbrainz_search")
        artists = _require_list(payload, "artists")
        candidates: list[ArtistCandidate] = []
        for raw in artists[:MAX_ARTIST_CANDIDATES]:
            if not isinstance(raw, dict):
                continue  # candidate-local malformed: skip only this one
            try:
                external_id = _require_str(raw, "id")
                name = _optional_str(raw, "name")
                disambiguation = _optional_str(raw, "disambiguation")
            except EnrichmentProviderError:
                continue  # candidate-local malformed: skip only this one
            # R1 FALSE-UNIQUENESS GATE: a support-evidence (album browse)
            # failure ABORTS the whole resolution — it must never make a
            # failed candidate disappear and fake uniqueness.
            known_albums = self._known_albums_for(external_id)
            candidates.append(
                ArtistCandidate(
                    external_artist_id=external_id,
                    canonical_name=name,
                    disambiguation=disambiguation,
                    known_albums=known_albums,
                )
            )
        # Deterministic: external ID ascending (provider order/score is
        # never identity authority).
        return tuple(sorted(candidates, key=lambda c: c.external_artist_id))

    def _known_albums_for(self, artist_id: str) -> tuple[LocalAlbumEvidence, ...]:
        """M6.9 REOPENED: release-group browse with the REAL contract.

        Endpoint: /ws/2/release-group/?artist=<MBID>&fmt=json&limit=100
        The ``type`` filter is NOT passed — ``release-group`` is the
        endpoint entity, not a valid value of the ``type`` parameter.
        Bounded pagination: up to MAX_RELEASE_GROUP_PAGES pages of
        RELEASE_GROUP_PAGE_SIZE, stopping early when a page comes back
        short (no further pages); results are deduplicated by title."""
        albums: list[LocalAlbumEvidence] = []
        seen_titles: set[str] = set()
        offset = 0
        for _page in range(MAX_RELEASE_GROUP_PAGES):
            url = _musicbrainz_query_url(
                "release-group/",
                {
                    "artist": artist_id,
                    "fmt": "json",
                    "limit": str(RELEASE_GROUP_PAGE_SIZE),
                    "offset": str(offset),
                },
                "musicbrainz_lookup",
            )
            payload = self._get_json(url, "musicbrainz_lookup")
            groups = _require_list(payload, "release-groups")
            for raw in groups:
                if not isinstance(raw, dict):
                    continue
                title = _optional_str(raw, "title")
                if not title:
                    continue
                normalized = title.casefold()
                if normalized in seen_titles:
                    continue
                seen_titles.add(normalized)
                albums.append(
                    LocalAlbumEvidence(title=title, year=_first_release_year(raw))
                )
                if len(albums) >= MAX_RELEASE_GROUPS_TOTAL:
                    return tuple(albums)
            if len(groups) < RELEASE_GROUP_PAGE_SIZE:
                break  # short page = last page
            offset += len(groups)
        return tuple(albums)

    # -- release-group candidates ------------------------------------------

    def find_release_group_candidates(
        self, evidence: AlbumIdentityEvidence
    ) -> tuple[ReleaseGroupCandidate, ...]:
        escaped_title = escape_musicbrainz_lucene(evidence.local_album_title)
        query = f"releasegroup:{escaped_title}"
        if evidence.local_album_artist_name:
            escaped_artist = escape_musicbrainz_lucene(evidence.local_album_artist_name)
            query += f" AND artist:{escaped_artist}"
        url = _musicbrainz_query_url(
            "release-group/",
            {"query": query, "fmt": "json", "limit": "25"},
            "musicbrainz_search",
        )
        payload = self._get_json(url, "musicbrainz_search")
        groups = _require_list(payload, "release-groups")
        candidates: list[ReleaseGroupCandidate] = []
        for raw in groups[:MAX_ARTIST_CANDIDATES]:
            if not isinstance(raw, dict):
                continue
            try:
                external_id = _require_str(raw, "id")
                title = _optional_str(raw, "title")
                credits = self._artist_credits(raw)
            except EnrichmentProviderError:
                continue
            candidates.append(
                ReleaseGroupCandidate(
                    release_group_id=external_id,
                    title=title,
                    artist_credit_external_ids=dedupe_identity_ids(credits[0]),
                    artist_credit_names=dedupe_identity_ids(credits[1]),
                    first_release_year=_first_release_year(raw),
                )
            )
        return tuple(sorted(candidates, key=lambda c: c.release_group_id))

    @staticmethod
    def _artist_credits(payload: dict) -> tuple[list[str], list[str]]:
        ids: list[str] = []
        names: list[str] = []
        for credit in payload.get("artist-credit", []) or []:
            if not isinstance(credit, dict):
                continue
            artist = credit.get("artist")
            name = credit.get("name")
            if isinstance(artist, dict) and isinstance(artist.get("id"), str):
                ids.append(artist["id"])
            if isinstance(name, str) and name:
                names.append(name)
        return ids, names

    # -- release edition candidates -----------------------------------------

    def find_release_edition_candidates(
        self, evidence: AlbumIdentityEvidence
    ) -> tuple[ReleaseEditionCandidate, ...]:
        hints = dedupe_identity_ids(evidence.identity_hints.release_ids)
        editions: list[ReleaseEditionCandidate] = []
        for release_id in hints[:_MAX_RELEASE_EDITION_LOOKUPS]:
            url = f"{API_ROOT}/release/{quote(release_id)}?inc=release-groups&fmt=json"
            payload = self._get_json(url, "musicbrainz_lookup")
            try:
                release_group = payload.get("release-group")
                if not isinstance(release_group, dict):
                    continue
                group_id = _require_str(release_group, "id")
            except EnrichmentProviderError:
                continue
            editions.append(
                ReleaseEditionCandidate(
                    release_id=release_id, release_group_id=group_id
                )
            )
        return tuple(sorted(editions, key=lambda e: e.release_id))
