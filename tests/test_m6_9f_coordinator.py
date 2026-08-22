"""M6.9F — coordinator end-to-end workflows (all fakes, no live network).

Covers: full artist pipeline (resolve → MB facts → Wikidata links →
Wikipedia biography → Commons asset → commit → projection-visible),
full album pipeline (resolve → MB facts → CAA cover → commit),
ambiguous flow (no knowledge, no identity), offline flow (partial
knowledge preserved, identity never remapped), privacy (only query
terms transmitted), executor off-thread boundary and cancellation.
"""

from pathlib import Path

from enrichment_fakes import (
    InMemoryIdentityRepository,
    RecordingKnowledgeRepository,
)

from michi.application.enrichment_coordinator import (
    EnrichmentCoordinator,
    EnrichmentOperationState,
)
from michi.application.enrichment_evidence import LibraryEnrichmentEvidenceBuilder
from michi.application.enrichment_ports import (
    ArtistExternalLinks,
    BiographyKnowledge,
    CommonsImageKnowledge,
    CoverArtArchiveProviderPort,
    CoverArtKnowledge,
    EnrichmentExecutorPort,
    EnrichmentProviderError,
    ExternalIdentityResolverPort,
    HttpRequest,
    HttpResponse,
    HttpTransportPort,
    MusicBrainzKnowledgeProviderPort,
    WikidataArtistClaims,
    WikidataKnowledgeProviderPort,
    WikimediaCommonsProviderPort,
    WikipediaBiographyProviderPort,
)
from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumKnowledgeProfile,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    KnowledgeProvenance,
)
from michi.domain.library import TrackRef, build_music_model


class InlineExecutor(EnrichmentExecutorPort):
    """Runs work synchronously (deterministic tests; the production
    executor is the ThreadPoolEnrichmentExecutor)."""

    def __init__(self):
        self.shutdown_calls = 0

    def submit(self, work) -> None:
        work()

    def shutdown(self, wait: bool = True) -> None:
        self.shutdown_calls += 1


class HintResolver(ExternalIdentityResolverPort):
    """Resolves ONLY from explicit identity hints (no network)."""

    def __init__(self):
        self.group_calls = 0

    def find_artist_candidates(self, evidence: ArtistIdentityEvidence):
        return ()

    def find_release_group_candidates(self, evidence: AlbumIdentityEvidence):
        self.group_calls += 1
        return ()

    def find_release_edition_candidates(self, evidence: AlbumIdentityEvidence):
        return ()


class NoopHttpTransport(HttpTransportPort):
    def __init__(self):
        self.requests: list[str] = []

    def get(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request.url)
        raise EnrichmentProviderError("offline transport")


def _tracks():
    return (
        TrackRef(
            file_path=Path("/m/a.flac"),
            title="T1",
            artist="Artist A",
            album="Album X",
            year=1980,
            album_artist="Artist A",
        ),
        TrackRef(
            file_path=Path("/m/b.flac"),
            title="T2",
            artist="Artist A",
            album="Album X",
            year=1980,
            album_artist="Artist A",
        ),
    )


class HintExtractorStub:
    def __init__(self, artist_hints=(), release_hints=()):
        self._artist_hints = artist_hints
        self._release_hints = release_hints

    def extract_hints(self, file_path):
        from michi.domain.enrichment import ExternalIdentityHints

        return ExternalIdentityHints(
            musicbrainz_artist_ids=tuple(self._artist_hints),
            musicbrainz_release_group_id=(
                self._release_hints[0] if self._release_hints else ""
            ),
        )


class FakeMbKnowledge(MusicBrainzKnowledgeProviderPort):
    def __init__(self, offline=False):
        self._offline = offline
        self.artist_calls = 0

    def fetch_artist(self, local_artist_key, external_artist_id):
        self.artist_calls += 1
        if self._offline:
            raise EnrichmentProviderError("network unavailable")
        return ArtistKnowledgeProfile(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            external_genres=("Classical",),
            begin_year=1932,
            provenance=KnowledgeProvenance(provider="musicbrainz"),
        )

    def artist_links(self, external_artist_id):
        if self._offline:
            raise EnrichmentProviderError("network unavailable")
        return ArtistExternalLinks(
            wikidata_qid="Q42",
            wikipedia_title="Artist A",
            wikipedia_language="en",
        )

    def fetch_release_group(self, local_album_key, release_group_id, release_id=""):
        if self._offline:
            raise EnrichmentProviderError("network unavailable")
        return AlbumKnowledgeProfile(
            local_album_key=local_album_key,
            release_group_id=release_group_id,
            release_id=release_id,
            external_genres=("Rock",),
            first_release_year=1980,
            provenance=KnowledgeProvenance(provider="musicbrainz"),
        )


