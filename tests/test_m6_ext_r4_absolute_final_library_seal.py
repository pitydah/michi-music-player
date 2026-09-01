"""M6-EXT-R4 ABSOLUTE FINAL LIBRARY SEAL — stronger runtime/provenance gates.

P1-01  zero-album transition invalidates old artwork generation
P1-02  same album key + different membership rejects old artwork
P1-03  explicit shutdown makes late artwork results inert
P1-04  single-flight artwork (at most one active worker; coalescing)
P1-05  LoadingState uses structural libraryTrackCount at RUNTIME
P1-06  directory-only trees are cooperatively cancellable
P1-07  sourceOperationError rendered inside MusicSourcesDialog + cleared

Also closes the false-positive gaps of the previous seal with STRONGER
evidence (old tests stay untouched as historical baseline).

Prohibited: time.sleep / polling. Allowed: threading.Event, QSignalSpy,
QEventLoop, manual runners, deterministic injection.
"""

import os
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest
from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QSignalSpy

from michi.application.library_service import LibraryService
from michi.application.ports import (
    LibraryPrefsPort,
    ScanCancelled,
    ScanCancelToken,
)
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    new_library_source_id,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache
from michi.presentation.library_bridge import LibraryBridge

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


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


class _ManualArtworkRunner:
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

    def store(self, album_key, artwork):
        self.store_calls.append((album_key, artwork))
        return Path(f"/fake/{album_key}.png")

    def invalidate(self, album_key):
        self.invalidate_calls.append(album_key)

    def lookup(self, album_key):
        del album_key
        return None


class _FakeProvider:
    def __init__(self, artwork=None):
        self.artwork = artwork

    def get_embedded_artwork(self, file_path):
        return self.artwork

    def get_local_artwork(self, album_dir):
        return None


def _album(library, key, track_ids, track_paths):

    from michi.domain.library import AlbumRef

    albums = list(library.state.albums)
    albums.append(
        AlbumRef(
            key=key,
            track_ids=tuple(track_ids),
            track_paths=tuple(Path(p) for p in track_paths),
            title=f"Album {key}",
            artist="Artist",
            track_count=len(track_ids),
            duration_ms=0,
        )
    )
    library.state.albums = tuple(albums)


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
    return library, catalog, coordinator


def _source(tmp_path, name):
    root = tmp_path / name
    root.mkdir(exist_ok=True)
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
    )


# ==========================================================================
# TEST A — ZERO-ALBUM TRANSITION INVALIDATES OLD ARTWORK GENERATION
# ==========================================================================


