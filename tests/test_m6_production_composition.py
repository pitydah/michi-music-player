"""M6-PRODUCTION-INTEGRATION-AND-ASYNC-CORRECTION — Phase-1 RED tests.

The production-composition contract: TEST GRAPH == PRODUCTION GRAPH. Every
test in this module builds the application graph through
``michi.bootstrap._build_services`` — the SAME construction path the real
``ApplicationContainer`` uses — and then exercises the REAL wiring:
SqliteLibraryIndexRepository, SqliteLibraryPrefsRepository,
SqlitePlaylistsRepository, PlaylistService, ThreadScanRunner and the
owner-thread LibraryScanDispatcher.

On the current baseline (HEAD 39f0f3b) ``_build_services`` does not exist and
the module fails at collection — that IS the expected Phase-1 red evidence.
The tests encode the target contract and must pass once the
M6-PRODUCTION-INTEGRATION-AND-ASYNC-CORRECTION changes land:

STAGE A (bootstrap wiring):
- ``_build_services(db_path, ...)`` builds the production graph testably;
- LibraryService receives the real ``library_index`` (SqliteLibraryIndexRepository)
  and ``library_prefs`` (SqliteLibraryPrefsRepository);
- LibraryBridge receives a real PlaylistService backed by SqlitePlaylistsRepository.
STAGE B (async generation safety):
- ThreadScanRunner keeps ONE token per generation (cancel(1) never poisons 2);
- durable index mutations happen ONLY after the generation gate (owner thread),
  inside a single ``apply_delta`` transaction — a stale worker NEVER writes SQLite.
STAGE C (owner-thread dispatch):
- LibraryScanDispatcher(QObject) with @Slot handlers connected via
  Qt.QueuedConnection; progress/done/state mutations run on the owner thread.
STAGE D (async shutdown lifecycle):
- ThreadScanRunner.shutdown() + LibraryScanDispatcher.shutdown(); late callbacks
  after shutdown are dropped; ApplicationContainer owns the lifecycle.
STAGE E (canonical determinism):
- AlbumRef.year from the FIRST canonical-sorted track with year > 0 (else 0);
- ArtistRef.album_count counts canonical AlbumIds, not title strings.
STAGE F (artwork state cleanup):
- _artwork_paths is rebuilt atomically during enrichment (stale entries pruned);
- album-level front-cover resolution is two-pass (explicit FRONT across all
  tracks, then first embedded fallback, then local).
STAGE G (presentation state):
- albumMode lives in LibraryView (survives the tab recreation);
- the bridge exposes scanProcessed/scanTotal/scanProgress/scanCurrentPath and
  a cancel_scan slot.
STAGE H (technical metadata):
- TrackRef retains codec/container/sample_rate_hz/bit_depth/channels/
  bitrate_bps/file_size; facts-only quality labels reach the projections.

Quality rules: no sleeps in the tested code, no xfail/skip, no lowered
assertions. The bounded event-loop spins below are the sanctioned Qt test
helpers; the GatedExtractor uses a threading.Event as a deterministic
in-flight gate (never a sleep-based race).
"""

import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.ports import ScanCancelToken, ScanProgress
from michi.bootstrap import _build_services
from michi.domain.library import LibraryScanStatus, TrackMetadata
from michi.infrastructure.library_index import SqliteLibraryIndexRepository
from michi.infrastructure.library_prefs import SqliteLibraryPrefsRepository
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from tests.conftest import FakeAudioPort
from tests.test_library_artwork import FakeArtworkCache, FakeArtworkProvider
from tests.test_library_incremental import StatScanner, _bump_mtime
from tests.test_library_metadata import FakeExtractor

QML_DIR = Path(__file__).parent.parent / "src" / "michi" / "presentation" / "qml"


@dataclass
class ProductionGraph:
    """The production composition under test (built by _build_services)."""

    db_path: Path
    library: object
    bridge: object
    runner: object
    dispatcher: object
    playlist_service: object
    library_index: SqliteLibraryIndexRepository
    library_prefs_repo: SqliteLibraryPrefsRepository
    playlists_repo: SqlitePlaylistsRepository
    scanner: object
    metadata_extractor: object


