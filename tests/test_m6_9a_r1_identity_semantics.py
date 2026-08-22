"""M6.9A-R1 — identity semantics behavioral tests (§59-62, §76-80).

Behavioral (not source-string) tests for the R1 matching semantics:
- year-only resolution is FORBIDDEN for artists AND albums
- name-only resolution never resolves (service level)
- homonym safety: same-name artists need associated album evidence
- candidate permutations never change verdicts (artist + album)
- wrong external id / wrong local key payloads are MISMATCHED with
  zero repository writes (artist + album)
- release-level facts require a specific release identity (invariant)
"""

import pytest
from enrichment_fakes import (
    FakeAlbumProvider,
    FakeArtistProvider,
    FakeIdentityResolver,
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)

from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    AlbumKnowledgeProfile,
    ArtistCandidate,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    DeliveryVerdict,
    IdentityResolutionStatus,
    LocalAlbumEvidence,
    ReleaseGroupCandidate,
    resolve_album_identity,
    resolve_artist_identity,
)


def make_service(resolver=None):
    return EnrichmentService(
        resolver=resolver or FakeIdentityResolver(),
        artist_provider=FakeArtistProvider(),
        album_provider=FakeAlbumProvider(),
        repository=RecordingKnowledgeRepository(),
        identity_repository=InMemoryIdentityRepository(),
    )


class TestYearOnlyIsForbidden:
    def test_artist_year_only_never_resolves(self):
        # Local: only a year. Candidates: same name, albums with matching
        # years but titles that never match the local library.
        evidence = ArtistIdentityEvidence(
            local_artist_key="artist-a",
            local_artist_name="John Williams",
            known_albums=(LocalAlbumEvidence("", 1978),),
        )
        candidates = [
            ArtistCandidate(
                "mb-a",
                canonical_name="John Williams",
                known_albums=(LocalAlbumEvidence("Star Wars", 1978),),
            ),
            ArtistCandidate(
                "mb-b",
                canonical_name="John Williams",
                known_albums=(LocalAlbumEvidence("Other", 2001),),
            ),
        ]
        resolution = resolve_artist_identity(candidates, evidence)
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS
        assert resolution.external_entity_id == ""

    def test_album_year_only_never_resolves(self):
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="",
            local_year=1959,
        )
        resolution = resolve_album_identity(
            [
                ReleaseGroupCandidate(
                    release_group_id="rg-a",
                    title="Kind of Blue",
                    first_release_year=1959,
                )
            ],
            [],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_album_title_gate_ignores_year_coincidence(self):
        # Local title Kind of Blue: rg-b has the matching YEAR but not the
        # title — the title gate excludes it regardless.
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Kind of Blue",
            local_year=1970,
        )
        resolution = resolve_album_identity(
            [
                ReleaseGroupCandidate(
                    release_group_id="rg-a",
                    title="Kind of Blue",
                    first_release_year=1959,
                ),
                ReleaseGroupCandidate(
                    release_group_id="rg-b",
                    title="Bitches Brew",
                    first_release_year=1970,
                ),
            ],
            [],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"


class TestNameOnlyNeverResolvesService:
    def test_name_only_artist_request_has_no_request(self):
        service = make_service(
            resolver=FakeIdentityResolver(
                artists=[
                    ArtistCandidate("mb-a", canonical_name="John Williams"),
                    ArtistCandidate("mb-b", canonical_name="John Williams"),
                ]
            )
        )
        evidence = ArtistIdentityEvidence(
            local_artist_key="john williams", local_artist_name="John Williams"
        )
        outcome = service.request_artist_enrichment(evidence)
        assert outcome.request is None
        assert outcome.resolution.status is IdentityResolutionStatus.AMBIGUOUS


class TestHomonymSafety:
    def test_same_name_different_evidence_resolves_correct_artist(self):
        composer = ArtistCandidate(
            "mb-composer",
            canonical_name="John Williams",
            known_albums=(LocalAlbumEvidence("Star Wars", 1977),),
        )
        guitarist = ArtistCandidate(
            "mb-guitarist",
            canonical_name="John Williams",
            known_albums=(LocalAlbumEvidence("The Height Below", 1969),),
        )
        service = make_service(
            resolver=FakeIdentityResolver(artists=[composer, guitarist])
        )
        evidence = ArtistIdentityEvidence(
            local_artist_key="john williams",
            local_artist_name="John Williams",
            known_albums=(LocalAlbumEvidence("Star Wars", 1977),),
        )
        outcome = service.request_artist_enrichment(evidence)
        assert outcome.request is not None
        assert outcome.request.external_entity_id == "mb-composer"


class TestPermutationDeterminism:
    def test_artist_permutation_same_verdict(self):
        from itertools import permutations

        candidates = [
            ArtistCandidate(
                "mb-a",
                canonical_name="Artist A",
                known_albums=(LocalAlbumEvidence("Album One", 1980),),
            ),
            ArtistCandidate(
                "mb-b",
                canonical_name="Artist A",
                known_albums=(LocalAlbumEvidence("Album Two", 1990),),
            ),
        ]
        evidence = ArtistIdentityEvidence(
            local_artist_key="artist a",
            local_artist_name="Artist A",
            known_albums=(LocalAlbumEvidence("Album One", 1980),),
        )
        expected = resolve_artist_identity(candidates, evidence)
        assert expected.status is IdentityResolutionStatus.RESOLVED
        for permuted in permutations(candidates):
            assert resolve_artist_identity(permuted, evidence) == expected

    def test_album_permutation_same_verdict(self):
        from itertools import permutations

        candidates = [
            ReleaseGroupCandidate(
                release_group_id="rg-a",
                title="Greatest Hits",
                first_release_year=1980,
            ),
            ReleaseGroupCandidate(
                release_group_id="rg-b",
                title="Greatest Hits",
                first_release_year=1990,
            ),
        ]
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Greatest Hits",
            local_year=1980,
        )
        expected = resolve_album_identity(candidates, [], evidence)
        assert expected.status is IdentityResolutionStatus.RESOLVED
        assert expected.release_group_id == "rg-a"
        for permuted in permutations(candidates):
            assert resolve_album_identity(permuted, [], evidence) == expected


