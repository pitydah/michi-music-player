"""Structured knowledge providers (M6.9E + M6.9-BACKEND-R1).

Field ownership (M6.9 contract):
- IDENTITY: MusicBrainz (resolver);
- STRUCTURED FACTS: MusicBrainz, then Wikidata for explicitly modeled
  facts (only through a VERIFIED QID — never name search);
- BIOGRAPHY: Wikipedia (only through a verified sitelink/relation);
- ARTIST IMAGE: Wikimedia Commons (verified file claim);
- ALBUM EXTERNAL COVER: Cover Art Archive (fallback authority).

R1 additions:
- ONE shared bounded retry policy (ProviderRequestExecutor);
- STALE cache is KNOWLEDGE-only and truthfully marked
  (KnowledgeProvenance.is_stale / retrieved_at) — identity resolution
  never touches stale entries;
- optional sources treat 404 as EMPTY optional results (never FAILED);
- Wikidata claim selection is deterministic and fail-closed
  (preferred rank → distinct values; contradictions stay unresolved;
  deprecated ignored; provider order irrelevant); country is a QID
  (country_qid), never disguised as a label; verified sitelinks provide
  a Wikipedia fallback (requested language → enwiki);
- every provider payload carries truthful retrieved_at (UTC ISO-8601,
  injectable clock).
"""

import json
from datetime import UTC, datetime
from urllib.parse import quote, unquote, urlsplit

from michi.application.enrichment_ports import (
    ArtistExternalLinks,
    BiographyKnowledge,
    CommonsImageKnowledge,
    CoverArtArchiveProviderPort,
    CoverArtKnowledge,
    EnrichmentHttpStatusError,
    EnrichmentProviderError,
    EnrichmentTransportError,
    HttpRequest,
    HttpTransportPort,
    MusicBrainzKnowledgeProviderPort,
    ProviderCachePort,
    WikidataArtistClaims,
    WikidataKnowledgeProviderPort,
    WikimediaCommonsProviderPort,
    WikipediaBiographyProviderPort,
)
from michi.domain.enrichment import (
    AlbumKnowledgeProfile,
    ArtistKnowledgeProfile,
    KnowledgeProvenance,
    dedupe_identity_ids,
)
from michi.infrastructure.enrichment_http import (
    MusicBrainzRateLimiter,
    ProviderRequestExecutor,
)
from michi.infrastructure.enrichment_musicbrainz import (
    API_ROOT,
    _first_release_year,
    _optional_str,
    _require_list,
)
from michi.infrastructure.enrichment_provider_cache import (
    DEFAULT_TTLS_SECONDS,
)

MAX_BIOGRAPHY_CHARS = 4000


def _utc_now_iso() -> str:
    """R1: UTC ISO-8601 retrieval timestamp (injectable per provider)."""
    return datetime.now(UTC).isoformat(timespec="seconds")