class CountingExtractor:
    """Spy extractor: records every extracted path, delegates to the factory."""

    def __init__(self, factory=None) -> None:
        self.inner = FakeExtractor(factory=factory)
        self.calls = []

    def extract(self, file_path):
        self.calls.append(file_path)
        return self.inner.extract(file_path)


class GatedExtractor:
    """Deterministic in-flight gate: extract() blocks until the gate is set.

    A test device — the worker parks inside the heavy work so the test can
    cancel/shutdown while the scan is provably in flight. Never sleeps; the
    gate is released explicitly (or times out bounded)."""

    def __init__(self, factory=None) -> None:
        self.inner = FakeExtractor(factory=factory)
        self.gate = threading.Event()
        self.calls = []
        self.worker_ids = []

    def extract(self, file_path):
        self.calls.append(file_path)
        self.worker_ids.append(threading.get_ident())
        self.gate.wait(timeout=5.0)
        return self.inner.extract(file_path)


def _music(tmp_path, names):
    music = tmp_path / "music"
    music.mkdir(exist_ok=True)
    paths = []
    for name in names:
        p = music / name
        p.write_bytes(b"x")
        paths.append(p)
    return music, paths


def _make_graph(tmp_path, scanner=None, extractor=None, provider=None, cache=None):
    """Build the PRODUCTION graph (bootstrap _build_services) for a fresh db.
    The audio backend is the sanctioned test seam (FakeAudioPort) — the real
    QtMultimediaBackend requires a QGuiApplication event loop and is an M5
    concern; every M6 component (index/prefs/playlists/runner/dispatcher/
    wiring) is the REAL production one."""
    db_path = tmp_path / "michi.db"
    graph = _build_services(
        db_path,
        backend=FakeAudioPort(),
        scanner=scanner,
        metadata_extractor=extractor,
        artwork_provider=provider,
        artwork_cache=cache,
    )
    return db_path, graph


