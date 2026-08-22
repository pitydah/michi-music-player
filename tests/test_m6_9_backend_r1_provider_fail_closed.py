"""M6.9-BACKEND-R1 — fail-closed resolution + offline embedded authority.

- P1-04: a support-evidence (album browse) failure ABORTS the whole
  artist resolution — it can never fake uniqueness; zero identity writes.
- Offline embedded authority: single embedded artist/RG ids resolve
  WITHOUT network; conflicts produce IDENTITY_CONFLICT with zero
  network; release edition never trusted without corroboration.
"""

import pytest
from enrichment_fakes import (
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)

from michi.application.enrichment_ports import (
    EnrichmentProviderError,
    EnrichmentTransportError,
    ExternalIdentityResolverPort,
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
)
from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    IdentityResolutionStatus,
    MatchMethod,
)
from michi.infrastructure.enrichment_http import (
    MusicBrainzRateLimiter,
)
from michi.infrastructure.enrichment_musicbrainz import (
    MusicBrainzIdentityResolver,
)


class ScriptedTransport(HttpTransportPort):
    """Sequence of responses/errors consumed FIFO."""

    def __init__(self, script):
        self.script = list(script)
        self.requests: list[str] = []

    def get(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request.url)
        item = self.script.pop(0) if self.script else None
        if item is None:
            raise AssertionError("unscripted request")
        if isinstance(item, Exception):
            raise item
        return item


class InstantLimiter(MusicBrainzRateLimiter):
    def __init__(self):
        super().__init__(clock=lambda: 0.0, sleeper=lambda s: None)


class TestFalseUniquenessGate:
    def test_support_evidence_failure_aborts_resolution(self):
        import json

        transport = ScriptedTransport(
            [
                # artist search: two candidates
                HttpResponse(
                    200,
                    {},
                    json.dumps(
                        {
                            "artists": [
                                {"id": "mb-a", "name": "John Williams"},
                                {"id": "mb-b", "name": "John Williams"},
                            ]
                        }
                    ).encode(),
                    "https://musicbrainz.org/x",
                ),
                # albums for A: success
                HttpResponse(
                    200,
                    {},
                    json.dumps(
                        {"release-groups": [{"id": "rg-1", "title": "Star Wars"}]}
                    ).encode(),
                    "https://musicbrainz.org/x",
                ),
                # albums for B: transport failure (would exhaust retries)
                EnrichmentTransportError("timeout"),
                EnrichmentTransportError("timeout"),
                EnrichmentTransportError("timeout"),
            ]
        )
        resolver = MusicBrainzIdentityResolver(
            transport, InstantLimiter(), cache=None, retry_sleeper=lambda s: None
        )
        service = EnrichmentService(
            resolver=resolver,
            artist_provider=None,
            album_provider=None,
            repository=RecordingKnowledgeRepository(),
            identity_repository=InMemoryIdentityRepository(),
        )
        evidence = ArtistIdentityEvidence(
            local_artist_key="jw", local_artist_name="John Williams"
        )
        with pytest.raises(EnrichmentProviderError):
            service.request_artist_enrichment(evidence)
        # ZERO false identity: no pending request, no identity row.
        assert service.pending_count() == 0
        assert service._identity_repository.load_artist_identity("jw") is None


class OfflineHintResolver(ExternalIdentityResolverPort):
    def __init__(self, raise_on_any_call=False):
        self.raise_on_any_call = raise_on_any_call
        self.artist_calls = 0
        self.group_calls = 0

    def find_artist_candidates(self, evidence: ArtistIdentityEvidence):
        self.artist_calls += 1
        if self.raise_on_any_call:
            raise EnrichmentTransportError("offline")
        return ()

    def find_release_group_candidates(self, evidence: AlbumIdentityEvidence):
        self.group_calls += 1
        if self.raise_on_any_call:
            raise EnrichmentTransportError("offline")
        return ()

    def find_release_edition_candidates(self, evidence: AlbumIdentityEvidence):
        if self.raise_on_any_call:
            raise EnrichmentTransportError("offline")
        return ()


class TestOfflineEmbeddedAuthority:
    def test_single_artist_hint_works_offline(self):
        resolver = OfflineHintResolver(raise_on_any_call=True)
        service = EnrichmentService(
            resolver=resolver,
            artist_provider=None,
            album_provider=None,
            repository=RecordingKnowledgeRepository(),
            identity_repository=InMemoryIdentityRepository(),
        )
        evidence = ArtistIdentityEvidence(
            local_artist_key="artist a",
            local_artist_name="Artist A",
            identity_hints=ArtistIdentityHints(artist_ids=("mb-a",)),
        )
        outcome = service.request_artist_enrichment(evidence)
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "mb-a"
        assert resolver.artist_calls == 0  # hint resolved WITHOUT search
        identity = service._identity_repository.load_artist_identity("artist a")
        assert identity.match_method is MatchMethod.EMBEDDED_HINT

    def test_conflicting_artist_hints_zero_network(self):
        resolver = OfflineHintResolver(raise_on_any_call=True)
        service = EnrichmentService(
            resolver=resolver,
            artist_provider=None,
            album_provider=None,
            repository=RecordingKnowledgeRepository(),
            identity_repository=InMemoryIdentityRepository(),
        )
        evidence = ArtistIdentityEvidence(
            local_artist_key="artist a",
            local_artist_name="Artist A",
            identity_hints=ArtistIdentityHints(artist_ids=("mb-a", "mb-b")),
        )
        outcome = service.request_artist_enrichment(evidence)
        assert outcome.request is None
        assert outcome.resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert resolver.artist_calls == 0

    def test_single_album_rg_hint_works_offline(self):
        resolver = OfflineHintResolver(raise_on_any_call=True)
        service = EnrichmentService(
            resolver=resolver,
            artist_provider=None,
            album_provider=None,
            repository=RecordingKnowledgeRepository(),
            identity_repository=InMemoryIdentityRepository(),
        )
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Album X",
            identity_hints=AlbumIdentityHints(release_group_ids=("rg-x",)),
        )
        outcome = service.request_album_enrichment(evidence)
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "rg-x"
        assert resolver.group_calls == 0

    def test_album_rg_plus_release_offline_keeps_rg_release_untrusted(self):
        resolver = OfflineHintResolver(raise_on_any_call=True)
        service = EnrichmentService(
            resolver=resolver,
            artist_provider=None,
            album_provider=None,
            repository=RecordingKnowledgeRepository(),
            identity_repository=InMemoryIdentityRepository(),
        )
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Album X",
            identity_hints=AlbumIdentityHints(
                release_group_ids=("rg-x",), release_ids=("rel-a",)
            ),
        )
        outcome = service.request_album_enrichment(evidence)
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "rg-x"
        # R1: without corroboration the edition stays "".
        assert outcome.request.external_variant_id == ""

    def test_release_hint_only_offline_no_invented_identity(self):
        resolver = OfflineHintResolver(raise_on_any_call=True)
        service = EnrichmentService(
            resolver=resolver,
            artist_provider=None,
            album_provider=None,
            repository=RecordingKnowledgeRepository(),
            identity_repository=InMemoryIdentityRepository(),
        )
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Album X",
            identity_hints=AlbumIdentityHints(release_ids=("rel-a",)),
        )
        # Resolution requires corroboration; the offline resolver raises
        # and NO invented RG identity is persisted.
        with pytest.raises(EnrichmentProviderError):
            service.request_album_enrichment(evidence)
        assert service._identity_repository.load_album_identity("album-a") is None
