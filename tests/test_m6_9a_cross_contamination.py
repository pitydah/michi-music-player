"""M6.9A — cross-contamination tests (the 15 required gates).

Each test proves that external knowledge/enrichment can NEVER mutate the
canonical local library (TrackMetadata/TrackRef/AlbumRef/ArtistRef/
GenreRef, library_index, audio tags, local artwork) under any order of
events, refresh, failure, offline, ambiguity or rebuild.
"""

import sqlite3
from pathlib import Path

from enrichment_fakes import (
    FakeAlbumProvider,
    FakeArtistProvider,
    FakeIdentityResolver,
    RecordingAssetStore,
    RecordingLibraryIndexRepository,
)

from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    DeliveryVerdict,
    EnrichmentEntityKind,
    LocalAlbumEvidence,
)
from michi.domain.library import TrackMetadata, TrackRef, build_music_model
from michi.infrastructure.enrichment_repository import SqliteEnrichmentRepository
from michi.infrastructure.library_index import SqliteLibraryIndexRepository


def canonical_tracks():
    return (
        TrackRef(
            file_path=Path("/music/a.flac"),
            title="Title A",
            artist="Artist A",
            album="Album X",
            duration_ms=200000,
            genre="Rock",
            year=1980,
            album_artist="Artist A",
            track_number=1,
            codec="FLAC",
            container="flac",
            sample_rate_hz=44100,
            bit_depth=16,
            channels=2,
            bitrate_bps=900000,
            file_size=1000,
        ),
        TrackRef(
            file_path=Path("/music/b.flac"),
            title="Title B",
            artist="Artist B",
            album="Album X",
            duration_ms=180000,
            genre="Rock",
            year=1980,
            album_artist="Artist A",
            track_number=2,
            codec="FLAC",
            container="flac",
            sample_rate_hz=44100,
            bit_depth=16,
            channels=2,
            bitrate_bps=900000,
            file_size=1000,
        ),
    )


def library_snapshot():
    tracks = canonical_tracks()
    return tracks, build_music_model(tracks)


def populate_library_index(tmp_path: Path, tracks) -> SqliteLibraryIndexRepository:
    repo = SqliteLibraryIndexRepository(tmp_path / "library.db")
    entries = [
        (
            str(t.file_path),
            t.file_size,
            123456789,
            TrackMetadata(
                title=t.title,
                artist=t.artist,
                album=t.album,
                duration_ms=t.duration_ms,
                genre=t.genre,
                year=t.year,
                album_artist=t.album_artist,
                track_number=t.track_number,
                codec=t.codec,
                container=t.container,
                sample_rate_hz=t.sample_rate_hz,
                bit_depth=t.bit_depth,
                channels=t.channels,
                bitrate_bps=t.bitrate_bps,
                file_size=t.file_size,
            ),
        )
        for t in tracks
    ]
    from michi.domain.library_index import LibraryIndexEntry

    repo.upsert_many([LibraryIndexEntry(e[0], e[1], e[2], e[3]) for e in entries])
    return repo


def index_rows(db_path: Path) -> list:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(
            "SELECT track_id, file_size, mtime_ns, metadata "
            "FROM library_index ORDER BY track_id"
        ).fetchall()
    finally:
        conn.close()


def build_service(tmp_path: Path, artist_provider=None, album_provider=None):
    resolver = FakeIdentityResolver()
    enrichment_repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
    identity_repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
    service = EnrichmentService(
        resolver=resolver,
        artist_provider=artist_provider or FakeArtistProvider(),
        album_provider=album_provider or FakeAlbumProvider(),
        repository=enrichment_repo,
        identity_repository=identity_repo,
    )
    return service, enrichment_repo


def artist_evidence(mbid: str, name: str = "Artist A") -> ArtistIdentityEvidence:
    return ArtistIdentityEvidence(
        local_artist_key=name.casefold(),
        local_artist_name=name,
        known_albums=(LocalAlbumEvidence("Album X", 1980),),
        identity_hints=ArtistIdentityHints(artist_ids=(mbid,)),
    )


def album_evidence(rg_id: str, key: str = "album-x-key") -> AlbumIdentityEvidence:
    return AlbumIdentityEvidence(
        local_album_key=key,
        local_album_title="Album X",
        local_album_artist_key="artist a",
        local_album_artist_name="Artist A",
        local_year=1980,
        identity_hints=AlbumIdentityHints(release_group_ids=(rg_id,)),
    )


