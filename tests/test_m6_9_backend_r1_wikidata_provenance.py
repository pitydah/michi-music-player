"""M6.9-BACKEND-R1 — Wikidata determinism + cross-provider provenance.

- claim selection: preferred single / duplicate / contradictory; normal
  single / contradictory; deprecated ignored; response permutation
  independence; country_qid never disguised as a label; verified
  sitelink fallback (requested language → enwiki).
- provenance ownership: MusicBrainz facts stay MB-attributed; Wikidata
  facts carry wikidata_provenance; Wikipedia biography has Wikipedia
  provenance; retrieved_at is populated; is_stale is truthful.
"""

import json

from michi.application.enrichment_ports import (
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
)
from michi.infrastructure.enrichment_http import MusicBrainzRateLimiter
from michi.infrastructure.enrichment_knowledge import (
    MusicBrainzKnowledgeProvider,
    WikidataKnowledgeProvider,
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


def wikidata_payload(claims, sitelinks=None):
    return HttpResponse(
        200,
        {},
        json.dumps(
            {"entities": {"Q1": {"claims": claims, "sitelinks": sitelinks or {}}}}
        ).encode(),
        "https://www.wikidata.org/x",
    )


def str_claim(value, rank="normal"):
    return {
        "rank": rank,
        "mainsnak": {"datavalue": {"value": value}},
    }


class TestWikidataClaimDeterminism:
    def _provider(self, claims):
        transport = FakeTransport([wikidata_payload(claims)])
        return WikidataKnowledgeProvider(transport, cache=None, sleeper=lambda s: None)

    def test_one_preferred_claim_used(self):
        claims = {"P856": [str_claim("https://a.example", "preferred")]}
        result = self._provider(claims).fetch_artist_claims("Q1")
        assert result.official_website == "https://a.example"

    def test_duplicate_identical_preferred_claims_used(self):
        claims = {
            "P856": [
                str_claim("https://a.example", "preferred"),
                str_claim("https://a.example", "preferred"),
            ]
        }
        result = self._provider(claims).fetch_artist_claims("Q1")
        assert result.official_website == "https://a.example"

    def test_two_contradictory_preferred_claims_unresolved(self):
        claims = {
            "P856": [
                str_claim("https://a.example", "preferred"),
                str_claim("https://b.example", "preferred"),
            ]
        }
        result = self._provider(claims).fetch_artist_claims("Q1")
        assert result.official_website == ""

    def test_one_normal_claim_used(self):
        claims = {"P856": [str_claim("https://a.example", "normal")]}
        result = self._provider(claims).fetch_artist_claims("Q1")
        assert result.official_website == "https://a.example"

    def test_two_contradictory_normal_claims_unresolved(self):
        claims = {
            "P856": [
                str_claim("https://a.example", "normal"),
                str_claim("https://b.example", "normal"),
            ]
        }
        result = self._provider(claims).fetch_artist_claims("Q1")
        assert result.official_website == ""

    def test_deprecated_ignored(self):
        claims = {
            "P856": [
                str_claim("https://bad.example", "deprecated"),
                str_claim("https://good.example", "normal"),
            ]
        }
        result = self._provider(claims).fetch_artist_claims("Q1")
        assert result.official_website == "https://good.example"

    def test_response_permutation_independent(self):
        from itertools import permutations

        base = [
            str_claim("https://a.example", "preferred"),
            str_claim("https://b.example", "preferred"),
            str_claim("https://c.example", "normal"),
        ]
        for permuted in permutations(base):
            provider = self._provider({"P856": list(permuted)})
            # Contradictory preferred values stay unresolved for EVERY
            # ordering — provider order is never authority.
            assert provider.fetch_artist_claims("Q1").official_website == ""

    def test_country_qid_not_disguised_as_label(self):
        claims = {
            "P27": [
                {
                    "rank": "preferred",
                    "mainsnak": {"datavalue": {"value": {"id": "Q145"}}},
                }
            ]
        }
        result = self._provider(claims).fetch_artist_claims("Q1")
        assert result.country_qid == "Q145"
        assert result.country_label == ""  # labels never invented

    def test_sitelink_fallback_requested_then_enwiki(self):
        claims = {"P856": []}
        sitelinks = {
            "eswiki": {"title": "Artista"},
            "enwiki": {"title": "Artist"},
        }
        provider = WikidataKnowledgeProvider(
            FakeTransport([wikidata_payload(claims, sitelinks)]),
            cache=None,
            sleeper=lambda s: None,
        )
        result = provider.fetch_artist_claims("Q1", preferred_language="es")
        assert result.wikipedia_title == "Artista"
        assert result.wikipedia_language == "es"
        # fr is absent → deterministic enwiki fallback.
        transport = FakeTransport([wikidata_payload(claims, sitelinks)])
        fallback = WikidataKnowledgeProvider(
            transport, cache=None, sleeper=lambda s: None
        ).fetch_artist_claims("Q1", preferred_language="fr")
        assert fallback.wikipedia_title == "Artist"
        assert fallback.wikipedia_language == "en"


class TestCrossProviderProvenance:
    def test_musicbrainz_facts_stay_mb_attributed(self):
        transport = FakeTransport(
            [
                HttpResponse(
                    200,
                    {},
                    json.dumps(
                        {
                            "id": "mb-a",
                            "life-span": {"begin": "1932", "end": ""},
                            "genres": [],
                        }
                    ).encode(),
                    "https://musicbrainz.org/x",
                )
            ]
        )
        profile = MusicBrainzKnowledgeProvider(
            transport, InstantLimiter(), cache=None, sleeper=lambda s: None
        ).fetch_artist("k", "mb-a")
        assert profile.provenance.provider == "musicbrainz"
        assert profile.begin_year == 1932
        # Wikidata fields are separate — never silently merged.
        assert profile.wikidata_begin_year == 0
        assert profile.wikidata_provenance.provider == ""

    def test_retrieved_at_populated(self):
        transport = FakeTransport(
            [
                HttpResponse(
                    200,
                    {},
                    json.dumps({"id": "mb-a", "genres": []}).encode(),
                    "https://musicbrainz.org/x",
                )
            ]
        )
        profile = MusicBrainzKnowledgeProvider(
            transport,
            InstantLimiter(),
            cache=None,
            sleeper=lambda s: None,
            clock=lambda: "2026-01-02T03:04:05+00:00",
        ).fetch_artist("k", "mb-a")
        assert profile.provenance.retrieved_at == "2026-01-02T03:04:05+00:00"
        assert profile.provenance.is_stale is False

    def test_wikipedia_biography_has_wikipedia_provenance_fields(self):
        from michi.domain.enrichment import BiographyKnowledge

        bio = BiographyKnowledge(
            text="x",
            page_title="P",
            source_url="https://en.wikipedia.org/wiki/P",
            language="en",
            retrieved_at="2026-01-01T00:00:00+00:00",
            is_stale=False,
        )
        assert bio.retrieved_at
        assert bio.is_stale is False