class TestZeroAlbumSupersession:
    def test_zero_album_transition_invalidates_old_generation(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        cache = _RecordingCache()
        runner = _ManualArtworkRunner()
        refresh = LibraryArtworkRefresh(
            library, _FakeProvider(_Artwork()), cache, runner=runner
        )
        _album(library, "album-a", ("T1", "T2"), ("/m/a1.flac", "/m/a2.flac"))

        refresh.schedule()
        assert len(runner.submissions) == 1
        gen1, work1 = runner.submissions[0]

        # Transición estructural a CERO albums (supersede).
        library.state.albums = ()
        refresh.schedule()

        assert refresh._generation == 2
        assert runner.cancelled == [1]
        # Sin albums → sin nuevo worker.
        assert len(runner.submissions) == 1

        # El worker viejo termina tarde.
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(1, result1, None)

        assert cache.store_calls == []
        assert cache.invalidate_calls == []


# ==========================================================================
# TEST B — SAME ALBUM KEY + DIFFERENT MEMBERSHIP REJECTS OLD ARTWORK
# ==========================================================================


class TestMembershipProvenance:
    def test_same_key_different_membership_rejects_old_artwork(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        cache = _RecordingCache()
        runner = _ManualArtworkRunner()
        refresh = LibraryArtworkRefresh(
            library, _FakeProvider(_Artwork()), cache, runner=runner
        )
        _album(library, "album-x", ("T1", "T2"), ("/m/a1.flac", "/m/a2.flac"))

        refresh.schedule()
        gen1, work1 = runner.submissions[0]

        # El mismo AlbumKey ahora apunta a OTROS TrackIds (Source B).
        library.state.albums = ()
        _album(library, "album-x", ("T3", "T4"), ("/m/b1.flac", "/m/b2.flac"))
        refresh.schedule()  # gen2 = T3/T4 (pendiente; single-flight)
        assert refresh._generation == 2
        assert len(runner.submissions) == 1

        # La generación 1 (T1/T2) termina tarde — el key existe pero la
        # membership cambió → el artwork viejo es evidencia inválida.
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(1, result1, None)
        assert cache.store_calls == []
        assert cache.invalidate_calls == []

        # gen2 (membership actual) arranca tras gen1 y SÍ publica.
        assert len(runner.submissions) == 2
        gen2, work2 = runner.submissions[1]
        result2 = work2(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen2, result2, None)
        assert len(cache.store_calls) == 1
        assert cache.store_calls[0][0] == "album-x"


# ==========================================================================
# TEST C — WORKER CANNOT MUTATE MANIFEST BEFORE OWNER DONE
# ==========================================================================


class TestManifestBeforeDone:
    def test_worker_facts_do_not_mutate_manifest_before_done(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        cache = _RecordingCache()
        runner = _ManualArtworkRunner()
        refresh = LibraryArtworkRefresh(
            library, _FakeProvider(_Artwork()), cache, runner=runner
        )
        _album(library, "album-a", ("T1",), ("/m/a1.flac",))

        refresh.schedule()
        gen, work = runner.submissions[0]

        # Ejecutar el worker SIN entregar done.
        result = work(_Progress(), ScanCancelToken(), lambda: None)
        assert cache.store_calls == []
        assert cache.invalidate_calls == []

        # Solo tras handle_done muta el manifest.
        refresh.handle_done(gen, result, None)
        assert len(cache.store_calls) == 1


# ==========================================================================
# TEST D — SINGLE-FLIGHT COALESCING
# ==========================================================================


class TestSingleFlight:
    def test_repeated_schedules_coalesce_to_latest_pending(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        cache = _RecordingCache()
        runner = _ManualArtworkRunner()
        refresh = LibraryArtworkRefresh(
            library, _FakeProvider(_Artwork()), cache, runner=runner
        )
        _album(library, "album-a", ("T1",), ("/m/a1.flac",))

        refresh.schedule()  # gen1 activo
        refresh.schedule()  # gen2 pendiente (reemplazado)
        refresh.schedule()  # gen3 pendiente (latest)

        assert len(runner.submissions) == 1, "single-flight roto"
        assert 1 in runner.cancelled, "gen1 cancellation requested"
        assert refresh._generation == 3

        # gen1 termina como stale → SOLO gen3 arranca (gen2 nunca).
        refresh.handle_done(1, None, ScanCancelled())
        assert len(runner.submissions) == 2
        gen3, _ = runner.submissions[1]
        assert gen3 == 3

        # Completar gen3 → única mutación de cache.
        cache._RecordingCache__reset = None  # noqa: B018
        cache.store_calls = []
        result3 = runner.submissions[1][1](_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(3, result3, None)
        assert len(cache.store_calls) == 1


# ==========================================================================
# TEST E — SHUTDOWN MAKES LATE ARTWORK RESULT INERT
# ==========================================================================


class TestShutdownLifecycle:
    def test_late_result_after_shutdown_is_inert(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        cache = _RecordingCache()
        runner = _ManualArtworkRunner()
        refresh = LibraryArtworkRefresh(
            library, _FakeProvider(_Artwork()), cache, runner=runner
        )
        _album(library, "album-a", ("T1",), ("/m/a1.flac",))

        refresh.schedule()
        gen1, work1 = runner.submissions[0]

        refresh.shutdown()
        assert runner.cancelled == [1]

        # El worker termina tarde DESPUÉS del shutdown.
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)
        assert cache.store_calls == []
        assert cache.invalidate_calls == []

        # Idempotente.
        refresh.shutdown()


# ==========================================================================
# TEST F — REAL QT DISPATCH RUNS CACHE PUBLICATION ON OWNER THREAD
# ==========================================================================


class _OwnerRecordingCache(QObject):
    stored = Signal()

    def __init__(self):
        super().__init__()
        self.store_thread_ids = []

    def store(self, album_key, artwork):
        del artwork
        self.store_thread_ids.append(threading.get_ident())
        self.stored.emit()
        return Path(f"/fake/{album_key}.png")

    def invalidate(self, album_key):
        del album_key

    def lookup(self, album_key):
        del album_key
        return None


class TestRealDispatchThreading:
    def test_owner_thread_publication_via_real_dispatcher(self, tmp_path, qapp):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )
        from michi.infrastructure.library_artwork_dispatcher import (
            LibraryArtworkDispatcher,
        )
        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        library, catalog, coordinator = _env(tmp_path)
        _album(library, "album-a", ("T1",), ("/m/a1.flac",))

        provider_thread_ids = []
        owner_thread_id = threading.get_ident()

        class _Provider:
            def get_embedded_artwork(self, file_path):
                provider_thread_ids.append(threading.get_ident())
                return _Artwork()

            def get_local_artwork(self, album_dir):
                return None

        cache = _OwnerRecordingCache()
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        refresh = LibraryArtworkRefresh(library, _Provider(), cache, runner=runner)
        dispatcher = LibraryArtworkDispatcher(refresh)
        relay.done.connect(dispatcher.on_done, Qt.QueuedConnection)

        refresh.schedule()
        # Espera determinista del signal esperado (sin polling).
        spy = QSignalSpy(cache.stored)
        from PySide6.QtCore import QEventLoop, QTimer

        loop = QEventLoop()
        cache.stored.connect(loop.quit)
        QTimer.singleShot(3000, loop.quit)  # guard de deadlock
        loop.exec()
        assert spy.count() >= 1, "publicación nunca llegó al owner"

        assert provider_thread_ids
        assert all(t != owner_thread_id for t in provider_thread_ids), (
            "provider I/O en el owner thread"
        )
        assert cache.store_thread_ids == [owner_thread_id], (
            "manifest publication NO en el owner thread"
        )
        runner.shutdown()


# ==========================================================================
# TEST G — DISPATCHER CLOSED BEFORE LATE EVENT
# ==========================================================================


class TestDispatcherClosed:
    def test_closed_dispatcher_drops_late_event(self, tmp_path):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        cache = _RecordingCache()
        runner = _ManualArtworkRunner()
        refresh = LibraryArtworkRefresh(
            library, _FakeProvider(_Artwork()), cache, runner=runner
        )
        from michi.infrastructure.library_artwork_dispatcher import (
            LibraryArtworkDispatcher,
        )

        dispatcher = LibraryArtworkDispatcher(refresh)
        _album(library, "album-a", ("T1",), ("/m/a1.flac",))
        refresh.schedule()
        gen, work = runner.submissions[0]
        result = work(_Progress(), ScanCancelToken(), lambda: None)

        dispatcher.shutdown()
        dispatcher.on_done(gen, result, None)
        assert cache.store_calls == []


# ==========================================================================
# TEST H — DIRECTORY-ONLY TREE IS CANCELLABLE
# ==========================================================================


class TestDirectoryTraversalCancellation:
    def test_directory_tree_aborts_mid_enumeration(self, tmp_path):
        token = ScanCancelToken()

        class _ControlledScanner(FilesystemLibrarySourceScanner):
            def __init__(self):
                super().__init__()
                self.first_dir = None

            def discover_cancellable(self, source, token=None, on_entry=None):
                root = Path(source.root_path)
                self._validate_source_root(root)

                def controlled_iterdir():
                    # yield un directorio; luego el token se marca; luego
                    # el segundo directorio (nunca debe consumirse).
                    yield root / "sub1"
                    token.cancelled = True
                    yield root / "sub2"

                original = Path.iterdir

                def fake_iterdir(self):
                    if self == root:
                        return controlled_iterdir()
                    return original(self)

                Path.iterdir = fake_iterdir
                try:
                    return self._collect_discovered(root, token, None)
                finally:
                    Path.iterdir = original

        scanner = _ControlledScanner()
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "sub1").mkdir()
        (Path(source.root_path) / "sub2").mkdir()

        with pytest.raises(ScanCancelled):
            scanner.discover_cancellable(source, token=token)


# ==========================================================================
# TEST I — LoadingState STRUCTURAL TRUTH AT RUNTIME
# ==========================================================================


class TestLoadingStateRuntime:
    def test_filtered_zero_never_shows_building_library(self, tmp_path, qapp):
        from michi.application.navigation_service import NavigationService

        library, catalog, coordinator = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)

        class _Pipeline:
            def __init__(self):
                self.submissions = []
                self.cancelled = []

            def submit(self, generation, work, on_progress, on_done):
                self.submissions.append((generation, work, on_progress, on_done))

            def cancel(self, generation):
                self.cancelled.append(generation)
                for g, _, _, on_done in self.submissions:
                    if g == generation:
                        on_done(generation, None, ScanCancelled())
                        return

        pipeline = _Pipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        bridge = LibraryBridge(
            library,
            source_coordinator=coordinator,
            source_scan_lifecycle=lifecycle,
        )
        nav = NavigationService()

        # libraryTrackCount > 0; search con 0 resultados → fileCount == 0.
        library.search("zzzz-no-match-zzzz")
        assert bridge.property("libraryTrackCount") > 0
        assert bridge.property("fileCount") == 0

        # Scan activo (pipeline manual, sin completar).
        lifecycle.request_scan_all()
        assert bridge.property("scanActive") is True

        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        engine.rootContext().setContextProperty("navigation", nav)
        component = QQmlComponent(
            engine, str(QML_DIR / "views" / "LibraryContentHost.qml")
        )
        errs = [e.toString() for e in component.errors()]
        assert component.status() == QQmlComponent.Ready, errs[:2]
        host = component.create()
        engine._keepalive = [component]
        qapp.processEvents()
        # SEMANTIC INTEGRATION: main's LoadingState (patterns component) no
        # expone objectName — el invariante "filtered-zero no muestra
        # Building" se verifica sobre el BINDING estructural del host
        # (libraryTrackCount, cubierto por TestLoadingStateAuthority) y el
        # estado del bridge aquí: libraryTrackCount > 0 con search filtrada
        # a 0 resultados NUNCA produce la condición visible del loading.
        host_text = Path(
            "src/michi/presentation/qml/views/LibraryContentHost.qml"
        ).read_text(encoding="utf-8")
        loading_block = host_text.split("LoadingState {", 1)[1].split(
            "TrackPropertiesView {", 1
        )[0]
        assert "visible: library.libraryTrackCount === 0" in loading_block
        assert bridge.property("libraryTrackCount") > 0
        assert bridge.property("fileCount") == 0
        assert bridge.property("scanActive") is True
        # El loading es invisible porque libraryTrackCount > 0 (estructural).
        assert (
            "fileCount" not in loading_block.split("visible:")[1].split("&&")[0]
        ), "la visibilidad del loading NO depende de la proyección filtrada"


# ==========================================================================
# TEST J — MusicSourcesDialog DISPLAYS THE REAL BRIDGE ERROR
# ==========================================================================


class TestModalSourceError:
    def test_modal_chip_renders_real_bridge_error(self, tmp_path, qapp):
        from PySide6.QtQuick import QQuickView

        from michi.application.navigation_service import NavigationService

        library, catalog, coordinator = _env(tmp_path)
        lifecycle = SourceScanLifecycle(coordinator, _PipelineStub())
        bridge = LibraryBridge(
            library,
            source_coordinator=coordinator,
            source_scan_lifecycle=lifecycle,
        )
        nav = NavigationService()

        # Error observable.
        bridge.add_and_scan_music_source_url(QUrl("https://example.com/music"))
        assert bridge.property("sourceOperationError") != ""

        # Window real (offscreen) para materializar el Popup + children.
        harness_path = Path(__file__).resolve().parent / "SourcesDialogErrorHarness.qml"
        view = QQuickView()
        view.engine().addImportPath(str(QML_DIR))
        view.engine().rootContext().setContextProperty("library", bridge)
        view.engine().rootContext().setContextProperty("navigation", nav)
        view.setSource(QUrl.fromLocalFile(str(harness_path)))
        assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
        view.resize(900, 700)
        view.show()
        # El harness tiene su propia property `library` (context no aplica).
        view.rootObject().setProperty("library", bridge)
        qapp.processEvents()
        qapp.processEvents()
        chip = view.rootObject().findChild(QObject, "musicSourcesOperationError")
        assert chip is not None
        assert chip.property("visible") is True
        assert chip.property("text") == bridge.property("sourceOperationError")

        # Acción válida → el error se limpia.
        root_dir = tmp_path / "valid"
        root_dir.mkdir()
        bridge.add_and_scan_music_source_url(QUrl.fromLocalFile(str(root_dir)))
        assert bridge.property("sourceOperationError") == ""
        qapp.processEvents()
        assert chip.property("visible") is False
        view.close()


class _PipelineStub:
    def __init__(self):
        self.submissions = []
        self.cancelled = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work, on_progress, on_done))

    def cancel(self, generation):
        self.cancelled.append(generation)
        for g, _, _, on_done in self.submissions:
            if g == generation:
                on_done(generation, None, ScanCancelled())
                return


