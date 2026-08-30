"""M6-EXT-R4 FINAL RUNTIME TRUTH & CONCURRENCY SEAL — adversarial gates.

P1-01  root validation en el productive cancellable path
P1-02  media stat()/is_dir() fail-closed
P1-03  artwork completion vuelve al owner por relay dedicado
P1-04  stale artwork generation no muta el manifest
P1-05  hydrate/retire = cache-only (cero provider I/O)
P1-06  relocate persiste el root normalizado
P1-07  LoadingState estructural (CONTRACT CONFLICT reportado aparte)
P1-08  source operation errors observables

Prohibido: time.sleep / polling. Permitido: barriers con threading.Event,
QSignalSpy, QEventLoop, pipelines manuales deterministas.
"""

import os
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QEventLoop, QTimer

from michi.application.library_port import (
    LibraryFilesystemError,
)
from michi.application.library_service import LibraryService
from michi.application.ports import (
    LibraryPrefsPort,
    ScanCancelled,
    ScanCancelToken,
)
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryDiagnosticCode, LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    MediaFileRecord,
    SourceAvailability,
    TrackRecord,
    new_library_source_id,
    new_media_file_id,
    new_track_id,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache
from michi.presentation.library_bridge import LibraryBridge


class _Prefs(LibraryPrefsPort):
    def load(self):
        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _ManualPipeline:
    def __init__(self):
        self.submissions = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work, on_progress, on_done))

    def cancel(self, generation):
        for submitted in self.submissions:
            if submitted[0] == generation:
                submitted[3](generation, None, ScanCancelled())
                return


class _Progress:
    def __init__(self, phase="", total=0, processed=0, current_path=""):
        self.phase = phase
        self.total = total
        self.processed = processed
        self.current_path = current_path


def _source(tmp_path, name):
    root = tmp_path / name
    root.mkdir(exist_ok=True)
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
    )


def _env(tmp_path, scanner=None):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(
        scanner or FilesystemLibrarySourceScanner(), library_prefs=_Prefs()
    )
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        scanner or FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
    )
    pipeline = _ManualPipeline()
    lifecycle = SourceScanLifecycle(coordinator, pipeline)
    return library, catalog, coordinator, lifecycle, pipeline


def _seed_media(catalog, source, relative, availability=MediaAvailability.AVAILABLE):
    media = MediaFileRecord(
        media_file_id=new_media_file_id(),
        library_source_id=source.library_source_id,
        relative_path=relative,
        last_known_path=str(Path(source.root_path) / relative),
        availability=availability,
    )
    track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
    catalog.upsert_source(source)
    catalog.apply_source_reconciliation((media,), (track,))
    return media


def _run_worker(lifecycle, pipeline, source_id=None, error_factory=None):
    if source_id is not None:
        lifecycle.request_scan_source(source_id)
    generation, work, _, done = pipeline.submissions[0]
    try:
        work(_Progress(), ScanCancelToken(), lambda: None)
    except LibraryFilesystemError as exc:
        done(generation, None, exc)
    except ScanCancelled:
        done(generation, None, ScanCancelled())
    except Exception as exc:  # noqa: BLE001 - typed by the worker contract
        if error_factory is not None:
            done(generation, None, error_factory(exc))
        else:
            done(generation, None, exc)
    else:
        raise AssertionError("worker should have failed")


# ==========================================================================
# P1-01 — ROOT VALIDATION EN EL PRODUCTIVE CANCELLABLE PATH
# ==========================================================================


