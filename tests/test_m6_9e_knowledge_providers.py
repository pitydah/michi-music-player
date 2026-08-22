"""M6.9E — knowledge provider matrices (fake HTTP, no live network).

Wikidata: verified QID only, no name search, malformed handling,
deterministic claim selection. Wikipedia: verified title only, bounded
extract, no HTML, provenance. Commons: verified file, license metadata,
UNKNOWN never fabricated. CAA: release vs release-group, front image,
unpermitted results.
"""

import json

import pytest

from michi.application.enrichment_ports import (
    EnrichmentProviderError,
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
)
from michi.infrastructure.enrichment_http import (
    EnrichmentHttpStatusError,
    MusicBrainzRateLimiter,
)
from michi.infrastructure.enrichment_knowledge import (
    CoverArtArchiveProvider,
    MusicBrainzKnowledgeProvider,
    WikidataKnowledgeProvider,
    WikimediaCommonsProvider,
    WikipediaBiographyProvider,
)


class FakeHttpTransport(HttpTransportPort):
    def __init__(self):
        self.routes: list[tuple[str, object]] = []
        self.requests: list[str] = []

    def route(self, prefix: str, response: object) -> None:
        self.routes.append((prefix, response))

    def get(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request.url)
        for index, (prefix, response) in enumerate(self.routes):
            if request.url.startswith(prefix):
                del self.routes[index]
                if isinstance(response, Exception):
                    raise response
                return response
        raise AssertionError(f"unscripted URL: {request.url}")


def json_response(payload, url="https://example.org/x"):
    return HttpResponse(200, {}, json.dumps(payload).encode(), final_url=url)


class InstantLimiter(MusicBrainzRateLimiter):
    def __init__(self):
        super().__init__(clock=lambda: 0.0, sleeper=lambda s: None)


class TestWikidata:
    def test_verified_qid_claims(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://www.wikidata.org/w/api.php",
            json_response(
                {
                    "entities": {
                        "Q42": {
                            "claims": {
                                "P27": [
                                    {
                                        "rank": "normal",
                                        "mainsnak": {
                                            "datavalue": {"value": {"id": "Q145"}}
                                        },
                                    }
                                ],
                                "P856": [
                                    {
                                        "rank": "normal",
                                        "mainsnak": {
                                            "datavalue": {"value": "https://x.org"}
                                        },
                                    }
                                ],
                                "P18": [
                                    {
                                        "rank": "normal",
                                        "mainsnak": {
                                            "datavalue": {"value": "File:Artist.jpg"}
                                        },
                                    }
                                ],
                                "P569": [
                                    {
                                        "rank": "normal",
                                        "mainsnak": {
                                            "datavalue": {
                                                "value": {
                                                    "time": "+1976-00-00T00:00:00Z"
                                                }
                                            }
                                        },
                                    }
                                ],
                            }
                        }
                    }
                }
            ),
        )
        provider = WikidataKnowledgeProvider(transport)
        claims = provider.fetch_artist_claims("Q42")
        assert claims.country == "Q145"
        assert claims.official_website == "https://x.org"
        assert claims.commons_image_title == "Artist.jpg"
        assert claims.begin_year == 1976

    def test_malformed_qid_rejected(self):
        provider = WikidataKnowledgeProvider(FakeHttpTransport())
        with pytest.raises(EnrichmentProviderError):
            provider.fetch_artist_claims("not-a-qid")

    def test_no_qid_means_no_wikidata_fetch(self):
        # No QID → the provider is never invoked at all (coordinator
        # contract); here we assert the provider rejects invalid input.
        provider = WikidataKnowledgeProvider(FakeHttpTransport())
        with pytest.raises(EnrichmentProviderError):
            provider.fetch_artist_claims("")

    def test_malformed_payload_raises(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://www.wikidata.org/w/api.php",
            json_response({"entities": "nope"}),
        )
        with pytest.raises(EnrichmentProviderError):
            WikidataKnowledgeProvider(transport).fetch_artist_claims("Q1")

    def test_deprecated_claim_ignored(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://www.wikidata.org/w/api.php",
            json_response(
                {
                    "entities": {
                        "Q1": {
                            "claims": {
                                "P856": [
                                    {
                                        "rank": "deprecated",
                                        "mainsnak": {
                                            "datavalue": {"value": "https://bad"}
                                        },
                                    },
                                    {
                                        "rank": "normal",
                                        "mainsnak": {
                                            "datavalue": {"value": "https://good"}
                                        },
                                    },
                                ]
                            }
                        }
                    }
                }
            ),
        )
        claims = WikidataKnowledgeProvider(transport).fetch_artist_claims("Q1")
        assert claims.official_website == "https://good"