class _CachedGetter:
    """Shared cached-GET helper for knowledge providers (R1).

    Fresh cache first; on a transient network failure KNOWLEDGE may fall
    back to a stale entry, truthfully flagged (is_stale=True) with the
    original retrieval time. Identity resolution never uses this helper
    with allow_stale.
    """

    def __init__(
        self,
        transport: HttpTransportPort,
        cache: ProviderCachePort | None,
        limiter: MusicBrainzRateLimiter | None = None,
        sleeper=None,
        clock=_utc_now_iso,
    ) -> None:
        import time as _time

        self._executor = ProviderRequestExecutor(
            transport, limiter, sleeper=sleeper or _time.sleep
        )
        self._cache = cache
        self._clock = clock

    def get_json(
        self, url: str, ttl_category: str, allow_stale: bool = False
    ) -> tuple[dict, bool, str]:
        """Returns (payload, is_stale, retrieved_at_iso)."""
        if self._cache is not None:
            cached = self._cache.get(ttl_category, url)
            if cached is not None:
                return (
                    self._parse(cached.body, url),
                    False,
                    self._iso(cached.retrieved_at),
                )
        try:
            response = self._executor.get(HttpRequest(url=url))
        except (EnrichmentTransportError, EnrichmentHttpStatusError) as exc:
            if (
                allow_stale
                and self._cache is not None
                and isinstance(
                    exc, (EnrichmentTransportError, EnrichmentHttpStatusError)
                )
                and not (
                    isinstance(exc, EnrichmentHttpStatusError)
                    and exc.status_code in (400, 401, 403, 404)
                )
            ):
                stale = self._cache.get_stale(ttl_category, url)
                if stale is not None:
                    return (
                        self._parse(stale.body, url),
                        True,
                        self._iso(stale.retrieved_at),
                    )
            raise
        payload = self._parse(response.body, url)
        if self._cache is not None:
            self._cache.put(
                ttl_category,
                url,
                response,
                ttl_seconds=DEFAULT_TTLS_SECONDS.get(
                    ttl_category, DEFAULT_TTLS_SECONDS["musicbrainz_lookup"]
                ),
                etag=response.headers.get("etag", ""),
                last_modified=response.headers.get("last-modified", ""),
            )
        return payload, False, self._clock()

    @staticmethod
    def _iso(epoch: float) -> str:
        return datetime.fromtimestamp(epoch, UTC).isoformat(timespec="seconds")

    @staticmethod
    def _parse(body: bytes, url: str) -> dict:
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


class MusicBrainzKnowledgeProvider(MusicBrainzKnowledgeProviderPort):
    """Structured facts + verified URL relations for resolved MBIDs."""

    def __init__(
        self,
        transport: HttpTransportPort,
        limiter: MusicBrainzRateLimiter,
        cache: ProviderCachePort | None = None,
        sleeper=None,
        clock=_utc_now_iso,
    ) -> None:
        self._getter = _CachedGetter(
            transport, cache, limiter=limiter, sleeper=sleeper, clock=clock
        )

    def fetch_artist(
        self, local_artist_key: str, external_artist_id: str
    ) -> ArtistKnowledgeProfile:
        url = f"{API_ROOT}/artist/{quote(external_artist_id)}?inc=genres+tags&fmt=json"
        payload, is_stale, retrieved_at = self._getter.get_json(
            url, "musicbrainz_lookup", allow_stale=True
        )
        genres = []
        for entry in _require_list(payload, "genres") or []:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                genres.append(entry["name"])
        begin = 0
        end = 0
        if isinstance(payload.get("life-span"), dict):
            lifespan = payload["life-span"]
            begin = _year(_optional_str(lifespan, "begin"))
            end = _year(_optional_str(lifespan, "end"))
        return ArtistKnowledgeProfile(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            external_genres=tuple(sorted(set(genres), key=str.casefold)),
            begin_year=begin,
            end_year=end,
            sort_name=_optional_str(payload, "sort-name"),
            artist_type=_optional_str(payload, "type"),
            area=(
                payload["area"]["name"]
                if isinstance(payload.get("area"), dict)
                and isinstance(payload["area"].get("name"), str)
                else ""
            ),
            provenance=KnowledgeProvenance(
                provider="musicbrainz",
                external_entity_id=external_artist_id,
                retrieved_at=retrieved_at,
                is_stale=is_stale,
            ),
        )

    def artist_links(self, external_artist_id: str) -> ArtistExternalLinks:
        url = f"{API_ROOT}/artist/{quote(external_artist_id)}?inc=url-rels&fmt=json"
        payload, _, _ = self._getter.get_json(
            url, "musicbrainz_lookup", allow_stale=True
        )
        wikidata_qid = ""
        wikipedia_title = ""
        wikipedia_language = ""
        for relation in payload.get("relations", []) or []:
            if not isinstance(relation, dict):
                continue
            target = relation.get("url")
            rel_type = relation.get("type")
            if not isinstance(target, dict) or not isinstance(
                target.get("resource"), str
            ):
                continue
            resource = target["resource"]
            if isinstance(rel_type, str) and rel_type == "wikidata":
                qid = resource.rstrip("/").rsplit("/", 1)[-1]
                if qid.startswith("Q") and qid[1:].isdigit():
                    wikidata_qid = qid
            elif isinstance(rel_type, str) and rel_type == "wikipedia":
                wikipedia_title, wikipedia_language = _parse_wikipedia_resource(
                    resource
                )
        return ArtistExternalLinks(
            wikidata_qid=wikidata_qid,
            wikipedia_title=wikipedia_title,
            wikipedia_language=wikipedia_language,
        )

    def fetch_release_group(
        self, local_album_key: str, release_group_id: str, release_id: str = ""
    ) -> AlbumKnowledgeProfile:
        url = f"{API_ROOT}/release-group/{quote(release_group_id)}?inc=genres&fmt=json"
        payload, is_stale, retrieved_at = self._getter.get_json(
            url, "musicbrainz_lookup", allow_stale=True
        )
        genres = []
        for entry in payload.get("genres", []) or []:
            if isinstance(entry, dict) and isinstance(entry.get("name"), str):
                genres.append(entry["name"])
        return AlbumKnowledgeProfile(
            local_album_key=local_album_key,
            release_group_id=release_group_id,
            release_id=release_id,
            external_genres=tuple(sorted(set(genres), key=str.casefold)),
            first_release_year=_first_release_year(payload),
            provenance=KnowledgeProvenance(
                provider="musicbrainz",
                external_entity_id=release_group_id,
                retrieved_at=retrieved_at,
                is_stale=is_stale,
            ),
        )