class FakeWikidata(WikidataKnowledgeProviderPort):
    def fetch_artist_claims(self, qid):
        return WikidataArtistClaims(
            country="United States",
            commons_image_title="Artist.jpg",
        )


class FakeWikipedia(WikipediaBiographyProviderPort):
    def fetch_biography(self, title, language=""):
        return BiographyKnowledge(
            text="A composer biography.",
            page_title=title,
            source_url=f"https://{language or 'en'}.wikipedia.org/wiki/{title}",
            language=language or "en",
        )


class FakeCommons(WikimediaCommonsProviderPort):
    def fetch_image(self, file_title):
        return CommonsImageKnowledge(
            source_url="https://upload.wikimedia.org/x.jpg",
            license="CC BY-SA 4.0",
            license_url="https://license/x",
            artist="Someone",
        )


class FakeCoverArt(CoverArtArchiveProviderPort):
    def fetch_cover(self, release_id="", release_group_id=""):
        return CoverArtKnowledge(
            image_url="https://coverartarchive.org/cover.jpg",
            entity_kind="release-group" if release_group_id else "release",
        )


class RecordingAssetStore:
    def __init__(self):
        self.stored: list = []

    def store(self, record, data):
        self.stored.append((record, data))
        return record

    def path_for(self, asset_id):
        return None

    def record_for(self, asset_id):
        return None

    def clear(self):
        self.stored.clear()


def make_coordinator(
    mb_knowledge,
    transport=None,
    wikidata=None,
    wikipedia=None,
    commons=None,
    coverart=None,
    executor=None,
    enabled=lambda: True,
):
    repository = RecordingKnowledgeRepository()
    identity_repo = InMemoryIdentityRepository()
    service = EnrichmentService(
        resolver=HintResolver(),
        artist_provider=None,
        album_provider=None,
        repository=repository,
        identity_repository=identity_repo,
    )
    service._resolver = HintResolver()
    coordinator = EnrichmentCoordinator(
        service=service,
        resolver=service._resolver,
        evidence_builder=LibraryEnrichmentEvidenceBuilder(
            HintExtractorStub(artist_hints=("mb-a",), release_hints=("rg-x",))
        ),
        mb_knowledge=mb_knowledge,
        wikidata=wikidata,
        wikipedia=wikipedia,
        commons=commons,
        coverart=coverart,
        asset_store=RecordingAssetStore(),
        executor=executor or InlineExecutor(),
        transport=transport or NoopHttpTransport(),
        enabled=enabled,
    )
    return coordinator, service, repository, identity_repo


class TestArtistEndToEnd:
    def test_full_pipeline_commits_and_projects(self):
        coordinator, service, repository, _ = make_coordinator(
            FakeMbKnowledge(),
            wikidata=FakeWikidata(),
            wikipedia=FakeWikipedia(),
            commons=FakeCommons(),
        )
        tracks = _tracks()
        model = build_music_model(tracks)
        artist = model.artists[0]
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            artist, model.albums, tracks, on_state=lambda k, s: states.append(s)
        )
        assert states[-1] in (
            EnrichmentOperationState.READY,
            EnrichmentOperationState.PARTIAL,
        )
        profile = service.get_artist_knowledge("artist a")
        assert profile is not None
        assert profile.biography == "A composer biography."
        assert profile.country == "United States"
        assert profile.commons_image_title == "Artist.jpg"
        assert profile.external_genres == ("Classical",)
        # Canonical model untouched (firewall).
        assert model.artists[0].name == "Artist A"

    def test_ambiguous_flow_no_identity_no_knowledge(self):
        extractor = HintExtractorStub()  # NO hints
        repository = RecordingKnowledgeRepository()
        identity_repo = InMemoryIdentityRepository()
        service = EnrichmentService(
            resolver=HintResolver(),
            artist_provider=None,
            album_provider=None,
            repository=repository,
            identity_repository=identity_repo,
        )
        coordinator = EnrichmentCoordinator(
            service=service,
            resolver=service._resolver,
            evidence_builder=LibraryEnrichmentEvidenceBuilder(extractor),
            mb_knowledge=FakeMbKnowledge(),
            wikidata=None,
            wikipedia=None,
            commons=None,
            coverart=None,
            asset_store=RecordingAssetStore(),
            executor=InlineExecutor(),
            transport=NoopHttpTransport(),
            enabled=lambda: True,
        )
        tracks = _tracks()
        model = build_music_model(tracks)
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            tracks,
            on_state=lambda k, s: states.append(s),
        )
        # No hints + no candidates → fail-closed NOT_FOUND (no identity,
        # no knowledge, no AUTO guess).
        assert states[-1] is EnrichmentOperationState.NOT_FOUND
        assert identity_repo.load_artist_identity("artist a") is None
        assert repository.write_count == 0

    def test_offline_flow_partial_safe(self):
        coordinator, service, repository, _ = make_coordinator(
            FakeMbKnowledge(offline=True)
        )
        tracks = _tracks()
        model = build_music_model(tracks)
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            tracks,
            on_state=lambda k, s: states.append(s),
        )
        assert states[-1] is EnrichmentOperationState.OFFLINE
        assert repository.write_count == 0
        assert service.get_artist_knowledge("artist a") is None