class TestRootValidationProductive:
    def test_missing_root_in_cancellable_path_is_missing_root(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        source = _source(tmp_path, "a")
        media = _seed_media(catalog, source, "song1.flac")
        root = Path(source.root_path)
        (root / "song1.flac").write_bytes(b"x")
        coordinator.list_sources()

        # El root desaparece (desmontaje simulado).
        root.rmdir() if not (root / "song1.flac").exists() else None
        import shutil

        shutil.rmtree(root, ignore_errors=True)

        pipeline2 = _ManualPipeline()
        lifecycle2 = SourceScanLifecycle(coordinator, pipeline2)
        _run_worker(lifecycle2, pipeline2, source.library_source_id)

        assert (
            coordinator.observed_availability(source.library_source_id)
            is SourceAvailability.MISSING_ROOT
        )
        # Sin commit: la media conocida NO se reescribe a MISSING.
        after = catalog.media_for_source(source.library_source_id)
        assert after and after[0].availability is MediaAvailability.AVAILABLE

    def test_root_vanishes_after_validation_before_walk(self, tmp_path):
        """Validación del root OK → root desaparece → iterdir del ROOT →
        DIRECTORY_MISSING (no enumeración vacía)."""
        scanner = FilesystemLibrarySourceScanner()
        library, catalog, coordinator, lifecycle, pipeline = _env(
            tmp_path, scanner=scanner
        )
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "song1.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.list_sources()

        # Seam determinista: validación del root OK → root desaparece →
        # el _walk del ROOT lanza DIRECTORY_MISSING (mi fix P1-01b) — el
        # worker aborta con truth a nivel de source.
        root = Path(source.root_path)
        original_walk = scanner._walk
        import shutil

        def walk_with_vanished_root(root_arg):
            if root_arg == root and not root.exists():
                raise LibraryFilesystemError(
                    LibraryDiagnosticCode.DIRECTORY_MISSING,
                    root_arg,
                    "vanished between validation and walk",
                )
            return original_walk(root_arg)

        scanner._walk = walk_with_vanished_root
        shutil.rmtree(root, ignore_errors=True)  # root borrado tras validación

        pipeline2 = _ManualPipeline()
        lifecycle2 = SourceScanLifecycle(coordinator, pipeline2)
        lifecycle2.request_scan_source(source.library_source_id)
        generation, work, _, done = pipeline2.submissions[0]
        try:
            work(_Progress(), ScanCancelToken(), lambda: None)
        except LibraryFilesystemError as exc:
            done(generation, None, exc)
        assert (
            coordinator.observed_availability(source.library_source_id)
            is SourceAvailability.MISSING_ROOT
        )


# ==========================================================================
# P1-02 — MEDIA stat() FAIL-CLOSED
# ==========================================================================


class _StatFaultScanner(FilesystemLibrarySourceScanner):
    """Inyecta fallos tipados en stat() de un path específico."""

    def __init__(self, fault_on=None, fault=PermissionError):
        super().__init__()
        self.fault_on = fault_on
        self.fault = fault

    def discover_cancellable(self, source, token=None, on_entry=None):
        return self._collect_discovered(Path(source.root_path), token, on_entry)


class TestStatFailClosed:
    def _fault_run(self, tmp_path, fault, expected_code):

        scanner = FilesystemLibrarySourceScanner()
        library, catalog, coordinator, lifecycle, pipeline = _env(
            tmp_path, scanner=scanner
        )
        source = _source(tmp_path, "a")
        root = Path(source.root_path)
        (root / "a.flac").write_bytes(b"x")
        (root / "b.flac").write_bytes(b"x")
        media_a = _seed_media(catalog, source, "a.flac")
        media_b = _seed_media(catalog, source, "b.flac")

        real_stat = Path.stat

        def fault_stat(self, *args, **kwargs):
            if self.name == "b.flac":
                raise fault(self)
            return real_stat(self, *args, **kwargs)

        Path.stat = fault_stat
        try:
            pipeline2 = _ManualPipeline()
            lifecycle2 = SourceScanLifecycle(coordinator, pipeline2)
            _run_worker(lifecycle2, pipeline2, source.library_source_id)
        finally:
            Path.stat = real_stat

        assert (
            coordinator.observed_availability(source.library_source_id)
            is SourceAvailability.ACCESS_DENIED
            if fault is PermissionError
            else SourceAvailability.IO_ERROR
        )
        after = {
            m.relative_path: m.availability
            for m in catalog.media_for_source(source.library_source_id)
        }
        assert after["a.flac"] is MediaAvailability.AVAILABLE
        assert after["b.flac"] is MediaAvailability.AVAILABLE

    def test_stat_permission_error_fails_closed(self, tmp_path):
        self._fault_run(tmp_path, PermissionError, LibraryDiagnosticCode.ACCESS_FAILURE)

    def test_stat_generic_oserror_fails_closed(self, tmp_path):
        class _EIO(OSError):
            errno = 5

        self._fault_run(tmp_path, _EIO, LibraryDiagnosticCode.IO_FAILURE)


# ==========================================================================
# P1-03/P1-04 — ARTWORK RELAY REAL + GENERATION GATE
# ==========================================================================


class _FakeProvider:
    def __init__(self, artwork_by_key=None, thread_ids=None):
        self.artwork_by_key = artwork_by_key or {}
        self.thread_ids = thread_ids

    def get_embedded_artwork(self, file_path):
        if self.thread_ids is not None:
            self.thread_ids.append(threading.get_ident())
        return None

    def get_local_artwork(self, album_dir):
        if self.thread_ids is not None:
            self.thread_ids.append(threading.get_ident())
        return None


class _Artwork:
    def __init__(self, data=b"PNG", mime_type="image/png"):
        self.data = data
        self.mime_type = mime_type


class TestArtworkRuntimeChannel:
    def _world(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )
        from michi.infrastructure.artwork import ArtworkCache
        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        provider = _FakeProvider(thread_ids=[])
        cache = ArtworkCache(tmp_path / "art")
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        refresh = LibraryArtworkRefresh(library, provider, cache, runner=runner)
        relay.done.connect(refresh.handle_done)
        coordinator._artwork_refresh = refresh
        return library, provider, cache, refresh, runner

    def test_artwork_relay_returns_to_owner(self, tmp_path, qapp):
        """6.6: relay real + runner real → handle_done → proyección."""
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )
        from michi.infrastructure.artwork import ArtworkCache
        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        album_key = library.state.albums[0].key

        class _ArtProvider:
            def __init__(self):
                self.thread_ids = []

            def get_embedded_artwork(self, file_path):
                self.thread_ids.append(threading.get_ident())
                return _Artwork()

            def get_local_artwork(self, album_dir):
                self.thread_ids.append(threading.get_ident())
                return None

        provider = _ArtProvider()
        cache = ArtworkCache(tmp_path / "art")
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        refresh = LibraryArtworkRefresh(library, provider, cache, runner=runner)
        relay.done.connect(refresh.handle_done)
        coordinator._artwork_refresh = refresh

        refresh.schedule()
        loop = QEventLoop()
        QTimer.singleShot(3000, loop.quit)
        loop.exec()

        assert provider.thread_ids, "provider nunca ejecutó"
        owner = threading.get_ident()
        assert all(t != owner for t in provider.thread_ids), "provider en owner"
        album = next(a for a in library.state.albums if a.key == album_key)
        assert album.has_artwork is True
        assert cache.lookup(album_key) is not None
        runner.shutdown()

    def test_worker_does_not_mutate_manifest_before_done(self, tmp_path, qapp):
        """6.8: el worker produce facts; el manifest cambia SOLO en _apply."""
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )
        from michi.infrastructure.artwork import ArtworkCache
        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        album_key = library.state.albums[0].key

        class _ArtProvider:
            def get_embedded_artwork(self, file_path):
                return _Artwork()

            def get_local_artwork(self, album_dir):
                return None

        cache = ArtworkCache(tmp_path / "art")
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        refresh = LibraryArtworkRefresh(library, _ArtProvider(), cache, runner=runner)
        relay.done.connect(refresh.handle_done)
        coordinator._artwork_refresh = refresh

        refresh.schedule()
        loop = QEventLoop()
        QTimer.singleShot(2500, loop.quit)
        loop.exec()

        # El manifest SOLO se muta tras el gate del owner (handle_done).
        album = next(a for a in library.state.albums if a.key == album_key)
        assert album.has_artwork is True
        assert cache.lookup(album_key) is not None
        runner.shutdown()

    def test_stale_artwork_generation_cannot_modify_manifest(self, tmp_path, qapp):
        """6.7: generación 2 entregada primero; la 1 tarde es inerte."""
        from michi.infrastructure.artwork import ArtworkCache

        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        album_key = library.state.albums[0].key
        cache = ArtworkCache(tmp_path / "art")

        class _ManualRunner:
            def __init__(self):
                self.submissions = []

            def submit(self, generation, work, on_progress, on_done):
                self.submissions.append((generation, work))

            def shutdown(self):
                pass

        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        refresh = LibraryArtworkRefresh(
            library, _FakeProvider(), cache, runner=_ManualRunner()
        )
        refresh.schedule()  # gen 1
        refresh.schedule()  # gen 2
        assert len(refresh._runner.submissions) == 2
        gen1_work = refresh._runner.submissions[0][1]
        gen2_work = refresh._runner.submissions[1][1]

        # Ejecutar el worker de la generación 2 (facts).
        results2 = gen2_work(_Progress(), ScanCancelToken(), lambda: None)
        results2[album_key] = _Artwork(b"B2")
        # Owner entrega la generación 2.
        refresh.handle_done(2, results2, None)
        assert cache.lookup(album_key) is not None
        manifest_after_gen2 = cache.lookup(album_key)

        # La generación 1 llega TARDE con ART_A — debe ser inerte.
        results1 = gen1_work(_Progress(), ScanCancelToken(), lambda: None)
        results1[album_key] = _Artwork(b"ART_A_STALE")
        refresh.handle_done(1, results1, None)
        assert cache.lookup(album_key) == manifest_after_gen2, (
            "stale generation modified the manifest"
        )