def _year(raw: str) -> int:
    digits = "".join(ch for ch in raw[:4] if ch.isdigit())
    return int(digits) if len(digits) == 4 else 0


def _parse_wikipedia_resource(resource: str) -> tuple[str, str]:
    """https://<lang>.wikipedia.org/wiki/<Title> -> (title, lang)."""
    parts = urlsplit(resource)
    host = parts.hostname or ""
    if not host.endswith(".wikipedia.org") or not parts.path.startswith("/wiki/"):
        return "", ""
    language = host.split(".")[0]
    title = unquote(parts.path[len("/wiki/") :]).replace("_", " ")
    return title, language


def _select_claim_value(claims: dict, properties: tuple[str, ...]) -> str:
    """R1 deterministic, fail-closed claim selection.

    For each RANK level (preferred first, then normal):
    - deprecated claims are discarded;
    - values are extracted and deduplicated;
    - EXACTLY ONE distinct value → use it;
    - MORE than one distinct value → unresolved (""), never first-wins;
    - no value at this rank → try the next rank level.
    Provider order is irrelevant by construction.
    """
    for rank in ("preferred", "normal"):
        values: list[str] = []
        for prop in properties:
            for claim in claims.get(prop, []) or []:
                if not isinstance(claim, dict):
                    continue
                if claim.get("rank") == "deprecated":
                    continue
                if claim.get("rank") != rank:
                    continue
                mainsnak = claim.get("mainsnak")
                if not isinstance(mainsnak, dict):
                    continue
                datavalue = mainsnak.get("datavalue")
                if not isinstance(datavalue, dict):
                    continue
                value = datavalue.get("value")
                if isinstance(value, str) and value:
                    values.append(value)
                elif isinstance(value, dict) and isinstance(value.get("id"), str):
                    values.append(value["id"])
                elif isinstance(value, dict) and isinstance(value.get("time"), str):
                    values.append(value["time"])
        distinct = dedupe_identity_ids(values)
        if len(distinct) == 1:
            return distinct[0]
        if len(distinct) > 1:
            return ""  # contradictory: unresolved, never first-wins
    return ""