class TestWikipedia:
    def test_verified_page_extract_bounded(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://en.wikipedia.org/api/rest_v1/page/summary/",
            json_response(
                {
                    "title": "John Williams",
                    "extract": "A long biography " + "x " * 5000,
                    "content_urls": {
                        "desktop": {
                            "page": "https://en.wikipedia.org/wiki/John_Williams"
                        }
                    },
                }
            ),
        )
        provider = WikipediaBiographyProvider(transport)
        bio = provider.fetch_biography("John Williams")
        assert bio.page_title == "John Williams"
        assert len(bio.text) <= 4000
        assert bio.language == "en"
        assert "x " in bio.text

    def test_language_preferred(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://es.wikipedia.org/api/rest_v1/page/summary/",
            json_response({"title": "X", "extract": "bio"}),
        )
        bio = WikipediaBiographyProvider(transport).fetch_biography("X", language="es")
        assert bio.language == "es"

    def test_missing_extract_raises(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://en.wikipedia.org/api/rest_v1/page/summary/",
            json_response({"title": "X"}),
        )
        with pytest.raises(EnrichmentProviderError):
            WikipediaBiographyProvider(transport).fetch_biography("X")

    def test_404_means_no_biography_error(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://en.wikipedia.org/api/rest_v1/page/summary/",
            EnrichmentHttpStatusError(404, {}, "missing"),
        )
        with pytest.raises(EnrichmentProviderError):
            WikipediaBiographyProvider(transport).fetch_biography("X")


