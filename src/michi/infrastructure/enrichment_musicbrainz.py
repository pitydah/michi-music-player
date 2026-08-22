"""MusicBrainz identity resolver + knowledge adapter (M6.9C/M6.9E).

MusicBrainz is the IDENTITY MASTER. Strict untrusted-JSON validation:
wrong types are never coerced into domain candidates; malformed top-
level payloads raise EnrichmentProviderError; malformed single
candidates are skipped; candidate order is deterministic (external ID
ascending) — provider score never influences identity.

Policy: central rate limiter (<= 1 request/sec), bounded retries only
for 429/502/503/504 (max 3 attempts; Retry-After honored; else 1s/2s),
provider response cache with TTLs (search 7d / lookup 30d), max 5
artist candidates and 50 release groups inspected per candidate.
"""

import json
import time
from urllib.parse import quote

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
    EnrichmentHttpStatusError,
    MusicBrainzRateLimiter,
)
from michi.infrastructure.enrichment_provider_cache import (
    DEFAULT_TTLS_SECONDS,
)

API_ROOT = "https://musicbrainz.org/ws/2"
MAX_ARTIST_CANDIDATES = 5
MAX_RELEASE_GROUPS_PER_CANDIDATE = 50
_MAX_RELEASE_EDITION_LOOKUPS = 5
_RETRYABLE_STATUS = (429, 502, 503, 504)


def _require_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EnrichmentProviderError(
            f"provider payload field {key!r} missing or not a non-blank str"
        )
    return value


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
        self._transport = transport
        self._limiter = limiter
        self._cache = cache
        self._retry_sleeper = retry_sleeper

    # -- transport --------------------------------------------------------

    def _get_json(self, url: str, ttl_category: str) -> dict:
        if self._cache is not None:
            cached = self._cache.get(ttl_category, url)
            if cached is not None:
                return self._parse_json(cached.body, url)
        attempts = 0
        while True:
            self._limiter.wait()
            try:
                response = self._transport.get(HttpRequest(url=url))
                break
            except EnrichmentHttpStatusError as exc:
                if exc.status_code in _RETRYABLE_STATUS and attempts < 2:
                    attempts += 1
                    self._retry_sleeper(self._retry_delay(exc, attempts))
                    continue
                raise
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
    def _retry_delay(exc: EnrichmentHttpStatusError, attempt: int) -> float:
        raw = exc.headers.get("retry-after", "")
        try:
            value = float(raw)
            if 0 < value <= 10:
                return value
        except (TypeError, ValueError):
            pass
        return float(attempt)  # bounded backoff: 1s, 2s

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
        url = (
            f"{API_ROOT}/artist/?query="
            f"{quote(f'artist:{evidence.local_artist_name}')}"
            "&fmt=json&limit=25"
        )
        payload = self._get_json(url, "musicbrainz_search")
        artists = _require_list(payload, "artists")
        candidates: list[ArtistCandidate] = []
        for raw in artists[:MAX_ARTIST_CANDIDATES]:
            if not isinstance(raw, dict):
                continue  # malformed single candidate: skip
            try:
                external_id = _require_str(raw, "id")
                name = _optional_str(raw, "name")
                disambiguation = _optional_str(raw, "disambiguation")
                known_albums = self._known_albums_for(external_id)
            except EnrichmentProviderError:
                continue
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
        url = (
            f"{API_ROOT}/release-group/?artist={quote(artist_id)}"
            "&type=release-group&fmt=json&limit="
            f"{MAX_RELEASE_GROUPS_PER_CANDIDATE}"
        )
        payload = self._get_json(url, "musicbrainz_lookup")
        groups = _require_list(payload, "release-groups")
        albums: list[LocalAlbumEvidence] = []
        for raw in groups:
            if not isinstance(raw, dict):
                continue
            title = _optional_str(raw, "title")
            if not title:
                continue
            albums.append(
                LocalAlbumEvidence(title=title, year=_first_release_year(raw))
            )
        return tuple(albums)

    # -- release-group candidates ------------------------------------------

    def find_release_group_candidates(
        self, evidence: AlbumIdentityEvidence
    ) -> tuple[ReleaseGroupCandidate, ...]:
        query = f"releasegroup:{evidence.local_album_title}"
        if evidence.local_album_artist_name:
            query += f" AND artist:{evidence.local_album_artist_name}"
        url = f"{API_ROOT}/release-group/?query={quote(query)}&fmt=json&limit=25"
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