class WikidataKnowledgeProvider(WikidataKnowledgeProviderPort):
    """wbgetentities for a verified QID only (claims + sitelinks)."""

    def __init__(
        self,
        transport: HttpTransportPort,
        cache: ProviderCachePort | None = None,
        sleeper=None,
        clock=_utc_now_iso,
    ) -> None:
        self._getter = _CachedGetter(transport, cache, sleeper=sleeper, clock=clock)

    def fetch_artist_claims(
        self, qid: str, preferred_language: str = "en"
    ) -> WikidataArtistClaims:
        if not (qid.startswith("Q") and qid[1:].isdigit()):
            raise EnrichmentProviderError(f"invalid Wikidata QID: {qid!r}")
        url = (
            "https://www.wikidata.org/w/api.php?action=wbgetentities"
            f"&ids={quote(qid)}&format=json&formatversion=2"
            "&props=claims|sitelinks"
        )
        payload, is_stale, retrieved_at = self._getter.get_json(
            url, "wikidata", allow_stale=True
        )
        entities = payload.get("entities")
        if not isinstance(entities, dict):
            raise EnrichmentProviderError("wikidata entities missing")
        entity = entities.get(qid)
        if not isinstance(entity, dict):
            raise EnrichmentProviderError("wikidata entity missing")
        claims = entity.get("claims")
        if not isinstance(claims, dict):
            claims = {}
        wikipedia_title, wikipedia_language = _sitelink(
            entity.get("sitelinks"), preferred_language
        )
        begin_raw = _select_claim_value(claims, ("P571", "P569"))
        end_raw = _select_claim_value(claims, ("P576", "P570"))
        return WikidataArtistClaims(
            country_qid=_select_claim_value(claims, ("P27", "P495")),
            country_label="",  # R1: labels are NEVER invented here
            official_website=_select_claim_value(claims, ("P856",)),
            commons_image_title=_file_title(_select_claim_value(claims, ("P18",))),
            wikipedia_title=wikipedia_title,
            wikipedia_language=wikipedia_language,
            begin_year=_year_from_claim(begin_raw),
            end_year=_year_from_claim(end_raw),
            retrieved_at=retrieved_at,
            is_stale=is_stale,
        )


def _sitelink(sitelinks, preferred_language: str) -> tuple[str, str]:
    """R1 verified sitelink fallback: requested language → enwiki."""
    if not isinstance(sitelinks, dict):
        return "", ""
    for lang in (preferred_language, "en"):
        entry = sitelinks.get(f"{lang}wiki")
        if isinstance(entry, dict) and isinstance(entry.get("title"), str):
            return entry["title"], lang
    return "", ""


def _file_title(raw: str) -> str:
    if raw.startswith("File:"):
        return raw[len("File:") :]
    return raw


def _year_from_claim(raw: str) -> int:
    if not raw:
        return 0
    digits = "".join(ch for ch in raw if ch.isdigit())[:4]
    return int(digits) if len(digits) == 4 else 0


class WikipediaBiographyProvider(WikipediaBiographyProviderPort):
    """REST summary extract for a VERIFIED page title (bounded text).

    R1: a 404 is an EMPTY OPTIONAL result (no biography), never FAILED.
    """

    def __init__(
        self,
        transport: HttpTransportPort,
        cache: ProviderCachePort | None = None,
        sleeper=None,
        clock=_utc_now_iso,
    ) -> None:
        self._getter = _CachedGetter(transport, cache, sleeper=sleeper, clock=clock)

    def fetch_biography(self, title: str, language: str = "") -> BiographyKnowledge:
        lang = language or "en"
        url = (
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
            f"{quote(title.replace(' ', '_'))}"
        )
        try:
            payload, is_stale, retrieved_at = self._getter.get_json(
                url, "wikipedia", allow_stale=True
            )
        except EnrichmentHttpStatusError as exc:
            if exc.status_code == 404:
                # R1 (P2-02): no page → empty OPTIONAL biography.
                return BiographyKnowledge()
            raise
        extract = payload.get("extract")
        if not isinstance(extract, str):
            return BiographyKnowledge()
        text = " ".join(extract.split())
        if len(text) > MAX_BIOGRAPHY_CHARS:
            text = text[:MAX_BIOGRAPHY_CHARS]
        page_title = payload.get("title")
        if not isinstance(page_title, str):
            page_title = title
        content_url = payload.get("content_urls")
        desktop = ""
        if isinstance(content_url, dict) and isinstance(
            content_url.get("desktop"), dict
        ):
            page_url = content_url["desktop"].get("page")
            if isinstance(page_url, str):
                desktop = page_url
        return BiographyKnowledge(
            text=text,
            page_title=page_title,
            source_url=desktop,
            language=lang,
            retrieved_at=retrieved_at,
            is_stale=is_stale,
        )