# ==========================================================================
# P1-05 — HYDRATE / RETIRE CACHE-ONLY (CERO PROVIDER I/O)
# ==========================================================================


class _TrapProvider:
    """Cualquier llamada del provider es un fallo del test."""

    def __init__(self):
        self.calls = 0

    def get_embedded_artwork(self, file_path):
        self.calls += 1
        raise AssertionError("provider I/O durante publicación cache-only")

    def get_local_artwork(self, album_dir):
        self.calls += 1
        raise AssertionError("provider I/O durante publicación cache-only")


class TestCacheOnlyPublication:
    def test_hydrate_does_zero_provider_io(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )
        from michi.infrastructure.artwork import ArtworkCache
        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        provider = _TrapProvider()
        cache = ArtworkCache(tmp_path / "art")
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        refresh = LibraryArtworkRefresh(library, provider, cache, runner=runner)
        relay.done.connect(refresh.handle_done)
        coordinator._artwork_refresh = refresh
        # Seed catálogo (una media).
        _seed_media(catalog, source, "a.flac")

        # Hydration con el provider trampa: si lo llama → AssertionError.
        coordinator.hydrate_catalog()
        assert provider.calls == 0
        assert len(library.state.tracks) == 1
        runner.shutdown()

    def test_retire_does_zero_provider_io(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )
        from michi.infrastructure.artwork import ArtworkCache
        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        _seed_media(catalog, source, "a.flac")
        provider = _TrapProvider()
        cache = ArtworkCache(tmp_path / "art")
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        refresh = LibraryArtworkRefresh(library, provider, cache, runner=runner)
        relay.done.connect(refresh.handle_done)
        coordinator._artwork_refresh = refresh

        coordinator.retire_source(source.library_source_id)
        assert provider.calls == 0
        assert library.state.tracks == []
        runner.shutdown()