class TestPayloadCorrelationGuards:
    def test_artist_wrong_external_id_no_write(self):
        service = make_service()
        repository = service._repository
        evidence = ArtistIdentityEvidence(
            local_artist_key="artist a",
            local_artist_name="Artist A",
            identity_hints=ArtistIdentityHints(artist_ids=("mb-a",)),
        )
        outcome = service.request_artist_enrichment(evidence)
        wrong = service._artist_provider.fetch_profile("artist a", "mb-b")
        assert (
            service.deliver_artist_profile(outcome.request, wrong)
            is DeliveryVerdict.MISMATCHED
        )
        assert repository.write_count == 0

    def test_artist_wrong_local_key_no_write(self):
        service = make_service()
        repository = service._repository
        evidence = ArtistIdentityEvidence(
            local_artist_key="artist a",
            local_artist_name="Artist A",
            identity_hints=ArtistIdentityHints(artist_ids=("mb-a",)),
        )
        outcome = service.request_artist_enrichment(evidence)
        wrong = service._artist_provider.fetch_profile("artist b", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, wrong)
            is DeliveryVerdict.MISMATCHED
        )
        assert repository.write_count == 0

    def test_album_wrong_external_id_no_write(self):
        service = make_service()
        repository = service._repository
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Album X",
            identity_hints=AlbumIdentityHints(release_group_ids=("rg-a",)),
        )
        outcome = service.request_album_enrichment(evidence)
        wrong = service._album_provider.fetch_profile("album-a", "rg-b")
        assert (
            service.deliver_album_profile(outcome.request, wrong)
            is DeliveryVerdict.MISMATCHED
        )
        assert repository.write_count == 0

    def test_album_wrong_local_key_no_write(self):
        service = make_service()
        repository = service._repository
        evidence = AlbumIdentityEvidence(
            local_album_key="album-a",
            local_album_title="Album X",
            identity_hints=AlbumIdentityHints(release_group_ids=("rg-a",)),
        )
        outcome = service.request_album_enrichment(evidence)
        wrong = service._album_provider.fetch_profile("album-b", "rg-a")
        assert (
            service.deliver_album_profile(outcome.request, wrong)
            is DeliveryVerdict.MISMATCHED
        )
        assert repository.write_count == 0


class TestReleaseLevelInvariants:
    def test_label_requires_release_identity(self):
        with pytest.raises(ValueError):
            AlbumKnowledgeProfile(
                local_album_key="album-a",
                release_group_id="rg-a",
                label="Columbia",
            )

    def test_release_year_requires_release_identity(self):
        with pytest.raises(ValueError):
            AlbumKnowledgeProfile(
                local_album_key="album-a",
                release_group_id="rg-a",
                release_year=1959,
            )

    def test_release_facts_allowed_with_release_identity(self):
        profile = AlbumKnowledgeProfile(
            local_album_key="album-a",
            release_group_id="rg-a",
            release_id="rel-1",
            release_year=1959,
            label="Columbia",
        )
        assert profile.release_id == "rel-1"