class WikimediaCommonsProvider(WikimediaCommonsProviderPort):
    """imageinfo + extmetadata for a verified Commons file title."""

    def __init__(
        self,
        transport: HttpTransportPort,
        cache: ProviderCachePort | None = None,
        sleeper=None,
        clock=_utc_now_iso,
    ) -> None:
        self._getter = _CachedGetter(transport, cache, sleeper=sleeper, clock=clock)

    def fetch_image(self, file_title: str) -> CommonsImageKnowledge:
        url = (
            "https://commons.wikimedia.org/w/api.php?action=query"
            f"&titles={quote(f'File:{file_title}')}"
            "&prop=imageinfo&iiprop=url|extmetadata&format=json"
        )
        try:
            payload, is_stale, retrieved_at = self._getter.get_json(
                url, "commons", allow_stale=True
            )
        except EnrichmentHttpStatusError as exc:
            if exc.status_code == 404:
                return CommonsImageKnowledge()
            raise
        pages = payload.get("query", {}).get("pages")
        if not isinstance(pages, dict):
            return CommonsImageKnowledge()
        for page in pages.values():
            if not isinstance(page, dict):
                continue
            if page.get("missing"):
                continue
            info_list = page.get("imageinfo")
            if not isinstance(info_list, list) or not info_list:
                continue
            info = info_list[0]
            if not isinstance(info, dict):
                continue
            source_url = info.get("url")
            if not isinstance(source_url, str) or not source_url:
                continue
            metadata = info.get("extmetadata") or {}
            return CommonsImageKnowledge(
                source_url=source_url,
                license=_meta_str(metadata, "LicenseShortName"),
                license_url=_meta_str(metadata, "LicenseUrl"),
                artist=_meta_str(metadata, "Artist"),
                attribution=_meta_str(metadata, "Credit"),
                retrieved_at=retrieved_at,
                is_stale=is_stale,
            )
        return CommonsImageKnowledge()


def _meta_str(metadata, key: str) -> str:
    entry = metadata.get(key)
    if isinstance(entry, dict) and isinstance(entry.get("value"), str):
        return entry["value"].strip()
    return ""


class CoverArtArchiveProvider(CoverArtArchiveProviderPort):
    """CAA JSON lookup for a resolved Release or Release Group.

    R1: 404 → empty optional cover (never FAILED)."""

    def __init__(
        self,
        transport: HttpTransportPort,
        cache: ProviderCachePort | None = None,
        sleeper=None,
        clock=_utc_now_iso,
    ) -> None:
        self._getter = _CachedGetter(transport, cache, sleeper=sleeper, clock=clock)

    def fetch_cover(
        self, release_id: str = "", release_group_id: str = ""
    ) -> CoverArtKnowledge:
        if release_id:
            url = f"https://coverartarchive.org/release/{quote(release_id)}"
            entity_kind = "release"
        elif release_group_id:
            url = f"https://coverartarchive.org/release-group/{quote(release_group_id)}"
            entity_kind = "release-group"
        else:
            raise EnrichmentProviderError("CAA cover requires an entity id")
        try:
            payload, _, _ = self._getter.get_json(url, "coverart", allow_stale=True)
        except EnrichmentHttpStatusError as exc:
            if exc.status_code == 404:
                return CoverArtKnowledge(entity_kind=entity_kind)
            raise
        images = payload.get("images")
        if not isinstance(images, list) or not images:
            return CoverArtKnowledge(entity_kind=entity_kind)
        for image in images:
            if not isinstance(image, dict):
                continue
            if image.get("front") is not True:
                continue
            image_url = image.get("image")
            if isinstance(image_url, str) and image_url.startswith(
                "https://coverartarchive.org/"
            ):
                return CoverArtKnowledge(image_url=image_url, entity_kind=entity_kind)
        return CoverArtKnowledge(entity_kind=entity_kind)