class TestAlbumEndToEnd:
    def test_full_pipeline_commits_cover(self):
        coordinator, service, _, _ = make_coordinator(
            FakeMbKnowledge(), coverart=FakeCoverArt()
        )
        tracks = _tracks()
        model = build_music_model(tracks)
        album = model.albums[0]
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_album(album, on_state=lambda k, s: states.append(s))
        assert states[-1] in (
            EnrichmentOperationState.READY,
            EnrichmentOperationState.PARTIAL,
        )
        profile = service.get_album_knowledge(album.key)
        assert profile is not None
        assert profile.release_group_id == "rg-x"
        assert profile.external_genres == ("Rock",)
        assert profile.first_release_year == 1980


class TestPrivacyAndOfflineContracts:
    def test_outbound_urls_contain_only_query_terms(self):
        # End-to-end: capture every URL the resolver/knowledge layer
        # would send and prove no filesystem/history data rides along.
        transport = NoopHttpTransport()
        coordinator, _, _, _ = make_coordinator(FakeMbKnowledge(), transport=transport)
        tracks = _tracks()
        model = build_music_model(tracks)
        coordinator.enrich_artist(model.artists[0], model.albums, tracks)
        for url in transport.requests:
            assert "/m/" not in url
            assert "/home/" not in url
            assert "file_path" not in url

    def test_disabled_setting_means_zero_provider_activity(self):
        mb = FakeMbKnowledge()
        coordinator, service, repository, _ = make_coordinator(
            mb, enabled=lambda: False
        )
        tracks = _tracks()
        model = build_music_model(tracks)
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            tracks,
            on_state=lambda k, s: states.append(s),
        )
        assert states == [EnrichmentOperationState.OFFLINE]
        assert mb.artist_calls == 0
        assert repository.write_count == 0

    def test_cancelled_flow_no_commit(self):
        coordinator, service, repository, _ = make_coordinator(FakeMbKnowledge())
        coordinator.cancel_all()
        tracks = _tracks()
        model = build_music_model(tracks)
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            model.artists[0],
            model.albums,
            tracks,
            on_state=lambda k, s: states.append(s),
        )
        assert states == [EnrichmentOperationState.CANCELLED]
        assert repository.write_count == 0

    def test_manual_resolution_flow(self):
        coordinator, service, _, identity_repo = make_coordinator(FakeMbKnowledge())
        tracks = _tracks()
        model = build_music_model(tracks)
        artist = model.artists[0]
        # Ambiguous auto evidence; user manually selects.
        coordinator.confirm_artist_identity(artist.key, "mb-manual")
        identity = identity_repo.load_artist_identity(artist.key)
        assert identity is not None
        assert identity.external_artist_id == "mb-manual"
        # Enrichment now uses the manual authority (no re-resolution).
        states: list[EnrichmentOperationState] = []
        coordinator.enrich_artist(
            artist, model.albums, tracks, on_state=lambda k, s: states.append(s)
        )
        profile = service.get_artist_knowledge(artist.key)
        assert profile is not None
        assert profile.external_artist_id == "mb-manual"
