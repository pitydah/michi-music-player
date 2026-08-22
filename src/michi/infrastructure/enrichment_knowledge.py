"""Structured knowledge providers (M6.9E) — MusicBrainz, Wikidata,
Wikipedia, Wikimedia Commons, Cover Art Archive.

Field ownership (M6.9 contract):
- IDENTITY: MusicBrainz (resolver);
- STRUCTURED FACTS: MusicBrainz, then Wikidata for explicitly modeled
  facts (only through a VERIFIED QID — never name search);
- BIOGRAPHY: Wikipedia (only through a verified sitelink/relation);
- ARTIST IMAGE: Wikimedia Commons (verified file claim);
- ALBUM EXTERNAL COVER: Cover Art Archive (fallback authority).

Every provider validates untrusted JSON strictly, never coerces types,
and returns typed knowledge DTOs with truthful provenance — unknown
license/attribution stays UNKNOWN, never fabricated.
"""

import json
from urllib.parse import quote

from michi.application.enrichment_ports import (
    ArtistExternalLinks,
    BiographyKnowledge,
    CommonsImageKnowledge,
    CoverArtArchiveProviderPort,
    CoverArtKnowledge,
    EnrichmentProviderError,
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
)
from michi.infrastructure.enrichment_http import MusicBrainzRateLimiter
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


def _strict_str(value, field: str) -> str:
    if not isinstance(value, str):
        raise EnrichmentProviderError(f"provider field {field!r} is not a str")
    return value


class _CachedGetter:
    """Shared cached-GET helper for knowledge providers (fresh cache
    only — knowledge is cache-like; identity decisions never use it)."""

    def __init__(
        self, transport: HttpTransportPort, cache: ProviderCachePort | None
    ) -> None:
        self._transport = transport
        self._cache = cache

    def get_json(self, url: str, ttl_category: str) -> dict:
        if self._cache is not None:
            cached = self._cache.get(ttl_category, url)
            if cached is not None:
                return self._parse(cached.body, url)
        response = self._transport.get(HttpRequest(url=url))
        payload = self._parse(response.body, url)
        if self._cache is not None:
            self._cache.put(
                ttl_category,
                url,
                response,
                ttl_seconds=DEFAULT_TTLS_SECONDS.get(
                    ttl_category, DEFAULT_TTLS_SECONDS["musicbrainz_lookup"]
                ),
            )
        return payload

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
    ) -> None:
        self._getter = _CachedGetter(transport, cache)
        self._limiter = limiter

    def _get_json(self, url: str, ttl_category: str) -> dict:
        self._limiter.wait()
        return self._getter.get_json(url, ttl_category)

    def fetch_artist(
        self, local_artist_key: str, external_artist_id: str
    ) -> ArtistKnowledgeProfile:
        url = f"{API_ROOT}/artist/{quote(external_artist_id)}?inc=genres+tags&fmt=json"
        payload = self._get_json(url, "musicbrainz_lookup")
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
                provider="musicbrainz", external_entity_id=external_artist_id
            ),
        )

    def artist_links(self, external_artist_id: str) -> ArtistExternalLinks:
        url = f"{API_ROOT}/artist/{quote(external_artist_id)}?inc=url-rels&fmt=json"
        payload = self._get_json(url, "musicbrainz_lookup")
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
        payload = self._get_json(url, "musicbrainz_lookup")
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
                provider="musicbrainz", external_entity_id=release_group_id
            ),
        )


def _year(raw: str) -> int:
    digits = "".join(ch for ch in raw[:4] if ch.isdigit())
    return int(digits) if len(digits) == 4 else 0


def _parse_wikipedia_resource(resource: str) -> tuple[str, str]:
    """https://<lang>.wikipedia.org/wiki/<Title> -> (title, lang)."""
    from urllib.parse import unquote, urlsplit

    parts = urlsplit(resource)
    host = parts.hostname or ""
    if not host.endswith(".wikipedia.org") or not parts.path.startswith("/wiki/"):
        return "", ""
    language = host.split(".")[0]
    title = unquote(parts.path[len("/wiki/") :]).replace("_", " ")
    return title, language


class WikidataKnowledgeProvider(WikidataKnowledgeProviderPort):
    """wbgetentities for a verified QID only."""

    def __init__(
        self, transport: HttpTransportPort, cache: ProviderCachePort | None = None
    ) -> None:
        self._getter = _CachedGetter(transport, cache)

    def fetch_artist_claims(self, qid: str) -> WikidataArtistClaims:
        if not (qid.startswith("Q") and qid[1:].isdigit()):
            raise EnrichmentProviderError(f"invalid Wikidata QID: {qid!r}")
        url = (
            "https://www.wikidata.org/w/api.php?action=wbgetentities"
            f"&ids={quote(qid)}&format=json&formatversion=2&props=claims"
        )
        payload = self._getter.get_json(url, "wikidata")
        entities = payload.get("entities")
        if not isinstance(entities, dict):
            raise EnrichmentProviderError("wikidata entities missing")
        entity = entities.get(qid)
        if not isinstance(entity, dict):
            raise EnrichmentProviderError("wikidata entity missing")
        claims = entity.get("claims")
        if not isinstance(claims, dict):
            return WikidataArtistClaims()
        return WikidataArtistClaims(
            country=_preferred_claim_str(claims, ("P27", "P495")),
            official_website=_preferred_claim_str(claims, ("P856",)),
            commons_image_title=_preferred_claim_file(claims, ("P18",)),
            begin_year=_preferred_claim_year(claims, ("P571", "P569")),
            end_year=_preferred_claim_year(claims, ("P576", "P570")),
        )