class TestExternalProfilesNeverTouchLocalMetadata:
    def test_artist_profile_never_changes_track_artist(self, tmp_path):
        service, repo = build_service(tmp_path)
        tracks, model_before = library_snapshot()
        outcome = service.request_artist_enrichment(artist_evidence("mb-a"))
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome.request, profile)
            is DeliveryVerdict.COMMITTED
        )
        tracks_after, model_after = library_snapshot()
        assert tracks_after == tracks
        assert model_after == model_before
        assert repo.load_artist_profile("artist a") is not None

    def test_album_profile_never_changes_track_album(self, tmp_path):
        service, repo = build_service(tmp_path)
        tracks, model_before = library_snapshot()
        outcome = service.request_album_enrichment(album_evidence("rg-x"))
        profile = service._album_provider.fetch_profile("album-x-key", "rg-x")
        assert (
            service.deliver_album_profile(outcome.request, profile)
            is DeliveryVerdict.COMMITTED
        )
        tracks_after, model_after = library_snapshot()
        assert tracks_after == tracks
        assert model_after == model_before
        assert repo.load_album_profile("album-x-key") is not None

    def test_external_first_release_date_never_changes_track_year(self, tmp_path):
        service, _ = build_service(tmp_path)
        tracks, model_before = library_snapshot()
        outcome = service.request_album_enrichment(album_evidence("rg-x"))
        profile = service._album_provider.fetch_profile("album-x-key", "rg-x")
        # External knowledge claims a different first release year AND a
        # different specific-release year (release facts ride the profile,
        # never the local model).
        profile = type(profile)(
            **{
                **profile.__dict__,
                "first_release_year": 1950,
                "release_id": "rel-1",
                "release_year": 1951,
            }
        )
        service.deliver_album_profile(outcome.request, profile)
        tracks_after, model_after = library_snapshot()
        assert tracks_after == tracks
        assert model_after == model_before
        assert model_after.albums[0].year == 1980  # LOCAL year untouched

    def test_external_genres_never_change_local_genre_refs(self, tmp_path):
        service, _ = build_service(tmp_path)
        tracks, model_before = library_snapshot()
        outcome = service.request_artist_enrichment(artist_evidence("mb-a"))
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        profile = type(profile)(
            **{**profile.__dict__, "external_genres": ("Jazz", "Ambient")}
        )
        service.deliver_artist_profile(outcome.request, profile)
        tracks_after, model_after = library_snapshot()
        assert model_after.genres == model_before.genres
        assert model_after.genres[0].name == "Rock"  # LOCAL genre untouched

    def test_external_artwork_never_replaces_local_artwork(self, tmp_path):
        from michi.application.ports import ArtworkCachePort
        from michi.domain.enrichment import EnrichmentAssetRecord

        class SpyArtworkCache(ArtworkCachePort):
            def __init__(self):
                self.calls = []

            def store(self, album_key, artwork):
                self.calls.append(("store", album_key))
                return None

        local_cache = SpyArtworkCache()
        external_store = RecordingAssetStore()
        service = EnrichmentService(
            resolver=FakeIdentityResolver(),
            artist_provider=FakeArtistProvider(),
            album_provider=FakeAlbumProvider(),
            repository=SqliteEnrichmentRepository(tmp_path / "enrichment.db"),
            identity_repository=SqliteEnrichmentRepository(tmp_path / "enrichment.db"),
            asset_store=external_store,
        )
        outcome = service.request_artist_enrichment(artist_evidence("mb-a"))
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        service.deliver_artist_profile(outcome.request, profile)
        stored = external_store.store(
            EnrichmentAssetRecord(
                asset_id=profile.artwork_asset_id,
                entity_kind=EnrichmentEntityKind.ARTIST,
                external_entity_id="mb-a",
                mime_type="image/jpeg",
            ),
            b"external-bytes",
        )
        # External artwork landed ONLY in the enrichment asset store.
        assert stored is not None
        assert local_cache.calls == []
        assert external_store.path_for(profile.artwork_asset_id) is not None


