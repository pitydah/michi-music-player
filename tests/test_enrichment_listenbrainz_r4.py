"""P6 — ListenBrainz supplemental provider tests (R4 §22C/§22AO).

- MBID-only metadata: bounded, meaningful User-Agent, no token required;
- tags parse from the LB metadata payload shape (community tags);
- optional-provider failures never break the coordinator flow;
- the coordinator merge adds listenbrainz_tags/popularity to the
  committed profile (post-MBID) with its own provenance;
- zero identity mutation: LB never runs pre-resolution.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrichment_presentation_fakes import (  # noqa: E402
    process_events,
)

from michi.infrastructure.enrichment_listenbrainz import (  # noqa: E402
    LB_API_ROOT,
    ListenBrainzSupplementalProvider,
    _parse_tags,
)


class _StaticTransport:
    """Devuelve el payload configurado (sin red real)."""

    def __init__(self, payload=None, status=200):
        self._payload = payload if payload is not None else {}
        self._status = status
        self.request_urls = []

    def get(self, request):
        self.request_urls.append(request.url)
        if self._status >= 400:
            raise RuntimeError(f"http {self._status}")
        return _FakeResponse(self._payload)


class _FakeResponse:
    def __init__(self, payload):
        self.body = _json_bytes(payload)

    @property
    def status(self):
        return 200


def _json_bytes(payload):
    import json

    return json.dumps(payload).encode("utf-8")


_ARTIST_PAYLOAD = {
    "artist_mbid": "mb-art-1",
    "tags": [
        {"tag": "Jazz", "count": 120},
        {"tag": "modal-jazz", "count": 40},
        {"tag": "jazz", "count": 90},
    ],
    "artist": {"artist_credit_name": "Artist A"},
}

_ALBUM_PAYLOAD = {
    "release_group_mbid": "rg-x",
    "tags": [
        {"tag": "Jazz", "count": 88},
        {"tag": "classic", "count": 12},
    ],
}


class TestProviderParsing:
    def test_tags_parse_sorted_casefolded_deduped(self):
        tags = _parse_tags(_ARTIST_PAYLOAD)
        assert tags == ("jazz", "modal-jazz"), tags

    def test_provider_fetch_artist_metadata(self, qapp):
        transport = _StaticTransport(_ARTIST_PAYLOAD)
        provider = ListenBrainzSupplementalProvider(transport=transport)
        supplement = provider.fetch_artist_metadata("mb-art-1")
        assert supplement.tags == ("jazz", "modal-jazz")
        assert supplement.provenance.provider == "listenbrainz"
        assert "mb-art-1" in supplement.provenance.external_entity_id
        # URL MBID-only, bounded endpoint:
        assert transport.request_urls[0].startswith(LB_API_ROOT + "/artist/")
        assert "mb-art-1" in transport.request_urls[0]
        assert "token" not in transport.request_urls[0].lower(), (
            "no se exige token de usuario para los endpoints MBID"
        )

    def test_provider_fetch_release_group_metadata(self, qapp):
        transport = _StaticTransport(_ALBUM_PAYLOAD)
        provider = ListenBrainzSupplementalProvider(transport=transport)
        supplement = provider.fetch_release_group_metadata("rg-x")
        assert supplement.tags == ("classic", "jazz")
        assert transport.request_urls[0].startswith(LB_API_ROOT + "/release-group/")

    def test_mbid_required(self, qapp):
        from michi.application.enrichment_ports import EnrichmentProviderError

        provider = ListenBrainzSupplementalProvider(transport=_StaticTransport())
        with pytest.raises(EnrichmentProviderError):
            provider.fetch_artist_metadata("")


class TestCoordinatorMerge:
    def test_supplemental_merge_after_mb_success(self, qapp, tmp_path):
        """Con el provider LB opcional, el perfil commiteado lleva los
        tags suplementarios y su provenance propia (post-MBID)."""
        from enrichment_presentation_fakes import make_bridge

        bridge, service, _, repository, _, _, _ = make_bridge(online=True)
        # el bridge de make_bridge no trae el LB: verifico el merge por el
        # flujo del coordinator real con un LB estático:
        # (construir el coordinator del make_bridge + el hook LB)
        coordinator = bridge._coordinator
        transport = _StaticTransport(_ARTIST_PAYLOAD)
        provider = ListenBrainzSupplementalProvider(transport=transport)
        coordinator._lb_supplemental = provider
        bridge.activate_artist("artist a")
        process_events(80)
        stored = repository.load_artist_profile("artist a")
        assert stored is not None
        assert stored.listenbrainz_tags, (
            "los tags suplementarios llegan al perfil persistido"
        )
        assert stored.listenbrainz_provenance.provider == "listenbrainz"
        # El perfil del MB no se degrada (los campos previos intactos).
        assert stored.external_genres is not None

    def test_supplemental_failure_keeps_core_usable(self, qapp, tmp_path):
        """El fallo del provider opcional nunca rompe el flujo principal:
        el perfil de MusicBrainz se commitea igualmente."""
        from enrichment_presentation_fakes import make_bridge

        bridge, service, _, repository, _, _, _ = make_bridge(online=True)
        coordinator = bridge._coordinator

        class _ExplodingProvider:
            def fetch_artist_metadata(self, artist_mbid):
                raise RuntimeError("lb down")

            def fetch_release_group_metadata(self, release_group_mbid):
                raise RuntimeError("lb down")

        coordinator._lb_supplemental = _ExplodingProvider()
        bridge.activate_artist("artist a")
        process_events(80)
        stored = repository.load_artist_profile("artist a")
        assert stored is not None, "el fallo del LB opcional no impide el perfil de MB"
        assert stored.listenbrainz_tags == ()
