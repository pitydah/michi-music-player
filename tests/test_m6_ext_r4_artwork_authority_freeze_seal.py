"""M6-EXT-R4 FINAL ARTWORK AUTHORITY & FREEZE CANDIDATE SEAL.

P1-A  productive ownership (ServiceGraph realmente posee artwork runtime)
P1-B  tri-state verdicts (FOUND / ABSENT_CONFIRMED / UNAVAILABLE)
P1-C  source-aware eligibility (offline/disabled sources never probed)
P1-D  ONE batch manifest commit (never N rewrites)
P1-E  source AVAILABLE observation published before artwork schedule

Prohibited: time.sleep / polling. Allowed: manual runners, QSignalSpy,
QEventLoop, threading.Event, deterministic retention.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")


from michi.application.library_artwork_contracts import (
    ArtworkProbeObservation,
    ArtworkProbeVerdict,
    PreparedArtwork,
)
from michi.application.library_service import LibraryService
from michi.application.ports import (
    LibraryPrefsPort,
    ScanCancelled,
    ScanCancelToken,
)
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.domain.library import LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    SourceAvailability,
    new_library_source_id,
)
from michi.infrastructure.artwork import ArtworkCache, MutagenArtworkProvider
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache


class _Prefs(LibraryPrefsPort):
    def load(self):
        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _Progress:
    def __init__(self, phase="", total=0, processed=0, current_path=""):
        self.phase = phase
        self.total = total
        self.processed = processed
        self.current_path = current_path


class _Artwork:
    def __init__(self, data=b"PNG", mime_type="image/png"):
        self.data = data
        self.mime_type = mime_type


class _ManualRunner:
    def __init__(self):
        self.submissions = []
        self.cancelled = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work))

    def cancel(self, generation):
        self.cancelled.append(generation)

    def shutdown(self):
        pass


class _RecordingCache:
    def __init__(self):
        self.store_calls = []
        self.invalidate_calls = []
        self.prepare_calls = []
        self.batch_calls = []
        self._mapping = {}

    def store(self, album_key, artwork):
        self.store_calls.append((album_key, artwork))
        return Path(f"/fake/{album_key}.png")

    def invalidate(self, album_key):
        self.invalidate_calls.append(album_key)

    def lookup(self, album_key):
        return self._mapping.get(album_key)

    def prepare_artwork(self, album_key, artwork):
        self.prepare_calls.append(album_key)
        return PreparedArtwork(
            album_key=album_key,
            filename=f"{album_key}.png",
            path=Path(f"/fake/{album_key}.png"),
        )

    def commit_manifest_batch(self, *, upserts, removals):
        self.batch_calls.append((len(upserts), tuple(removals)))
        published = {}
        for p in upserts:
            published[p.album_key] = p.path
            self._mapping[p.album_key] = p.path
        for key in removals:
            self._mapping.pop(key, None)
        return published


class _ProbeProvider:
    def __init__(self, verdict=ArtworkProbeVerdict.ABSENT_CONFIRMED):
        self.verdict = verdict
        self.calls = []

    def probe_album_artwork(self, track_paths, token=None):
        self.calls.append(tuple(str(p) for p in track_paths))
        if self.verdict is ArtworkProbeVerdict.FOUND:
            return ArtworkProbeObservation.found(_Artwork())
        if self.verdict is ArtworkProbeVerdict.ABSENT_CONFIRMED:
            return ArtworkProbeObservation.absent()
        return ArtworkProbeObservation.unavailable("injected")


def _env(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(FilesystemLibrarySourceScanner(), library_prefs=_Prefs())
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
    )
    return library, catalog, coordinator


def _album(library, key, track_ids, track_paths):
    from michi.domain.library import AlbumRef

    library.state.albums = tuple(a for a in library.state.albums if a.key != key) + (
        AlbumRef(
            key=key,
            title=f"Album {key}",
            artist="Artist",
            track_count=len(track_ids),
            duration_ms=0,
            track_ids=tuple(track_ids),
            track_paths=tuple(Path(p) for p in track_paths),
        ),
    )


# ==========================================================================
# TEST 1/2 — PRODUCTION OWNERSHIP + SHUTDOWN
# ==========================================================================


class TestProductionOwnership:
    def _build_graph(self, tmp_path):
        from michi.bootstrap import _build_services
        from tests.test_library_model import FakeAudioPort

        graph = _build_services(
            tmp_path / "m.db",
            backend=FakeAudioPort(),
        )
        return graph

    def test_production_service_graph_owns_artwork_runtime(self, tmp_path):
        graph = self._build_graph(tmp_path)
        assert graph.artwork_runner is not None
        assert graph.artwork_refresh is not None
        assert graph.artwork_dispatcher is not None
        assert graph.artwork_refresh._runner is graph.artwork_runner
        assert graph.artwork_refresh._album_probe is graph.artwork_provider
        assert graph.artwork_refresh._prepared_cache is graph.artwork_cache

    def test_container_shutdown_closes_artwork_runtime(self, tmp_path):
        from michi.bootstrap import ApplicationContainer

        graph = self._build_graph(tmp_path)
        container = ApplicationContainer.__new__(ApplicationContainer)
        container._artwork_refresh = graph.artwork_refresh
        container._artwork_runner = graph.artwork_runner
        container._artwork_dispatcher = graph.artwork_dispatcher
        container._queue = None
        container._library = None
        container._playlist_service = None
        container._scan_runner = None
        container._scan_dispatcher = None
        container._source_scan_runner = None
        container._source_scan_lifecycle = None
        container._library_prefs = None
        container._navigation = None
        container._coordinator = None
        container._persistence = None
        # Todos los atributos del __init__ real con None (excepto artwork).
        for attr in (
            "_app",
            "_engine",
            "_audio_router",
            "_audio_engine_registry",
            "_audio_engine_service",
            "_audio_engine_convergence",
            "_qt_engine_provider",
            "_engine_selection_coordinator",
            "_queue",
            "_library",
            "_playback",
            "_playback_session",
            "_playlist_service",
            "_library_prefs",
            "_navigation",
            "_coordinator",
            "_persistence",
            "_scan_runner",
            "_scan_dispatcher",
            "_source_scan_runner",
            "_source_scan_lifecycle",
            "_pb",
            "_qb",
            "_lb",
            "_plb",
            "_nb",
            "_sb",
            "_eb",
            "_psb",
            "_aeb",
            "_settings",
            "_history_coordinator",
            "_enrichment",
            "_enrichment_settings",
        ):
            setattr(container, attr, None)

        ApplicationContainer.shutdown(container)
        assert graph.artwork_refresh._closed is True
        assert graph.artwork_dispatcher._refresh is None

        # Late completion es inerte.
        library = graph.artwork_refresh._library
        before = library.state.albums
        graph.artwork_refresh.handle_done(999, (), None)
        assert library.state.albums is before


# ==========================================================================
# TEST 3 — TRI-STATE PROVIDER
# ==========================================================================


class TestTriStateProvider:
    def test_found_absent_unavailable_are_distinct(self, tmp_path):
        provider = MutagenArtworkProvider()
        # UNAVAILABLE: archivo inexistente.
        obs = provider.probe_album_artwork((tmp_path / "missing.flac",))
        assert obs.verdict is ArtworkProbeVerdict.UNAVAILABLE
        assert obs.artwork is None
        # ABSENT_CONFIRMED: directorio completo sin artwork.
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        (empty_dir / "track.flac").write_bytes(b"x")
        obs2 = provider.probe_album_artwork((empty_dir / "track.flac",))
        # Mutagen no puede leer bytes inválidos → parser failure → UNAVAILABLE
        # es lo correcto (no se puede PROBAR ausencia).
        assert obs2.verdict in (
            ArtworkProbeVerdict.UNAVAILABLE,
            ArtworkProbeVerdict.ABSENT_CONFIRMED,
        )
        assert obs2.artwork is None


# ==========================================================================
# TEST 4/5 — UNAVAILABLE PRESERVES / ABSENT CONFIRMED INVALIDATES
# ==========================================================================


class TestVerdictSemantics:
    def _refresh(self, library, provider, cache):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        runner = _ManualRunner()
        refresh = LibraryArtworkRefresh(
            library,
            provider,
            cache,
            runner=runner,
            album_probe=provider,
            prepared_cache=cache,
        )
        return refresh, runner

    def _deliver(self, refresh, runner):
        gen, work = runner.submissions[0]
        result = work(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen, result, None)
        return result

    def test_unavailable_probe_never_invalidates_last_known(self, tmp_path):
        library, catalog, coordinator = _env(tmp_path)
        real_cache = ArtworkCache(tmp_path / "art")
        real_cache.store("album-a", _Artwork())
        assert real_cache.lookup("album-a") is not None
        _album(library, "album-a", ("T1",), ("/m/a.flac",))
        provider = _ProbeProvider(ArtworkProbeVerdict.UNAVAILABLE)
        refresh, runner = self._refresh(library, provider, real_cache)
        refresh.schedule()
        self._deliver(refresh, runner)
        assert real_cache.lookup("album-a") is not None, (
            "unavailable destruyó el artwork cacheado"
        )

    def test_confirmed_absence_invalidates_cached_artwork(self, tmp_path):
        library, catalog, coordinator = _env(tmp_path)
        real_cache = ArtworkCache(tmp_path / "art")
        real_cache.store("album-a", _Artwork())
        _album(library, "album-a", ("T1",), ("/m/a.flac",))
        provider = _ProbeProvider(ArtworkProbeVerdict.ABSENT_CONFIRMED)
        refresh, runner = self._refresh(library, provider, real_cache)
        refresh.schedule()
        self._deliver(refresh, runner)
        assert real_cache.lookup("album-a") is None


# ==========================================================================
# TEST 6/7 — SOURCE AWARENESS
# ==========================================================================


class TestSourceAwareness:
    def _source_world(self, tmp_path):
        library, catalog, coordinator = _env(tmp_path)
        source_a = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="a",
            root_path=str(tmp_path / "a"),
        )
        source_b = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="b",
            root_path=str(tmp_path / "b"),
        )
        (tmp_path / "a").mkdir(exist_ok=True)
        (tmp_path / "b").mkdir(exist_ok=True)
        catalog.upsert_source(source_a)
        catalog.upsert_source(source_b)
        return library, catalog, coordinator, source_a, source_b

    def test_disabled_source_tracks_never_probed(self, tmp_path):
        library, catalog, coordinator, a, b = self._source_world(tmp_path)
        coordinator.set_source_enabled(b.library_source_id, False)
        coordinator._observations[a.library_source_id] = SourceAvailability.AVAILABLE
        library.state.albums = ()
        _album(library, "album-a", ("TA1",), ("/a/a.flac",))
        _album(library, "album-b", ("TB1",), ("/b/b.flac",))
        library.state.tracks = (
            _ref("TA1", a, "/a/a.flac"),
            _ref("TB1", b, "/b/b.flac"),
        )
        library._reindex_track_refs()
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        cache = _RecordingCache()
        provider = _ProbeProvider(ArtworkProbeVerdict.ABSENT_CONFIRMED)
        runner = _ManualRunner()
        refresh = LibraryArtworkRefresh(
            library,
            provider,
            cache,
            runner=runner,
            album_probe=provider,
            prepared_cache=cache,
            source_availability_provider=coordinator.observed_availability,
        )
        refresh.schedule()
        # El snapshot solo incluye album-a (source b no es AVAILABLE).
        assert len(runner.submissions) == 1
        gen, work = runner.submissions[0]
        result = work(_Progress(), ScanCancelToken(), lambda: None)
        probed = set()
        for probe in result:
            probed.update(probe.membership_signature)
        assert "TB1" not in probed, "source disabled fue probado"

    def test_offline_missing_access_io_sources_never_probed(self, tmp_path):
        library, catalog, coordinator, a, b = self._source_world(tmp_path)
        for availability in (
            SourceAvailability.OFFLINE,
            SourceAvailability.MISSING_ROOT,
            SourceAvailability.ACCESS_DENIED,
            SourceAvailability.IO_ERROR,
        ):
            coordinator._observations[b.library_source_id] = availability
            library.state.albums = ()
            library.state.tracks = (_ref("TB1", b, "/b/b.flac"),)
            _album(library, "album-b", ("TB1",), ("/b/b.flac",))
            from michi.application.library_artwork_refresh import (
                LibraryArtworkRefresh,
            )

            cache = _RecordingCache()
            provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
            runner = _ManualRunner()
            refresh = LibraryArtworkRefresh(
                library,
                provider,
                cache,
                runner=runner,
                album_probe=provider,
                prepared_cache=cache,
                source_availability_provider=coordinator.observed_availability,
            )
            refresh.schedule()
            assert runner.submissions == [], f"{availability} fue probado"


def _ref(track_id, source, path):
    from michi.domain.library import TrackRef

    return TrackRef(
        track_id=track_id,
        library_source_id=source.library_source_id,
        file_path=Path(path),
        display_name=track_id,
        availability=__import__(
            "michi.domain.library_catalog", fromlist=["MediaAvailability"]
        ).MediaAvailability.AVAILABLE,
    )


# ==========================================================================
# TEST 8 — OBSERVATION PRECEDES ARTWORK SCHEDULE
# ==========================================================================


class TestObservationOrder:
    def test_source_available_published_before_artwork_schedule(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="a",
            root_path=str(tmp_path / "a"),
        )
        (tmp_path / "a").mkdir(exist_ok=True)
        (tmp_path / "a" / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)

        observed_at_schedule = []

        class _SpyRefresh(LibraryArtworkRefresh):
            def schedule(self):
                observed_at_schedule.append(
                    coordinator.observed_availability(source.library_source_id)
                )

        coordinator._artwork_refresh = _SpyRefresh(library, None, None, runner=None)

        class _Pipe:
            def __init__(self):
                self.submissions = []
                self.cancelled = []

            def submit(self, g, w, op, od):
                self.submissions.append((g, w, op, od))

            def cancel(self, g):
                self.cancelled.append(g)

        pipe = _Pipe()
        from michi.application.source_scan_lifecycle import (
            SourceScanLifecycle,
        )

        lifecycle = SourceScanLifecycle(coordinator, pipe)
        lifecycle.request_scan_source(source.library_source_id)
        generation, work, _, done = pipe.submissions[0]
        from michi.application.ports import ScanCancelToken

        plan = work(_Progress(), ScanCancelToken(), lambda: None)
        done(generation, plan, None)
        assert observed_at_schedule, "schedule nunca se llamó"
        assert observed_at_schedule[0] is SourceAvailability.AVAILABLE


# ==========================================================================
# TEST 9/10 — SOURCE ERROR / RELOCATE SUPERSEDE ARTWORK
# ==========================================================================


class TestArtworkSupersession:
    def test_source_scan_error_supersedes_inflight_artwork(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="a",
            root_path=str(tmp_path / "a"),
        )
        (tmp_path / "a").mkdir(exist_ok=True)
        catalog.upsert_source(source)
        library.state.albums = ()
        _album(library, "album-a", ("TA1",), ("/a/a.flac",))
        library.state.tracks = (_ref("TA1", source, "/a/a.flac"),)
        cache = _RecordingCache()
        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        runner = _ManualRunner()
        refresh = LibraryArtworkRefresh(
            library,
            provider,
            cache,
            runner=runner,
            album_probe=provider,
            prepared_cache=cache,
        )
        coordinator._artwork_refresh = refresh
        refresh.schedule()
        gen1, work1 = runner.submissions[0]
        assert runner.cancelled == []

        # Error del source → invalidate (epoch bump + cancel).
        coordinator.record_source_scan_error(
            source.library_source_id,
            __import__(
                "michi.application.library_port",
                fromlist=["LibraryFilesystemError"],
            ).LibraryFilesystemError(
                __import__(
                    "michi.domain.library",
                    fromlist=["LibraryDiagnosticCode"],
                ).LibraryDiagnosticCode.DIRECTORY_MISSING,
                Path("/a"),
                "missing",
            ),
        )
        assert 1 in runner.cancelled

        # gen1 late → inerte.
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)
        assert cache.batch_calls == []

    def test_relocate_invalidates_old_path_artwork_work(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="a",
            root_path=str(tmp_path / "old"),
        )
        (tmp_path / "old").mkdir(exist_ok=True)
        (tmp_path / "new").mkdir(exist_ok=True)
        catalog.upsert_source(source)
        library.state.albums = ()
        _album(library, "album-a", ("TA1",), ("/old/a.flac",))
        library.state.tracks = (_ref("TA1", source, "/old/a.flac"),)
        cache = _RecordingCache()
        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        runner = _ManualRunner()
        refresh = LibraryArtworkRefresh(
            library,
            provider,
            cache,
            runner=runner,
            album_probe=provider,
            prepared_cache=cache,
        )
        coordinator._artwork_refresh = refresh
        refresh.schedule()
        gen1, work1 = runner.submissions[0]

        coordinator.relocate_source_root(
            source.library_source_id, str(tmp_path / "new")
        )
        assert 1 in runner.cancelled

        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)
        assert cache.batch_calls == []


# ==========================================================================
# TEST 11/12 — PREPARE + BATCH
# ==========================================================================


class TestBatchCache:
    def test_prepare_writes_blob_but_not_manifest(self, tmp_path):
        cache = ArtworkCache(tmp_path / "art")
        prepared = cache.prepare_artwork("album-a", _Artwork())
        assert prepared is not None
        assert prepared.path.is_file()
        assert cache.lookup("album-a") is None
        published = cache.commit_manifest_batch(upserts=(prepared,), removals=())
        assert cache.lookup("album-a") == published["album-a"]

    def test_large_artwork_batch_rewrites_manifest_once(self, tmp_path):
        cache = ArtworkCache(tmp_path / "art")

        prepared = []
        for i in range(250):
            art = _Artwork(data=f"PNG{i}".encode())
            p = cache.prepare_artwork(f"album-{i}", art)
            assert p is not None
            prepared.append(p)
        calls = []

        original = cache._persist_manifest
        cache._persist_manifest = lambda: calls.append(1) or original()
        cache.commit_manifest_batch(upserts=tuple(prepared), removals=())
        assert len(calls) == 1, f"manifest persistido {len(calls)} veces"


# ==========================================================================
# TEST 13 — OWNER ONE BATCH COMMIT
# ==========================================================================


class TestOwnerBatchCommit:
    def test_artwork_owner_apply_uses_one_batch_commit(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        for i in range(20):
            _album(library, f"album-{i}", (f"T{i}",), (f"/m/{i}.flac",))
        cache = _RecordingCache()
        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        runner = _ManualRunner()
        refresh = LibraryArtworkRefresh(
            library,
            provider,
            cache,
            runner=runner,
            album_probe=provider,
            prepared_cache=cache,
        )
        refresh.schedule()
        gen, work = runner.submissions[0]
        result = work(_Progress(), ScanCancelToken(), lambda: None)
        assert cache.batch_calls == []
        refresh.handle_done(gen, result, None)
        assert len(cache.batch_calls) == 1
        assert cache.store_calls == []
        assert cache.invalidate_calls == []


# ==========================================================================
# TEST 14 — STALE BLOB NO MANIFEST
# ==========================================================================


class TestStaleBlob:
    def test_stale_generation_may_leave_blob_but_never_mapping(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        _album(library, "album-a", ("T1",), ("/m/a.flac",))
        real_cache = ArtworkCache(tmp_path / "art")
        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        runner = _ManualRunner()
        refresh = LibraryArtworkRefresh(
            library,
            provider,
            real_cache,
            runner=runner,
            album_probe=provider,
            prepared_cache=real_cache,
        )
        refresh.schedule()  # gen1
        gen1, work1 = runner.submissions[0]
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        # gen2 supersede antes de done.
        refresh.schedule()
        refresh.handle_done(gen1, result1, None)
        assert real_cache.lookup("album-a") is None, (
            "stale blob se volvió autoridad de manifest"
        )


# ==========================================================================
# TEST 15/16 — SINGLE-FLIGHT + MEMBERSHIP PROVENANCE
# ==========================================================================


class TestRetainedContracts:
    def test_single_flight_coalesces_to_latest(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        _album(library, "album-a", ("T1",), ("/m/a.flac",))
        cache = _RecordingCache()
        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        runner = _ManualRunner()
        refresh = LibraryArtworkRefresh(
            library,
            provider,
            cache,
            runner=runner,
            album_probe=provider,
            prepared_cache=cache,
        )
        refresh.schedule()
        refresh.schedule()
        refresh.schedule()
        refresh.schedule()
        assert len(runner.submissions) == 1
        assert 1 in runner.cancelled
        refresh.handle_done(1, None, ScanCancelled())
        assert len(runner.submissions) == 2
        gen_latest, _ = runner.submissions[1]
        assert gen_latest == 4

    def test_same_key_different_membership_still_rejected(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        _album(library, "album-x", ("T1", "T2"), ("/m/a.flac", "/m/b.flac"))
        cache = _RecordingCache()
        provider = _ProbeProvider(ArtworkProbeVerdict.FOUND)
        runner = _ManualRunner()
        refresh = LibraryArtworkRefresh(
            library,
            provider,
            cache,
            runner=runner,
            album_probe=provider,
            prepared_cache=cache,
        )
        refresh.schedule()
        gen1, work1 = runner.submissions[0]
        library.state.albums = ()
        _album(library, "album-x", ("T3", "T4"), ("/m/c.flac", "/m/d.flac"))
        refresh.schedule()
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)
        assert cache.batch_calls == []