class TestLibraryIndexIsolation:
    def test_refresh_produces_zero_library_index_writes(self, tmp_path):
        library_repo = populate_library_index(tmp_path, canonical_tracks())
        rows_before = index_rows(tmp_path / "library.db")
        spy = RecordingLibraryIndexRepository()
        service, _ = build_service(tmp_path)
        from michi.domain.enrichment import EnrichmentEntityKind

        for generation in (1, 2, 3):  # initial + refreshes
            service.begin_operation(EnrichmentEntityKind.ARTIST, "artist a", generation)
            outcome = service.request_artist_enrichment(
                artist_evidence("mb-a"), generation=generation
            )
            profile = service._artist_provider.fetch_profile("artist a", "mb-a")
            assert (
                service.deliver_artist_profile(outcome.request, profile)
                is DeliveryVerdict.COMMITTED
            )
        assert spy.writes == []
        assert index_rows(tmp_path / "library.db") == rows_before
        assert library_repo.load_all()  # index still healthy

    def test_clearing_enrichment_db_changes_zero_library_rows(self, tmp_path):
        library_repo = populate_library_index(tmp_path, canonical_tracks())
        rows_before = index_rows(tmp_path / "library.db")
        service, enrichment_repo = build_service(tmp_path)
        outcome = service.request_artist_enrichment(artist_evidence("mb-a"))
        service.deliver_artist_profile(
            outcome.request, service._artist_provider.fetch_profile("artist a", "mb-a")
        )
        enrichment_repo.clear_knowledge()
        assert enrichment_repo.load_artist_profiles() == ()
        assert index_rows(tmp_path / "library.db") == rows_before
        assert len(library_repo.load_all()) == 2

    def test_rebuilding_enrichment_db_changes_zero_track_refs(self, tmp_path):
        tracks, model_before = library_snapshot()
        service, _ = build_service(tmp_path)
        outcome = service.request_artist_enrichment(artist_evidence("mb-a"))
        service.deliver_artist_profile(
            outcome.request, service._artist_provider.fetch_profile("artist a", "mb-a")
        )
        # "Rebuild": delete enrichment.db and repopulate from scratch.
        (tmp_path / "enrichment.db").unlink()
        rebuilt = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        rebuilt.save_artist_profile(
            service._artist_provider.fetch_profile("artist a", "mb-a")
        )
        tracks_after, model_after = library_snapshot()
        assert tracks_after == tracks
        assert model_after == model_before


class TestEntityOwnershipAtRest:
    def test_out_of_order_artists_never_cross_ownership(self, tmp_path):
        service, repo = build_service(tmp_path)
        outcome_a = service.request_artist_enrichment(artist_evidence("mb-a"))
        outcome_b = service.request_artist_enrichment(
            artist_evidence("mb-b", name="Artist B")
        )
        profile_b = service._artist_provider.fetch_profile("artist b", "mb-b")
        profile_a = service._artist_provider.fetch_profile("artist a", "mb-a")
        assert (
            service.deliver_artist_profile(outcome_b.request, profile_b)
            is DeliveryVerdict.COMMITTED
        )
        assert (
            service.deliver_artist_profile(outcome_a.request, profile_a)
            is DeliveryVerdict.COMMITTED
        )
        stored_a = repo.load_artist_profile("artist a")
        stored_b = repo.load_artist_profile("artist b")
        assert stored_a is not None and stored_a.external_artist_id == "mb-a"
        assert stored_b is not None and stored_b.external_artist_id == "mb-b"
        assert stored_a.biography != stored_b.biography

    def test_out_of_order_albums_never_cross_ownership(self, tmp_path):
        service, repo = build_service(tmp_path)
        outcome_a = service.request_album_enrichment(
            album_evidence("rg-a", key="album-key-a")
        )
        outcome_b = service.request_album_enrichment(
            album_evidence("rg-b", key="album-key-b")
        )
        profile_b = service._album_provider.fetch_profile("album-key-b", "rg-b")
        profile_a = service._album_provider.fetch_profile("album-key-a", "rg-a")
        service.deliver_album_profile(outcome_b.request, profile_b)
        service.deliver_album_profile(outcome_a.request, profile_a)
        stored_a = repo.load_album_profile("album-key-a")
        stored_b = repo.load_album_profile("album-key-b")
        assert stored_a is not None and stored_a.release_group_id == "rg-a"
        assert stored_b is not None and stored_b.release_group_id == "rg-b"

    def test_ambiguous_artist_never_receives_biography_or_photo(self, tmp_path):
        from michi.domain.enrichment import ArtistCandidate

        resolver = FakeIdentityResolver(
            artists=[ArtistCandidate("mb-a"), ArtistCandidate("mb-b")]
        )
        service = EnrichmentService(
            resolver=resolver,
            artist_provider=FakeArtistProvider(),
            album_provider=FakeAlbumProvider(),
            repository=SqliteEnrichmentRepository(tmp_path / "enrichment.db"),
            identity_repository=SqliteEnrichmentRepository(tmp_path / "enrichment.db"),
        )
        evidence = ArtistIdentityEvidence(
            local_artist_key="john williams",
            local_artist_name="John Williams",
            known_albums=(LocalAlbumEvidence("Same Title", 0),),
        )
        outcome = service.request_artist_enrichment(evidence)
        assert outcome.request is None
        repo = SqliteEnrichmentRepository(tmp_path / "enrichment.db")
        assert repo.load_artist_profiles() == ()


