"""POST-R4 P9 (E2) — direct MusicBrainz identifier resolution.

- parse_musicbrainz_identifier: acepta MBID crudo y URLs de
  musicbrainz.org (artist/release-group) con validación controlada;
  el texto arbitrario NUNCA es una identidad;
- el flujo de búsqueda manual del coordinator: un texto con formato de
  identidad hace el LOOKUP directo del candidato exacto (cero búsqueda
  por nombre); el texto arbitrario sigue la búsqueda normal;
- el tipo de entidad equivocado (URL de release en un lookup de
  artista) se rechaza.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from michi.domain.enrichment import (  # noqa: E402
    parse_musicbrainz_identifier,
)


class TestIdentifierValidation:
    MBID = "12345678-1234-1234-1234-123456789abc"

    def test_raw_mbid_accepted(self):
        assert parse_musicbrainz_identifier(self.MBID) == self.MBID
        assert (
            parse_musicbrainz_identifier(self.MBID, expected_kind="artist") == self.MBID
        )

    def test_artist_url_accepted(self):
        url = f"https://musicbrainz.org/artist/{self.MBID}"
        assert parse_musicbrainz_identifier(url) == self.MBID
        assert parse_musicbrainz_identifier(url, expected_kind="artist") == self.MBID

    def test_release_group_url_accepted(self):
        url = f"https://musicbrainz.org/release-group/{self.MBID}"
        assert (
            parse_musicbrainz_identifier(url, expected_kind="release-group")
            == self.MBID
        )

    def test_wrong_entity_kind_rejected(self):
        url = f"https://musicbrainz.org/release-group/{self.MBID}"
        assert parse_musicbrainz_identifier(url, expected_kind="artist") == ""
        artist_url = f"https://musicbrainz.org/artist/{self.MBID}"
        assert (
            parse_musicbrainz_identifier(artist_url, expected_kind="release-group")
            == ""
        )

    def test_arbitrary_text_never_an_identity(self):
        for text in (
            "Miles Davis",
            "https://musicbrainz.org/artist/not-a-uuid",
            "12345",
            "https://evil.example/artist/" + self.MBID,
            "",
            "  ",
        ):
            assert parse_musicbrainz_identifier(text) == "", repr(text)


class TestDirectLookupFlow:
    def _make_resolver(self, transport):
        from michi.infrastructure.enrichment_http import MusicBrainzRateLimiter
        from michi.infrastructure.enrichment_musicbrainz import (
            MusicBrainzIdentityResolver,
        )

        class InstantLimiter(MusicBrainzRateLimiter):
            def __init__(self):
                super().__init__(clock=lambda: 0.0, sleeper=lambda s: None)

        return MusicBrainzIdentityResolver(
            transport, InstantLimiter(), cache=None, retry_sleeper=lambda s: None
        )

    def test_artist_mbid_performs_lookup_not_name_search(self, tmp_path):
        from michi.application.enrichment_coordinator import EnrichmentCoordinator
        from tests.test_m6_9c_resolver_hints import (
            FakeHttpTransport,
            artist_payload,
            json_response,
        )

        mbid = "12345678-1234-1234-1234-123456789abc"
        transport = FakeHttpTransport()
        transport.route(
            f"https://musicbrainz.org/ws/2/artist/{mbid}",
            json_response(artist_payload(mbid, "Miles Davis")),
        )
        resolver = self._make_resolver(transport)
        coordinator = EnrichmentCoordinator(
            service=None,  # type: ignore[arg-type] — solo se usa el resolver
            resolver=resolver,
            evidence_builder=None,
            mb_knowledge=None,
            wikidata=None,
            wikipedia=None,
            commons=None,
            coverart=None,
            asset_store=None,
            executor=None,
            transport=transport,
            enabled=lambda: True,
        )
        views = coordinator._search_artist_candidates_sync(
            f"https://musicbrainz.org/artist/{mbid}"
        )
        assert len(views) == 1
        assert views[0].external_artist_id == mbid
        assert views[0].display_name == "Miles Davis"
        # CERO búsqueda por nombre: solo el lookup directo.
        assert all("/artist/?query=" not in u for u in transport.requests)
        assert any(f"/artist/{mbid}" in u for u in transport.requests)

    def test_arbitrary_text_falls_back_to_name_search(self, tmp_path):
        from michi.application.enrichment_coordinator import EnrichmentCoordinator
        from tests.test_m6_9c_resolver_hints import (
            FakeHttpTransport,
            artist_payload,
            json_response,
        )

        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response({"artists": [artist_payload("mb-a", "Miles Davis")]}),
        )
        resolver = self._make_resolver(transport)
        coordinator = EnrichmentCoordinator(
            service=None,  # type: ignore[arg-type]
            resolver=resolver,
            evidence_builder=None,
            mb_knowledge=None,
            wikidata=None,
            wikipedia=None,
            commons=None,
            coverart=None,
            asset_store=None,
            executor=None,
            transport=transport,
            enabled=lambda: True,
        )
        views = coordinator._search_artist_candidates_sync("Miles Davis")
        assert views and views[0].display_name == "Miles Davis"
        assert any("/artist/?query=" in u for u in transport.requests)