def _preferred_claim_str(claims: dict, properties: tuple[str, ...]) -> str:
    """Deterministic preferred/normal-rank selection; no guessing."""
    for prop in properties:
        for claim in claims.get(prop, []) or []:
            if not isinstance(claim, dict):
                continue
            if claim.get("rank") == "deprecated":
                continue
            mainsnak = claim.get("mainsnak")
            if not isinstance(mainsnak, dict):
                continue
            datavalue = mainsnak.get("datavalue")
            if not isinstance(datavalue, dict):
                continue
            value = datavalue.get("value")
            if isinstance(value, str) and value:
                return value
            if isinstance(value, dict) and isinstance(value.get("id"), str):
                return value["id"]
            if isinstance(value, dict) and isinstance(value.get("time"), str):
                return value["time"]
    return ""


def _preferred_claim_file(claims: dict, properties: tuple[str, ...]) -> str:
    for prop in properties:
        for claim in claims.get(prop, []) or []:
            if not isinstance(claim, dict):
                continue
            if claim.get("rank") == "deprecated":
                continue
            mainsnak = claim.get("mainsnak")
            if not isinstance(mainsnak, dict):
                continue
            datavalue = mainsnak.get("datavalue")
            if not isinstance(datavalue, dict):
                continue
            value = datavalue.get("value")
            if isinstance(value, str) and value.startswith("File:"):
                return value[len("File:") :]
    return ""


def _preferred_claim_year(claims: dict, properties: tuple[str, ...]) -> int:
    raw = _preferred_claim_str(claims, properties)
    if not raw:
        return 0
    digits = "".join(ch for ch in raw if ch.isdigit())[:4]
    return int(digits) if len(digits) == 4 else 0


class WikipediaBiographyProvider(WikipediaBiographyProviderPort):
    """REST summary extract for a VERIFIED page title (bounded text)."""

    def __init__(
        self, transport: HttpTransportPort, cache: ProviderCachePort | None = None
    ) -> None:
        self._getter = _CachedGetter(transport, cache)

    def fetch_biography(self, title: str, language: str = "") -> BiographyKnowledge:
        lang = language or "en"
        url = (
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
            f"{quote(title.replace(' ', '_'))}"
        )
        payload = self._getter.get_json(url, "wikipedia")
        extract = payload.get("extract")
        if not isinstance(extract, str):
            raise EnrichmentProviderError("wikipedia extract missing")
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
        )


class WikimediaCommonsProvider(WikimediaCommonsProviderPort):
    """imageinfo + extmetadata for a verified Commons file title."""

    def __init__(
        self, transport: HttpTransportPort, cache: ProviderCachePort | None = None
    ) -> None:
        self._getter = _CachedGetter(transport, cache)

    def fetch_image(self, file_title: str) -> CommonsImageKnowledge:
        url = (
            "https://commons.wikimedia.org/w/api.php?action=query"
            f"&titles={quote(f'File:{file_title}')}"
            "&prop=imageinfo&iiprop=url|extmetadata&format=json"
        )
        payload = self._getter.get_json(url, "commons")
        pages = payload.get("query", {}).get("pages")
        if not isinstance(pages, dict):
            raise EnrichmentProviderError("commons pages missing")
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
                raise EnrichmentProviderError("commons image url missing")
            metadata = info.get("extmetadata") or {}
            return CommonsImageKnowledge(
                source_url=source_url,
                license=_meta_str(metadata, "LicenseShortName"),
                license_url=_meta_str(metadata, "LicenseUrl"),
                artist=_meta_str(metadata, "Artist"),
                attribution=_meta_str(metadata, "Credit"),
            )
        raise EnrichmentProviderError("commons image not found")


def _meta_str(metadata, key: str) -> str:
    entry = metadata.get(key)
    if isinstance(entry, dict) and isinstance(entry.get("value"), str):
        value = entry["value"].strip()
        return value
    return ""


class CoverArtArchiveProvider(CoverArtArchiveProviderPort):
    """CAA JSON lookup for a resolved Release or Release Group."""

    def __init__(
        self, transport: HttpTransportPort, cache: ProviderCachePort | None = None
    ) -> None:
        self._getter = _CachedGetter(transport, cache)

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
        payload = self._getter.get_json(url, "coverart")
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