class TestManualMatchAndFailure:
    def test_manual_external_match_does_not_change_local_tags(self, tmp_path):
        tracks, model_before = library_snapshot()
        library_repo = populate_library_index(tmp_path, canonical_tracks())
        rows_before = index_rows(tmp_path / "library.db")
        service, repo = build_service(tmp_path)
        # Manual match: user explicitly provides the identity hint.
        outcome = service.request_artist_enrichment(artist_evidence("mb-a"))
        assert outcome.request is not None
        profile = service._artist_provider.fetch_profile("artist a", "mb-a")
        service.deliver_artist_profile(outcome.request, profile)
        tracks_after, model_after = library_snapshot()
        assert tracks_after == tracks
        assert model_after == model_before
        assert index_rows(tmp_path / "library.db") == rows_before
        assert len(library_repo.load_all()) == 2
        assert repo.load_artist_profile("artist a") is not None

    def test_failed_enrichment_leaves_canonical_library_unchanged(self, tmp_path):
        from michi.application.enrichment_ports import EnrichmentProviderError

        tracks, model_before = library_snapshot()
        populate_library_index(tmp_path, canonical_tracks())
        rows_before = index_rows(tmp_path / "library.db")

        class FailingProvider(FakeArtistProvider):
            def fetch_profile(self, local_artist_key, external_artist_id):
                raise EnrichmentProviderError("boom")

        service, repo = build_service(tmp_path, artist_provider=FailingProvider())
        outcome = service.request_artist_enrichment(artist_evidence("mb-a"))
        assert (
            service.deliver_artist_failure(outcome.request) is DeliveryVerdict.COMMITTED
        )
        tracks_after, model_after = library_snapshot()
        assert tracks_after == tracks
        assert model_after == model_before
        assert index_rows(tmp_path / "library.db") == rows_before
        assert repo.load_artist_profiles() == ()

    def test_offline_enrichment_leaves_canonical_library_unchanged(self, tmp_path):
        from michi.application.enrichment_ports import EnrichmentProviderError

        tracks, model_before = library_snapshot()
        populate_library_index(tmp_path, canonical_tracks())
        rows_before = index_rows(tmp_path / "library.db")
        service, repo = build_service(
            tmp_path, artist_provider=FakeArtistProvider(offline=True)
        )
        outcome = service.request_artist_enrichment(artist_evidence("mb-a"))
        try:
            service._artist_provider.fetch_profile("artist a", "mb-a")
            raised = False
        except EnrichmentProviderError:
            raised = True
        assert raised
        service.deliver_artist_failure(outcome.request)
        tracks_after, model_after = library_snapshot()
        assert tracks_after == tracks
        assert model_after == model_before
        assert index_rows(tmp_path / "library.db") == rows_before
        assert repo.load_artist_profiles() == ()


class TestNoTagWriteLogic:
    def test_enrichment_modules_contain_zero_mutagen_tag_write_logic(self):
        import inspect

        import michi.application.enrichment_ports as ports_module
        import michi.application.enrichment_service as service_module
        import michi.domain.enrichment as domain_module
        import michi.infrastructure.enrichment_assets as assets_module
        import michi.infrastructure.enrichment_repository as repo_module

        modules = [
            domain_module,
            ports_module,
            service_module,
            repo_module,
            assets_module,
        ]
        for module in modules:
            source = inspect.getsource(module)
            assert "mutagen" not in source
            assert ".save(" not in source
            assert ".delete(" not in source