class TestCommons:
    def test_verified_image_with_license(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://commons.wikimedia.org/w/api.php",
            json_response(
                {
                    "query": {
                        "pages": {
                            "-1": {
                                "imageinfo": [
                                    {
                                        "url": "https://upload.wikimedia.org/x.jpg",
                                        "extmetadata": {
                                            "LicenseShortName": {
                                                "value": "CC BY-SA 4.0"
                                            },
                                            "LicenseUrl": {
                                                "value": "https://license/x"
                                            },
                                            "Artist": {"value": "Someone"},
                                            "Credit": {"value": "Own work"},
                                        },
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
        )
        image = WikimediaCommonsProvider(transport).fetch_image("Artist.jpg")
        assert image.source_url == "https://upload.wikimedia.org/x.jpg"
        assert image.license == "CC BY-SA 4.0"
        assert image.artist == "Someone"

    def test_missing_license_stays_unknown(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://commons.wikimedia.org/w/api.php",
            json_response(
                {
                    "query": {
                        "pages": {
                            "-1": {
                                "imageinfo": [
                                    {
                                        "url": "https://upload.wikimedia.org/x.jpg",
                                        "extmetadata": {},
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
        )
        image = WikimediaCommonsProvider(transport).fetch_image("X.jpg")
        assert image.license == ""  # UNKNOWN, never fabricated
        assert image.source_url.startswith("https://upload.wikimedia.org/")

    def test_missing_page_raises(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://commons.wikimedia.org/w/api.php",
            json_response({"query": {"pages": {"-1": {"missing": ""}}}}),
        )
        with pytest.raises(EnrichmentProviderError):
            WikimediaCommonsProvider(transport).fetch_image("X.jpg")


class TestCoverArtArchive:
    def test_release_front_cover(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://coverartarchive.org/release/rel-x",
            json_response(
                {
                    "images": [
                        {
                            "front": True,
                            "image": "https://coverartarchive.org/release/rel-x/1.jpg",
                        },
                        {
                            "front": False,
                            "image": "https://coverartarchive.org/back.jpg",
                        },
                    ]
                }
            ),
        )
        cover = CoverArtArchiveProvider(transport).fetch_cover(release_id="rel-x")
        assert cover.entity_kind == "release"
        assert cover.image_url.endswith("/1.jpg")

    def test_release_group_fallback(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://coverartarchive.org/release-group/rg-x",
            json_response(
                {
                    "images": [
                        {"front": True, "image": "https://coverartarchive.org/rg.jpg"}
                    ]
                }
            ),
        )
        cover = CoverArtArchiveProvider(transport).fetch_cover(release_group_id="rg-x")
        assert cover.entity_kind == "release-group"

    def test_404_no_cover(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://coverartarchive.org/release/rel-x",
            EnrichmentHttpStatusError(404, {}, "missing"),
        )
        with pytest.raises(EnrichmentProviderError):
            CoverArtArchiveProvider(transport).fetch_cover(release_id="rel-x")

    def test_unpermitted_image_host_ignored(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://coverartarchive.org/release/rel-x",
            json_response(
                {"images": [{"front": True, "image": "https://evil.com/steal.jpg"}]}
            ),
        )
        cover = CoverArtArchiveProvider(transport).fetch_cover(release_id="rel-x")
        assert cover.image_url == ""  # non-allowlisted image ignored

    def test_requires_entity_id(self):
        with pytest.raises(EnrichmentProviderError):
            CoverArtArchiveProvider(FakeHttpTransport()).fetch_cover()


class TestMusicBrainzKnowledge:
    def test_artist_structured_facts_and_links(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/mb-a?inc=genres+tags",
            json_response(
                {
                    "id": "mb-a",
                    "sort-name": "Williams, John",
                    "type": "Person",
                    "area": {"name": "United States"},
                    "life-span": {"begin": "1932-02-08", "end": ""},
                    "genres": [
                        {"name": "Classical"},
                        {"name": "Film Score"},
                    ],
                }
            ),
        )
        transport.route(
            "https://musicbrainz.org/ws/2/artist/mb-a?inc=url-rels",
            json_response(
                {
                    "relations": [
                        {
                            "type": "wikidata",
                            "url": {"resource": "https://www.wikidata.org/wiki/Q42"},
                        },
                        {
                            "type": "wikipedia",
                            "url": {
                                "resource": "https://en.wikipedia.org/wiki/John_Williams"
                            },
                        },
                    ]
                }
            ),
        )
        provider = MusicBrainzKnowledgeProvider(transport, InstantLimiter())
        profile = provider.fetch_artist("artist a", "mb-a")
        assert profile.external_genres == ("Classical", "Film Score")
        assert profile.begin_year == 1932
        assert profile.area == "United States"
        assert profile.sort_name == "Williams, John"
        links = provider.artist_links("mb-a")
        assert links.wikidata_qid == "Q42"
        assert links.wikipedia_title == "John Williams"
        assert links.wikipedia_language == "en"

    def test_non_wikidata_relations_ignored(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/mb-a?inc=url-rels",
            json_response(
                {
                    "relations": [
                        {
                            "type": "official homepage",
                            "url": {"resource": "https://artist.example"},
                        }
                    ]
                }
            ),
        )
        links = MusicBrainzKnowledgeProvider(transport, InstantLimiter()).artist_links(
            "mb-a"
        )
        assert links.wikidata_qid == ""
        assert links.wikipedia_title == ""

    def test_malformed_top_level_raises(self):
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/mb-a?inc=genres+tags",
            json_response({"genres": "nope"}),
        )
        with pytest.raises(EnrichmentProviderError):
            MusicBrainzKnowledgeProvider(transport, InstantLimiter()).fetch_artist(
                "k", "mb-a"
            )