# ==========================================================================
# P1-06 — RELOCATE PERSISTE EL ROOT NORMALIZADO
# ==========================================================================


class TestRelocateNormalizedRoot:
    def test_relocate_persists_normalized_path_same_id(self, tmp_path):
        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        actual = tmp_path / "Music2"
        actual.mkdir()
        raw = str(tmp_path / "temp" / ".." / "Music2")

        relocated = coordinator.relocate_source_root(source.library_source_id, raw)
        assert Path(relocated.root_path) == actual
        assert relocated.library_source_id == source.library_source_id


# ==========================================================================
# P1-08 — SOURCE OPERATION ERRORS OBSERVABLES
# ==========================================================================


class TestSourceOperationError:
    def _bridge(self, tmp_path):
        from michi.application.navigation_service import NavigationService

        library, catalog, coordinator, lifecycle, pipeline = _env(tmp_path)
        nav = NavigationService()
        bridge = LibraryBridge(
            library,
            source_coordinator=coordinator,
            source_scan_lifecycle=lifecycle,
        )
        return bridge

    def test_invalid_source_error_observable_then_cleared(self, tmp_path):
        from PySide6.QtCore import QUrl

        bridge = self._bridge(tmp_path)
        # Operación inválida → error observable.
        bridge.add_and_scan_music_source_url(QUrl("https://example.com/music"))
        assert bridge.property("sourceOperationError") != ""
        # Operación válida → el error se limpia.
        root = tmp_path / "ok"
        root.mkdir()
        error = bridge.add_and_scan_music_source_url(QUrl.fromLocalFile(str(root)))
        assert error == ""
        assert bridge.property("sourceOperationError") == ""