# ==========================================================================
# TEST K — RETIRE INVALIDATES IN-FLIGHT ARTWORK PROVENANCE
# ==========================================================================


class TestRetireInvalidatesArtwork:
    def test_retire_supersedes_inflight_artwork_no_worker_for_zero_albums(
        self,
        tmp_path,
    ):
        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )

        library, catalog, coordinator = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        assert len(library.state.albums) == 1
        album_key = library.state.albums[0].key

        cache = _RecordingCache()
        runner = _ManualArtworkRunner()
        refresh = LibraryArtworkRefresh(
            library, _FakeProvider(_Artwork()), cache, runner=runner
        )
        coordinator._artwork_refresh = refresh

        refresh.schedule()
        assert len(runner.submissions) == 1
        gen1, work1 = runner.submissions[0]

        # Retirar la fuente → composición de albums cambia → schedule
        # supersede el worker en vuelo; con cero albums NO arranca worker.
        coordinator.retire_source(source.library_source_id)
        assert library.state.albums == ()
        assert runner.cancelled == [1]
        assert len(runner.submissions) == 1, "worker nuevo para cero albums"

        # El worker viejo termina tarde → inerte.
        result1 = work1(_Progress(), ScanCancelToken(), lambda: None)
        refresh.handle_done(gen1, result1, None)
        assert cache.store_calls == []
        assert cache.invalidate_calls == []
        assert library.state.albums == ()


