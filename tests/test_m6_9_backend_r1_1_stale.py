"""M6.9-BACKEND-R1.1 — stale knowledge end-to-end truth.

- stale + transient (timeout/503) -> stale used, final PARTIAL
- stale + 404 / malformed JSON -> stale NOT used
- stale Commons / CAA / MB links -> PARTIAL final state
- identity resolution never uses stale cache
"""

import json

import pytest

from michi.application.enrichment_ports import (
    EnrichmentHttpStatusError,
    EnrichmentProviderError,
    EnrichmentTransportError,
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
)
from michi.infrastructure.enrichment_http import MusicBrainzRateLimiter
from michi.infrastructure.enrichment_knowledge import (
    CoverArtArchiveProvider,
    MusicBrainzKnowledgeProvider,
    WikimediaCommonsProvider,
    WikipediaBiographyProvider,
)
from michi.infrastructure.enrichment_provider_cache import (
    FilesystemProviderCache,
)


class FakeTransport(HttpTransportPort):
    def __init__(self, script):
        self._script = list(script)

    def get(self, request: HttpRequest) -> HttpResponse:
        item = self._script.pop(0) if self._script else None
        if item is None:
            raise AssertionError("unscripted")
        if isinstance(item, Exception):
            raise item
        return item


class InstantLimiter(MusicBrainzRateLimiter):
    def __init__(self):
        super().__init__(clock=lambda: 0.0, sleeper=lambda s: None)


def _cache_with(tmp_path, category, url, payload, ttl=60, now=1000.0):
    cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: now)
    cache.put(
        category,
        url,
        HttpResponse(200, {}, json.dumps(payload).encode(), url),
        ttl_seconds=ttl,
    )
    return cache


class TestStaleEligibility:
    def test_stale_after_timeout_used_partial_flagged(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/Artist"
        cache.put(
            "wikipedia",
            url,
            HttpResponse(
                200, {}, json.dumps({"title": "Artist", "extract": "bio"}).encode(), url
            ),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        transport = FakeTransport([EnrichmentTransportError("t")] * 3)
        bio = WikipediaBiographyProvider(
            transport, cache=cache, sleeper=lambda s: None
        ).fetch_biography("Artist")
        assert bio.text == "bio"
        assert bio.is_stale is True

    def test_stale_after_503_used(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        url = (
            "https://www.wikidata.org/w/api.php?action=wbgetentities"
            "&ids=Q1&format=json&formatversion=2&props=claims|sitelinks"
        )
        cache.put(
            "wikidata",
            url,
            HttpResponse(
                200,
                {},
                json.dumps({"entities": {"Q1": {"claims": {}}}}).encode(),
                url,
            ),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        transport = FakeTransport([EnrichmentHttpStatusError(503, {}, "down")] * 3)
        from michi.infrastructure.enrichment_knowledge import WikidataKnowledgeProvider

        claims = WikidataKnowledgeProvider(
            transport, cache=cache, sleeper=lambda s: None
        ).fetch_artist_claims("Q1")
        assert claims.is_stale is True

    def test_stale_after_404_not_used(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/Artist"
        cache.put(
            "wikipedia",
            url,
            HttpResponse(200, {}, json.dumps({"extract": "bio"}).encode(), url),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        transport = FakeTransport([EnrichmentHttpStatusError(404, {}, "no")])
        bio = WikipediaBiographyProvider(
            transport, cache=cache, sleeper=lambda s: None
        ).fetch_biography("Artist")
        # 404 is NOT transient: stale NOT used; empty optional result.
        assert bio.text == ""
        assert bio.is_stale is False

    def test_stale_after_malformed_json_not_used(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/Artist"
        cache.put(
            "wikipedia",
            url,
            HttpResponse(200, {}, b"{broken", url),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        transport = FakeTransport([EnrichmentTransportError("t")] * 3)
        with pytest.raises(EnrichmentProviderError):
            WikipediaBiographyProvider(
                transport, cache=cache, sleeper=lambda s: None
            ).fetch_biography("Artist")


class TestFreshnessPropagation:
    def test_stale_mb_links_flagged(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        url = "https://musicbrainz.org/ws/2/artist/mb-a?inc=url-rels&fmt=json"
        cache.put(
            "musicbrainz_lookup",
            url,
            HttpResponse(200, {}, json.dumps({"relations": []}).encode(), url),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        transport = FakeTransport([EnrichmentTransportError("t")] * 3)
        links = MusicBrainzKnowledgeProvider(
            transport, InstantLimiter(), cache=cache, sleeper=lambda s: None
        ).artist_links("mb-a")
        assert links.is_stale is True
        assert links.retrieved_at

    def test_stale_commons_flagged(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        url = (
            "https://commons.wikimedia.org/w/api.php?action=query"
            "&titles=File%3AX.jpg&prop=imageinfo&iiprop=url|extmetadata&format=json"
        )
        cache.put(
            "commons",
            url,
            HttpResponse(
                200,
                {},
                json.dumps(
                    {
                        "query": {
                            "pages": {
                                "-1": {
                                    "imageinfo": [
                                        {"url": "https://upload.wikimedia.org/x.jpg"}
                                    ]
                                }
                            }
                        }
                    }
                ).encode(),
                url,
            ),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        transport = FakeTransport([EnrichmentTransportError("t")] * 3)
        image = WikimediaCommonsProvider(
            transport, cache=cache, sleeper=lambda s: None
        ).fetch_image("X.jpg")
        assert image.is_stale is True
        assert image.source_url == "https://upload.wikimedia.org/x.jpg"

    def test_stale_caa_flagged(self, tmp_path):
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        url = "https://coverartarchive.org/release/rel-x"
        cache.put(
            "coverart",
            url,
            HttpResponse(
                200,
                {},
                json.dumps(
                    {
                        "images": [
                            {
                                "front": True,
                                "image": "https://coverartarchive.org/x.jpg",
                            }
                        ]
                    }
                ).encode(),
                url,
            ),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        transport = FakeTransport([EnrichmentTransportError("t")] * 3)
        cover = CoverArtArchiveProvider(
            transport, cache=cache, sleeper=lambda s: None
        ).fetch_cover(release_id="rel-x")
        assert cover.is_stale is True
        assert cover.image_url == "https://coverartarchive.org/x.jpg"


class TestIdentityNeverStale:
    def test_identity_resolution_fresh_only(self, tmp_path):
        """An EXPIRED identity candidate entry must never remap identity —
        even offline the resolution FAILS instead of using stale data."""
        state = {"now": 1000.0}
        cache = FilesystemProviderCache(tmp_path / "cache", clock=lambda: state["now"])
        url = "https://musicbrainz.org/ws/2/artist/?query=artist%3An&fmt=json&limit=25"
        cache.put(
            "musicbrainz_search",
            url,
            HttpResponse(200, {}, b'{"artists": []}', url),
            ttl_seconds=60,
        )
        state["now"] = 2000.0
        transport = FakeTransport([EnrichmentTransportError("t")] * 3)
        from michi.infrastructure.enrichment_musicbrainz import (
            MusicBrainzIdentityResolver,
        )

        resolver = MusicBrainzIdentityResolver(
            transport, InstantLimiter(), cache=cache, retry_sleeper=lambda s: None
        )
        from michi.domain.enrichment import ArtistIdentityEvidence

        with pytest.raises(EnrichmentProviderError):
            resolver.find_artist_candidates(
                ArtistIdentityEvidence(local_artist_key="k", local_artist_name="n")
            )