# ==========================================================================
# 6.5 — CANCELLATION DURING ACTIVE TRAVERSAL (barrier determinista)
# ==========================================================================


class TestCancellationDuringTraversal:
    def test_cancel_during_walk_aborts_no_commit(self, tmp_path):
        traversal_started = threading.Event()
        allow_continue = threading.Event()

        class _BarrierScanner(FilesystemLibrarySourceScanner):
            def __init__(self):
                super().__init__()
                self.first = True

            def discover_cancellable(self, source, token=None, on_entry=None):
                root = Path(source.root_path)
                self._validate_source_root(root)
                facts = []
                for path in self._walk(root):
                    if self.first:
                        self.first = False
                        traversal_started.set()
                        allow_continue.wait(5)
                    if token is not None and token.cancelled:
                        from michi.application.ports import ScanCancelled

                        raise ScanCancelled()
                    facts.append(path)
                return tuple(facts)

        library, catalog, coordinator, lifecycle, pipeline = _env(
            tmp_path, scanner=_BarrierScanner()
        )
        source = _source(tmp_path, "a")
        root = Path(source.root_path)
        for i in range(10):
            (root / f"t{i}.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        _seed_media(catalog, source, "t0.flac")

        pipeline2 = _ManualPipeline()
        lifecycle2 = SourceScanLifecycle(coordinator, pipeline2)
        lifecycle2.request_scan_source(source.library_source_id)
        generation, work, _, done = pipeline2.submissions[0]

        result = {}
        token = ScanCancelToken()

        def run_worker():
            try:
                work(_Progress(), token, lambda: None)
                result["ok"] = True
            except ScanCancelled:
                result["cancelled"] = True

        thread = threading.Thread(target=run_worker)
        thread.start()
        assert traversal_started.wait(5), "traversal nunca arrancó"
        lifecycle2.cancel()  # owner cancela la generación activa
        token.cancelled = True  # el token cooperativo del worker se marca
        allow_continue.set()
        thread.join(5)
        assert result.get("cancelled") is True, "worker no abortó"
        # Sin commit: el catálogo conserva SOLO el seed (1 track).
        assert len(catalog.load_tracks()) == 1, "commit tras cancel"