def _spin_until(predicate, timeout=2.0):
    """Bounded Qt event-loop spin (sanctioned test helper)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return False


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


def _terminal(graph):
    return graph.library.state.scan_status in (
        LibraryScanStatus.COMPLETED,
        LibraryScanStatus.CANCELLED,
        LibraryScanStatus.FAILED,
    )


def _wait_terminal(graph, timeout=3.0):
    assert _spin_until(lambda: _terminal(graph), timeout=timeout), (
        f"scan did not reach a terminal status, got "
        f"{graph.library.state.scan_status.name}"
    )


def _wait_calls(extractor, n, timeout=3.0):
    assert _spin_until(lambda: len(extractor.calls) >= n, timeout=timeout), (
        f"extractor made {len(extractor.calls)} calls, expected at least {n}"
    )


class TestProductionComposition:
    def test_production_graph_wires_library_index(self, tmp_path):
        db_path, graph = _make_graph(tmp_path, StatScanner([]), CountingExtractor())
        assert graph.library._library_index is not None
        assert isinstance(graph.library._library_index, SqliteLibraryIndexRepository)
        assert graph.library._library_prefs is not None
        assert isinstance(graph.library._library_prefs, SqliteLibraryPrefsRepository)
        assert graph.bridge._playlist_service is graph.playlist_service
        assert graph.playlist_service is not None

    def test_production_unchanged_rescan_zero_extractions(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(8)])
        scanner = StatScanner(paths)
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, scanner, extractor)

        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(extractor.calls) == 8  # initial scan: N extractions

        extractor.calls.clear()
        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.COMPLETED
        assert extractor.calls == []  # unchanged rescan: ZERO extractions

    def test_production_library_prefs_survive_restart(self, tmp_path):
        music, (a, b) = _music(tmp_path, ("a.mp3", "b.mp3"))
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner([a, b]), extractor)
        graph.library.scan(str(music))
        graph.library.toggle_favorite(a)
        assert str(a) in graph.library.state.favorite_paths

        _teardown_graph(graph)
        _, graph2 = _make_graph_at(db_path, StatScanner([a, b]), CountingExtractor())
        assert str(a) in graph2.library.state.favorite_paths  # survives restart

    def test_production_history_survives_restart(self, tmp_path):
        music, (a, b) = _music(tmp_path, ("a.mp3", "b.mp3"))
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner([a, b]), extractor)
        graph.library.scan(str(music))
        graph.library.activate(0)  # arms the pending track
        graph.backend.trigger_media_accepted(a)  # commit -> history entry
        assert graph.library.state.history_paths, "activation should arm history"

        _teardown_graph(graph)
        _, graph2 = _make_graph_at(db_path, StatScanner([a, b]), CountingExtractor())
        assert graph2.library.state.history_paths == graph.library.state.history_paths

    def test_production_recently_added_survives_restart(self, tmp_path):
        music, (a, b) = _music(tmp_path, ("a.mp3", "b.mp3"))
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner([a, b]), extractor)
        graph.library.scan(str(music))
        assert str(a) in graph.library.state.recently_added_paths

        _teardown_graph(graph)
        _, graph2 = _make_graph_at(db_path, StatScanner([a, b]), CountingExtractor())
        assert str(a) in graph2.library.state.recently_added_paths

    def test_production_playlist_survives_restart(self, tmp_path):
        music, (a, b) = _music(tmp_path, ("a.mp3", "b.mp3"))
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner([a, b]), extractor)
        graph.library.scan(str(music))
        graph.bridge.create_playlist("Road")
        graph.bridge.add_to_playlist("Road", str(a))
        graph.bridge.add_to_playlist("Road", str(b))
        assert [(r["name"], r["trackCount"]) for r in graph.bridge.playlists] == [
            ("Road", 2)
        ]

        _teardown_graph(graph)
        _, graph2 = _make_graph_at(db_path, StatScanner([a, b]), CountingExtractor())
        assert [(r["name"], r["trackCount"]) for r in graph2.bridge.playlists] == [
            ("Road", 2)
        ]

    def test_production_bridge_exposes_persisted_playlists(self, tmp_path):
        music, (a,) = _music(tmp_path, ("a.mp3",))
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner([a]), extractor)
        graph.library.scan(str(music))
        graph.bridge.create_playlist("Keep")
        graph.bridge.add_to_playlist("Keep", str(a))
        assert graph.bridge.playlists != []  # real service, not a no-op


class TestTokenLifecycle:
    def test_cancelled_runner_allows_next_scan(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(20)])
        extractor = GatedExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        graph.library.start_scan(str(music))  # generation 1
        _wait_calls(extractor, 1)  # worker is IN FLIGHT inside the gate
        graph.library.cancel_scan()
        extractor.gate.set()  # release; the token check aborts the worker
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.CANCELLED

        # generation 2 must start with a FRESH token and COMPLETE.
        extractor.gate = threading.Event()
        extractor.gate.set()  # never block the new scan
        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(graph.library.state.tracks) == 20

    def test_cancel_generation_does_not_cancel_new_generation(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(20)])
        extractor = GatedExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        graph.library.start_scan(str(music))  # generation 1
        _wait_calls(extractor, 1)
        graph.library.start_scan(str(music))  # generation 2 supersedes (in flight)
        graph.runner.cancel(1)  # cancel ONLY generation 1's token
        extractor.gate.set()
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(graph.library.state.tracks) == 20  # gen 2 survived cancel(1)

    def test_cancel_unknown_generation_safe(self, tmp_path):
        _, graph = _make_graph(tmp_path, StatScanner([]), CountingExtractor())
        graph.runner.cancel(999)  # safe no-op, no crash
        assert True


class TestStaleGenerationDurable:
    def test_stale_generation_never_mutates_persistent_index(self, tmp_path):
        music, (a, b, c, d) = _music(tmp_path, ("a.mp3", "b.mp3", "c.mp3", "d.mp3"))
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner([a, b, c]), extractor)
        graph.library.scan(str(music))  # initial index: A B C
        assert {e.track_id for e in graph.library_index.load_all()} == {
            str(a),
            str(b),
            str(c),
        }

        # gen 10 builds A B C D but is superseded by gen 11 (A B C) that
        # completes FIRST; gen 10's late on_done must never write D.
        graph.library._scan_pipeline = _FakePipeline(graph.library)  # deterministic
        graph.library.start_scan(str(music))  # gen 1 == "10"
        gen10, work10, _, on_done10 = graph.library._scan_pipeline.submits[0]
        graph.scanner.paths = [a, b, c]
        graph.library.start_scan(str(music))  # gen 2 == "11" supersedes
        gen11, work11, _, on_done11 = graph.library._scan_pipeline.submits[1]

        result11 = work11(ScanProgress(), ScanCancelToken(), lambda: None)
        on_done11(gen11, result11, None)
        assert {e.track_id for e in graph.library_index.load_all()} == {
            str(a),
            str(b),
            str(c),
        }

        graph.scanner.paths = [a, b, c, d]  # the stale world would add D
        result10 = work10(ScanProgress(), ScanCancelToken(), lambda: None)
        assert len(result10.tracks) == 4  # prove the stale result DIFFERS
        on_done10(gen10, result10, None)  # late: MUST be dropped

        assert [t.file_path for t in graph.library.state.tracks] == [a, b, c]
        assert {e.track_id for e in graph.library_index.load_all()} == {
            str(a),
            str(b),
            str(c),  # D MUST NOT reappear in SQLite
        }

    def test_restart_after_stale_generation_uses_current_index(self, tmp_path):
        music, (a, b, c, d) = _music(tmp_path, ("a.mp3", "b.mp3", "c.mp3", "d.mp3"))
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner([a, b, c]), extractor)
        graph.library.scan(str(music))
        graph.library._scan_pipeline = _FakePipeline(graph.library)
        graph.library.start_scan(str(music))
        gen10, work10, _, on_done10 = graph.library._scan_pipeline.submits[0]
        graph.scanner.paths = [a, b, c]
        graph.library.start_scan(str(music))
        gen11, work11, _, on_done11 = graph.library._scan_pipeline.submits[1]
        on_done11(gen11, work11(ScanProgress(), ScanCancelToken(), lambda: None), None)
        graph.scanner.paths = [a, b, c, d]
        on_done10(gen10, work10(ScanProgress(), ScanCancelToken(), lambda: None), None)

        _teardown_graph(graph)
        scanner2 = StatScanner([a, b, c, d])
        extractor2 = CountingExtractor()
        _, graph2 = _make_graph_at(db_path, scanner2, extractor2)
        graph2.library.scan(str(music))
        # D must NOT be resurrected: unchanged index metadata for A B C,
        # D treated as a NEW file (its only legitimate path).
        assert [t.file_path for t in graph2.library.state.tracks] == [a, b, c, d]
        assert d in extractor2.calls  # D freshly extracted (was never indexed)


class TestOwnerThread:
    def test_async_commit_runs_on_owner_thread(self, tmp_path, qapp):
        gui_id = threading.get_ident()
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(8)])
        extractor = GatedExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        commit_ids = []
        graph.library.subscribe_changed(
            lambda: commit_ids.append(threading.get_ident())
        )

        graph.library.start_scan(str(music))
        _wait_calls(extractor, 1)
        extractor.gate.set()
        _wait_terminal(graph)

        assert graph.library.state.scan_status is LibraryScanStatus.COMPLETED
        assert commit_ids, "no service notify observed"
        # The heavy work ran on the worker thread (never the GUI thread), and
        # every state-mutation notify ran on the GUI (owner) thread.
        assert extractor.worker_ids
        assert all(wid != gui_id for wid in extractor.worker_ids)
        assert all(cid == gui_id for cid in commit_ids)

    def test_progress_callback_runs_on_owner_thread(self, tmp_path, qapp):
        gui_id = threading.get_ident()
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(8)])
        extractor = GatedExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        progress_ids = []
        graph.library.subscribe_changed(
            lambda: progress_ids.append(threading.get_ident())
        )

        graph.library.start_scan(str(music))
        _wait_calls(extractor, 1)
        extractor.gate.set()
        assert _spin_until(lambda: graph.library.state.scan_processed > 0)
        assert progress_ids, "no progress notifications observed"
        assert extractor.worker_ids
        assert all(wid != gui_id for wid in extractor.worker_ids)
        assert all(pid == gui_id for pid in progress_ids)

    def test_worker_thread_differs_from_gui_thread(self, tmp_path, qapp):
        gui_id = threading.get_ident()
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(8)])
        extractor = GatedExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        graph.library.start_scan(str(music))
        _wait_calls(extractor, 1)
        extractor.gate.set()
        _wait_terminal(graph)

        # The GatedExtractor records the thread that performed the heavy work:
        # it must differ from the GUI thread.
        assert extractor.worker_ids
        assert all(wid != gui_id for wid in extractor.worker_ids)


class TestShutdown:
    def test_shutdown_during_scan_blocks_late_commit(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(20)])
        extractor = GatedExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        graph.library.start_scan(str(music))
        _wait_calls(extractor, 1)  # scan is provably in flight

        notifies = []
        graph.library.subscribe_changed(lambda: notifies.append(1))
        graph.runner.shutdown()  # freeze/cancel the scan pipeline
        graph.dispatcher.shutdown()  # drop late callbacks
        extractor.gate.set()  # the worker finishes late
        QCoreApplication.processEvents()
        time.sleep(0.05)

        assert notifies == []  # no state mutation after shutdown
        assert graph.library.state.scan_status is LibraryScanStatus.DISCOVERING
        assert graph.library.state.scan_processed == 0
        assert graph.library_index.load_all() == ()  # no late durable write


class TestCanonicalModel:
    def test_album_year_deterministic_under_input_permutation(self):
        from michi.domain.library import TrackRef, build_music_model

        def refs(order):
            return [
                TrackRef(
                    file_path=Path(f"/m/{p}.mp3"),
                    album="Same",
                    artist="Artist",
                    track_number=num,
                    disc_number=disc,
                    year=year,
                    title=p,
                )
                for p, disc, num, year in order
            ]

        order_a = [("t1", 1, 1, 1999), ("t2", 1, 2, 2000)]
        order_b = [("t2", 1, 2, 2000), ("t1", 1, 1, 1999)]
        model_a = build_music_model(refs(order_a))
        model_b = build_music_model(refs(order_b))

        assert model_a.albums[0].key == model_b.albums[0].key  # same AlbumRef
        assert model_a.albums[0].year == model_b.albums[0].year
        assert model_a.albums[0].year == 1999  # first canonical track with year

    def test_artist_album_count_uses_canonical_album_identity(self):
        from michi.domain.library import TrackRef, build_music_model

        tracks = [
            TrackRef(
                file_path=Path("/m/a1.mp3"),
                title="t1",
                artist="Artist",
                album="Same",
                album_artist="Artist",
            ),
            TrackRef(
                file_path=Path("/m/a2.mp3"),
                title="t2",
                artist="Artist",
                album="Same",
                album_artist="Other",
            ),
        ]
        model = build_music_model(tracks)
        artist = next(a for a in model.artists if a.name == "Artist")
        assert artist.album_count == 2  # canonical AlbumIds, not title strings
        assert len(model.albums) == 2  # same title, different album_artist


class TestArtworkState:
    def test_artwork_path_pruned_after_album_removal(self, tmp_path):
        music, (a, b) = _music(tmp_path, ("a.mp3", "b.mp3"))
        provider = FakeArtworkProvider(artwork=None, local_artwork=_artwork())
        cache = FakeArtworkCache()
        extractor = CountingExtractor()
        _, graph = _make_graph(
            tmp_path, StatScanner([a, b]), extractor, provider, cache
        )
        graph.library.scan(str(music))
        album = graph.library.state.albums[0]
        assert album.has_artwork
        assert graph.library.artwork_path_for(album.key) is not None

        graph.scanner.paths = [a]  # album B leaves the library
        graph.library.scan(str(music))
        remaining = graph.library.state.albums[0]
        assert remaining.has_artwork  # the surviving album keeps its artwork
        assert graph.library.artwork_path_for(
            album.key
        ) == graph.library.artwork_path_for(remaining.key)

    def test_artwork_path_pruned_when_art_disappears(self, tmp_path):
        music, (a,) = _music(tmp_path, ("a.mp3",))
        provider = FakeArtworkProvider(artwork=None, local_artwork=_artwork())
        cache = FakeArtworkCache()
        extractor = CountingExtractor()
        _, graph = _make_graph(tmp_path, StatScanner([a]), extractor, provider, cache)
        graph.library.scan(str(music))
        album = graph.library.state.albums[0]
        assert graph.library.artwork_path_for(album.key) is not None

        provider.local_artwork = None  # artwork disappears
        graph.library.scan(str(music))
        assert graph.library.state.albums[0].key == album.key  # album still exists
        assert graph.library.artwork_path_for(album.key) is None  # pruned


class TestPresentationState:
    def test_album_mode_preserved_across_tab_switch(self, qapp, tmp_path):
        from michi.domain.library import Artwork

        music, (a,) = _music(tmp_path, ("a.mp3",))
        provider = FakeArtworkProvider(artwork=Artwork(b"x", "image/png"))
        cache = FakeArtworkCache()
        extractor = CountingExtractor()
        _, graph = _make_graph(tmp_path, StatScanner([a]), extractor, provider, cache)
        graph.library.scan(str(music))

        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", graph.bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
        obj = component.create()
        assert obj is not None, "LibraryView: null object"

        obj.setProperty("currentTab", "albums")
        QCoreApplication.processEvents()
        obj.setProperty("albumMode", "magazine")
        QCoreApplication.processEvents()
        albums = obj.findChild(QObject, "albumsView")
        assert albums is not None
        assert albums.property("albumMode") == "magazine"

        obj.setProperty("currentTab", "artists")  # AlbumsView is destroyed
        QCoreApplication.processEvents()
        obj.setProperty("currentTab", "albums")  # recreated
        QCoreApplication.processEvents()
        albums2 = obj.findChild(QObject, "albumsView")
        assert albums2 is not None
        assert albums2.property("albumMode") == "magazine"  # preserved

        obj.deleteLater()
        _teardown_graph(graph)

    def test_scan_progress_bridge_projection(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(8)])
        extractor = GatedExtractor()
        _, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        graph.library.start_scan(str(music))
        assert graph.bridge.scanStatus != ""  # armed synchronously
        assert graph.bridge.scanStatus == "DISCOVERING"
        _wait_calls(extractor, 1)  # worker in flight inside the gate
        extractor.gate.set()
        assert _spin_until(lambda: graph.bridge.scanProcessed > 0)
        assert graph.bridge.scanTotal == 8
        assert graph.bridge.scanProgress > 0
        assert graph.bridge.scanCurrentPath != ""
        _wait_terminal(graph)
        assert graph.bridge.scanStatus == "COMPLETED"
        assert graph.bridge.scanProcessed == 8
        assert graph.bridge.scanProgress == 1.0

    def test_cancel_scan_bridge_slot(self, tmp_path, monkeypatch):
        _, graph = _make_graph(tmp_path, StatScanner([]), CountingExtractor())
        calls = []
        original = graph.library.cancel_scan

        def spy():
            calls.append(1)
            return original()

        monkeypatch.setattr(graph.library, "cancel_scan", spy)
        graph.bridge.cancel_scan()
        assert calls == [1]  # the slot delegates to service.cancel_scan

    def test_new_scan_after_cancel_via_full_pipeline(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(12)])
        extractor = GatedExtractor()
        _, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        graph.library.start_scan(str(music))
        _wait_calls(extractor, 1)
        graph.library.cancel_scan()
        extractor.gate.set()
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.CANCELLED

        extractor.gate = threading.Event()
        extractor.gate.set()
        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(graph.library.state.tracks) == 12


class TestTechnicalMetadata:
    def test_technical_metadata_reaches_track_projection(self, tmp_path):
        music, (a, b) = _music(tmp_path, ("a.mp3", "b.mp3"))

        def factory(path):
            if path.name == "a.mp3":
                return TrackMetadata(
                    title="A",
                    artist="Artist",
                    album="Album",
                    codec="FLAC",
                    container="flac",
                    sample_rate_hz=96000,
                    bit_depth=24,
                    channels=2,
                    bitrate_bps=0,
                    file_size=12345,
                )
            return TrackMetadata(
                title="B",
                artist="Artist",
                album="Album",
                codec="MP3",
                container="mp3",
                sample_rate_hz=0,
                bit_depth=0,
                channels=2,
                bitrate_bps=320000,
                file_size=6789,
            )

        extractor = CountingExtractor(factory=factory)
        _, graph = _make_graph(tmp_path, StatScanner([a, b]), extractor)
        graph.library.scan(str(music))

        album = graph.library.state.albums[0]
        graph.bridge.select_album(album.key)
        rows = graph.bridge.albumTracks
        assert len(rows) == 2
        row_a = next(r for r in rows if r["path"] == str(a))
        assert row_a["codec"] == "FLAC"
        assert row_a["container"] == "flac"
        assert row_a["sampleRateHz"] == 96000
        assert row_a["bitDepth"] == 24
        assert row_a["channels"] == 2
        assert row_a["bitrateBps"] == 0
        assert row_a["fileSize"] == 12345
        assert row_a["qualityLabel"] == "FLAC · 24-bit · 96 kHz"
        row_b = next(r for r in rows if r["path"] == str(b))
        assert row_b["qualityLabel"] == "MP3 · 320 kbps"
        assert "Hi-Res" not in row_b["qualityLabel"]
        assert "Lossless" not in row_a["qualityLabel"]


class TestProductionGolden:
    def test_production_golden_full_sequence(self, tmp_path, qapp):
        names = [f"t{i:02}.mp3" for i in range(10)]
        music, paths = _music(tmp_path, names)
        extractor = CountingExtractor()
        db_path, graph = _make_graph(tmp_path, StatScanner(paths), extractor)

        # 1. initial scan -> N extractions
        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert len(extractor.calls) == 10

        # 2. unchanged scan -> ZERO extractions
        extractor.calls.clear()
        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert extractor.calls == []

        # 3. favorite + playlist through the BRIDGE (production surface)
        graph.bridge.toggle_favorite(str(paths[0]))
        assert str(paths[0]) in graph.library.state.favorite_paths
        graph.bridge.create_playlist("Golden")
        for p in paths[:3]:
            graph.bridge.add_to_playlist("Golden", str(p))

        # 4. cancel a scan, then a new scan completes (full pipeline)
        graph.library.start_scan(str(music))
        _wait_terminal(graph)  # may complete before the cancel lands; the
        # dedicated token tests cover the in-flight cancel deterministically
        graph.library.cancel_scan()
        extractor.calls.clear()
        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.COMPLETED
        assert extractor.calls == []  # still unchanged: no reparse

        # 5. modify ONE track -> exactly ONE extraction
        _bump_mtime(paths[5])
        extractor.calls.clear()
        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert extractor.calls == [paths[5]]

        # 6. shutdown the production graph
        graph.runner.shutdown()
        graph.dispatcher.shutdown()

        # 7. a NEW production graph on the same db: everything survives
        scanner2 = StatScanner(paths)
        extractor2 = CountingExtractor()
        _, graph2 = _make_graph_at(db_path, scanner2, extractor2)
        graph2.library.start_scan(str(music))
        _wait_terminal(graph2)
        assert extractor2.calls == []  # index reused: zero reparse
        assert str(paths[0]) in graph2.library.state.favorite_paths
        assert [(r["name"], r["trackCount"]) for r in graph2.bridge.playlists] == [
            ("Golden", 3)
        ]
        assert str(paths[0]) in graph2.library.state.recently_added_paths


# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------


class _FakePipeline:
    """Deterministic pipeline drive (the SAME commit path as production):
    submit records; the tests call work()/on_done() explicitly. Reuses the
    production _on_scan_done handler through the service."""

    def __init__(self, library):
        self._library = library
        self.submits = []

    def submit(self, generation, work, on_progress, on_done):
        def recording_work(progress, token, report):
            return work(progress, token, report)

        self.submits.append((generation, recording_work, on_progress, on_done))

    def cancel(self, generation):
        pass


def _artwork():
    from michi.domain.library import Artwork

    return Artwork(data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 20, mime_type="image/png")


def _make_graph_at(db_path, scanner, extractor):
    graph = _build_services(
        db_path,
        backend=FakeAudioPort(),
        scanner=scanner,
        metadata_extractor=extractor,
        artwork_provider=None,
        artwork_cache=None,
    )
    return db_path, graph


def _teardown_graph(graph):
    """Freeze the graph (mirrors the container shutdown order for scans)."""
    if getattr(graph.runner, "shutdown", None) is not None:
        graph.runner.shutdown()
    if getattr(graph.dispatcher, "shutdown", None) is not None:
        graph.dispatcher.shutdown()
    graph.bridge.dispose()