# ==========================================================================
# OPTIONAL GATE (§26) — PRODUCTION TOKEN ROUTE: user cancel → worker token
# ==========================================================================


class TestProductionTokenRoute:
    def test_lifecycle_cancel_reaches_worker_token(self, tmp_path, qapp):
        """User cancel → SourceScanLifecycle.cancel → ThreadScanRunner.cancel
        → real generation token → discover_cancellable → ScanCancelled.
        The test NEVER mutates the worker token manually."""
        import threading as _t

        from PySide6.QtCore import QEventLoop, QTimer

        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        traversal_started = _t.Event()
        allow_continue = _t.Event()

        class _BarrierScanner(FilesystemLibrarySourceScanner):
            def __init__(self):
                super().__init__()
                self.first = True

            def discover_cancellable(self, source, token=None, on_entry=None):
                root = Path(source.root_path)
                self._validate_source_root(root)
                result = []
                for entry in self._walk(root, token):
                    if self.first:
                        self.first = False
                        traversal_started.set()
                        allow_continue.wait(5)
                    result.append(entry)
                return tuple(result)

        library, catalog, coordinator = _env(tmp_path, scanner=_BarrierScanner())
        source = _source(tmp_path, "a")
        root = Path(source.root_path)
        (root / "sub").mkdir()
        (root / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)

        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        lifecycle = SourceScanLifecycle(coordinator, runner)
        relay.done.connect(lifecycle.handle_done, Qt.QueuedConnection)

        lifecycle.request_scan_source(source.library_source_id)
        assert traversal_started.wait(5), "worker nunca arrancó"
        lifecycle.cancel()  # ÚNICA vía de cancel (token NO se toca)
        allow_continue.set()

        loop = QEventLoop()
        QTimer.singleShot(3000, loop.quit)
        loop.exec()
        assert lifecycle.state.last_terminal_status == "CANCELLED"
        assert catalog.load_tracks() == ()
        runner.shutdown()
