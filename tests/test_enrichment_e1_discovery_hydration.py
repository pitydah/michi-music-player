"""POST-R4 P8 (E1) — MusicBrainz discovery vs evidence hydration.

Sobre el resolver PRODUCTIVO (transport fake scriptado, cero red):

- el candidato correcto devuelto por MB en la posición cruda 6+ debe
  poder resolverse (el viejo artists[:5] lo descartaba antes de cualquier
  evidencia);
- 25 candidatos NUNCA causan hydration de los 25: el shortlist por
  evidencia barata (nombre exacto + hints) acota la discografía que se
  descarga;
- el contrato de red es bounded: search = 1 request; hydration <= N
  candidatos; páginas por candidato acotadas.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from michi.domain.enrichment import (  # noqa: E402
    ArtistIdentityEvidence,
    IdentityResolutionStatus,
    LocalAlbumEvidence,
)
from michi.infrastructure.enrichment_musicbrainz import (  # noqa: E402
    MAX_ARTIST_CANDIDATES,
    MusicBrainzIdentityResolver,
)
from tests.test_m6_9c_resolver_hints import (  # noqa: E402
    FakeHttpTransport,
    InstantLimiter,
    artist_payload,
    json_response,
)


def _resolver(transport):
    return MusicBrainzIdentityResolver(
        transport, InstantLimiter(), cache=None, retry_sleeper=lambda s: None
    )


def _rg_page(rgs):
    return json_response({"release-groups": rgs})


def _rg(artist_id, title, year):
    return {"id": f"rg-{artist_id}", "title": title, "first-release-date": str(year)}


class TestDiscoveryHydrationSeparation:
    def test_raw_position_six_candidate_resolves(self):
        """25 resultados: el correcto vive en la posición cruda 6 (índice
        5). Debe ser elegible: find (1 request) → rank por nombre →
        hydrate del finalista (1 browse) → RESOLVED."""
        transport = FakeHttpTransport()
        artists = [
            artist_payload(f"mb-wrong-{i}", f"Wrong Artist {i}")
            for i in range(25)
            if i != 5
        ]
        artists.insert(5, artist_payload("mb-miles", "Miles Davis"))
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response({"artists": artists}),
        )
        transport.route(
            "https://musicbrainz.org/ws/2/release-group/?artist=mb-miles",
            _rg_page([_rg("mb-miles", "Kind of Blue", 1959)]),
        )
        resolver = _resolver(transport)
        evidence = ArtistIdentityEvidence(
            local_artist_key="miles",
            local_artist_name="Miles Davis",
            known_albums=(LocalAlbumEvidence(title="Kind of Blue", year=1959),),
        )
        # discovery: TODOS los summaries (el 6+ existe)
        candidates = resolver.find_artist_candidates(evidence)
        assert any(c.external_artist_id == "mb-miles" for c in candidates), (
            "el candidato de la posición cruda 6 existe en el discovery"
        )
        finalists = resolver.rank_artist_candidates(candidates, evidence)
        assert [c.external_artist_id for c in finalists] == ["mb-miles"], (
            "el shortlist por nombre deja solo al correcto"
        )
        hydrated = resolver.hydrate_artist_candidates(finalists)
        assert hydrated[0].known_albums, "el finalista se hidrata"
        from michi.domain.enrichment import resolve_artist_identity

        resolution = resolve_artist_identity(hydrated, evidence)
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-miles"
        # contrato de red bounded: search(1) + hydration(1 candidato)
        browse_requests = [
            u for u in transport.requests if "release-group/?artist=" in u
        ]
        assert len(browse_requests) == 1, "solo el finalista hidrata su discografía"

    def test_twenty_five_homonyms_hydrate_at_most_shortlist_bound(self):
        """25 homónimos: la hydratación NO descarga 25 discografías — el
        bound del shortlist (MAX_ARTIST_CANDIDATES) aplica DESPUÉS del
        ranking determinístico."""
        transport = FakeHttpTransport()
        artists = [artist_payload(f"mb-x-{i:02d}", "Miles Davis") for i in range(25)]
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response({"artists": artists}),
        )
        for i in range(MAX_ARTIST_CANDIDATES):
            transport.route(
                f"https://musicbrainz.org/ws/2/release-group/?artist=mb-x-{i:02d}",
                _rg_page([_rg(f"mb-x-{i:02d}", "Kind of Blue", 1959)]),
            )
        resolver = _resolver(transport)
        evidence = ArtistIdentityEvidence(
            local_artist_key="miles",
            local_artist_name="Miles Davis",
            known_albums=(LocalAlbumEvidence(title="Kind of Blue", year=1959),),
        )
        candidates = resolver.find_artist_candidates(evidence)
        finalists = resolver.rank_artist_candidates(candidates, evidence)
        assert len(finalists) == MAX_ARTIST_CANDIDATES, (
            "shortlist acotado tras el ranking"
        )
        hydrated = resolver.hydrate_artist_candidates(finalists)
        assert len(hydrated) == MAX_ARTIST_CANDIDATES
        browse_requests = [
            u for u in transport.requests if "release-group/?artist=" in u
        ]
        assert len(browse_requests) == MAX_ARTIST_CANDIDATES, (
            f"nunca 25 hydrations (obtenidas: {len(browse_requests)})"
        )

    def test_non_matching_names_never_hydrate(self):
        """Ningún candidato matchea el nombre local: cero hydrations — el
        discovery cuesta 1 request y el resultado es NO_MATCH/AMBIGUOUS
        sin descargar discografías."""
        transport = FakeHttpTransport()
        transport.route(
            "https://musicbrainz.org/ws/2/artist/?query=",
            json_response(
                {
                    "artists": [
                        artist_payload(f"mb-other-{i}", f"Other {i}") for i in range(25)
                    ]
                }
            ),
        )
        resolver = _resolver(transport)
        evidence = ArtistIdentityEvidence(
            local_artist_key="miles",
            local_artist_name="Miles Davis",
            known_albums=(LocalAlbumEvidence(title="Kind of Blue", year=1959),),
        )
        candidates = resolver.find_artist_candidates(evidence)
        finalists = resolver.rank_artist_candidates(candidates, evidence)
        assert finalists == (), "sin finalistas por nombre"
        resolver.hydrate_artist_candidates(finalists)
        browse_requests = [
            u for u in transport.requests if "release-group/?artist=" in u
        ]
        assert browse_requests == [], "cero hydrations sin finalistas"
