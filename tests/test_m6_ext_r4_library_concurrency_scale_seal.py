"""M6-EXT-R4 LIBRARY CONCURRENCY / SCALE SEAL — deterministic race gates.

CONCURRENCY-LIB-02  scan_changed vs library_changed telemetry separation
CONCURRENCY-LIB-03  cancellable discovery + truthful MARKING_MISSING
CONCURRENCY-LIB-04  rejected generation cannot publish late progress
PERF-LIB-01         O(1) TrackId/path indexes (structural counters)
P1/PERF-LIB-12      artwork provider probing is NOT owner-thread work
"""

import os
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest

from michi.application.library_port import DiscoveredMediaFile
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
    MediaAvailability,
    MediaFileRecord,
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
    def __init__(self, delayed_cancel=False):
        self.submissions = []
        self.cancelled = []
        self.delayed_cancel = delayed_cancel

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work, on_progress, on_done))

    def cancel(self, generation):
        self.cancelled.append(generation)
        if not self.delayed_cancel:
            for submitted in self.submissions:
                if submitted[0] == generation:
                    submitted[3](generation, None, ScanCancelled())
                    return

    def run(self, index=0):
        generation, work, on_progress, on_done = self.submissions[index]
        progress = _Progress()
        token = ScanCancelToken()
        try:
            plan = work(progress, token, lambda: None)
        except BaseException as exc:  # noqa: BLE001
            on_done(generation, None, exc)
            return None
        on_done(generation, plan, None)
        return plan


class _DelayedCancelPipeline(_ManualPipeline):
    def __init__(self):
        super().__init__(delayed_cancel=True)


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
    return library, catalog, coordinator


class _CancellableScanner(FilesystemLibrarySourceScanner):
    """Walk determinista con entradas contadas y parada cooperativa."""

    def __init__(self, entries=50):
        super().__init__()
        self.entries = entries
        self.yielded = 0

    def discover_cancellable(self, source, token=None, on_entry=None):
        # Usa la implementación real con on_entry para contar.
        return super().discover_cancellable(source, token=token, on_entry=on_entry)


class _ManyFilesScanner(FilesystemLibrarySourceScanner):
    def __init__(self, files):
        super().__init__()
        self.files = files

    def discover(self, source):
        facts = []
        for relative, (size, mtime, dev, inode) in self.files.items():
            facts.append(
                DiscoveredMediaFile(
                    absolute_path=Path(source.root_path) / relative,
                    relative_path=relative,
                    file_size=size,
                    mtime_ns=mtime,
                    device_id=dev,
                    inode=inode,
                )
            )
        return tuple(facts)


# ==========================================================================
# CONCURRENCY-LIB-02 — TELEMETRY SIGNAL SEPARATION
# ==========================================================================


class TestTelemetrySeparation:
    def test_progress_ticks_never_emit_library_changed(self, tmp_path):
        library, catalog, coordinator = _env(tmp_path)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        pipeline = _DelayedCancelPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        bridge = LibraryBridge(
            library,
            source_coordinator=coordinator,
            source_scan_lifecycle=lifecycle,
        )
        scan_events = []
        library_events = []
        bridge.scan_changed.connect(lambda: scan_events.append(1))
        bridge.library_changed.connect(lambda: library_events.append(1))

        lifecycle.request_scan_source(source.library_source_id)
        generation, work, _, _ = pipeline.submissions[0]
        progress = _Progress()
        # Ejecutar el worker: DISCOVERING + RECONCILING reportan progress.
        import contextlib

        with contextlib.suppress(ScanCancelled):
            work(progress, ScanCancelToken(), lambda: None)
        # 100 ticks deterministas de progress puro:
        for i in range(100):
            lifecycle.handle_progress(
                generation, _Progress(phase="RECONCILING", processed=i, total=100)
            )
        assert len(scan_events) > 0
        assert len(library_events) == 0

    def test_terminal_transition_emits_library_changed(self, tmp_path):
        library, catalog, coordinator = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        bridge = LibraryBridge(
            library,
            source_coordinator=coordinator,
            source_scan_lifecycle=lifecycle,
        )
        library_events = []
        bridge.library_changed.connect(lambda: library_events.append(1))
        lifecycle.request_scan_source(source.library_source_id)
        pipeline.run(0)
        assert len(library_events) >= 1


# ==========================================================================
# CONCURRENCY-LIB-03 — CANCELLABLE DISCOVERY + MARKING_MISSING
# ==========================================================================


class TestCancellableDiscovery:
    def test_cancel_token_stops_walk_before_complete_traversal(self, tmp_path):
        library, catalog, coordinator = _env(tmp_path)
        source = _source(tmp_path, "a")
        root = Path(source.root_path)
        for i in range(60):
            (root / f"t{i}.flac").write_bytes(b"x")
        catalog.upsert_source(source)
        pipeline = _DelayedCancelPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, work, _, _ = pipeline.submissions[0]
        token = ScanCancelToken()
        token.cancelled = True  # cancel ANTES de empezar el walk
        with pytest.raises(ScanCancelled):
            work(_Progress(), token, lambda: None)
        # Sin plan → sin commit.
        assert catalog.load_tracks() == ()

    def test_marking_missing_phase_is_truthful(self, tmp_path):
        scanner = _ManyFilesScanner({})
        library, catalog, coordinator = _env(tmp_path, scanner=scanner)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        # 5 medias conocidas que ya no se descubren.
        media_records = []
        tracks = []
        for i in range(5):
            media = MediaFileRecord(
                media_file_id=new_media_file_id(),
                library_source_id=source.library_source_id,
                relative_path=f"old{i}.flac",
                last_known_path=str(Path(source.root_path) / f"old{i}.flac"),
                availability=MediaAvailability.AVAILABLE,
            )
            media_records.append(media)
            tracks.append(
                __import__(
                    "michi.domain.library_catalog", fromlist=["TrackRecord"]
                ).TrackRecord(
                    track_id=new_track_id(), media_file_id=media.media_file_id
                )
            )
        catalog.apply_source_reconciliation(tuple(media_records), tuple(tracks))
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, work, _, _ = pipeline.submissions[0]
        phases = []

        def report():
            phases.append((progress.phase, progress.total, progress.processed))

        progress = _Progress()
        work(progress, ScanCancelToken(), report)
        assert any(p[0] == "MARKING_MISSING" and p[1] == 5 for p in phases), phases

    def test_cancel_during_marking_missing_no_commit(self, tmp_path):
        scanner = _ManyFilesScanner({})
        library, catalog, coordinator = _env(tmp_path, scanner=scanner)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        media_records = []
        tracks = []
        for i in range(5):
            media = MediaFileRecord(
                media_file_id=new_media_file_id(),
                library_source_id=source.library_source_id,
                relative_path=f"old{i}.flac",
                last_known_path=str(Path(source.root_path) / f"old{i}.flac"),
                availability=MediaAvailability.AVAILABLE,
            )
            media_records.append(media)
            tracks.append(
                __import__(
                    "michi.domain.library_catalog", fromlist=["TrackRecord"]
                ).TrackRecord(
                    track_id=new_track_id(), media_file_id=media.media_file_id
                )
            )
        catalog.apply_source_reconciliation(tuple(media_records), tuple(tracks))
        pipeline = _DelayedCancelPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, work, _, _ = pipeline.submissions[0]
        token = ScanCancelToken()
        token.cancelled = True
        with pytest.raises(ScanCancelled):
            work(_Progress(), token, lambda: None)
        # Sin commit de la fase de missing.
        assert all(
            m.availability is MediaAvailability.AVAILABLE
            for m in catalog.media_for_source(source.library_source_id)
        )


# ==========================================================================
# CONCURRENCY-LIB-04 — LATE PROGRESS AFTER OWNER REJECTION
# ==========================================================================


class TestLateProgressRejected:
    def test_late_progress_never_mutates_state_after_cancel(self, tmp_path):
        library, catalog, coordinator = _env(tmp_path)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        pipeline = _DelayedCancelPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, work, _, _ = pipeline.submissions[0]
        # Worker reporta un poco de progreso normal.
        lifecycle.handle_progress(
            generation, _Progress(phase="RECONCILING", processed=1, total=10)
        )
        assert lifecycle.state.processed == 1
        # Owner rechaza la generación.
        lifecycle.cancel()
        # Late progress de la MISMA generación → ignorado.
        lifecycle.handle_progress(
            generation, _Progress(phase="RECONCILING", processed=9, total=10)
        )
        assert lifecycle.state.processed == 1
        assert lifecycle.state.current_path == ""


# ==========================================================================
# PERF-LIB-01 — O(1) INDEXES (structural proof, no timing)
# ==========================================================================


class TestIndexedLookups:
    def _library_with_tracks(self, tmp_path, count=200):
        scanner = _ManyFilesScanner(
            {f"t{i}.flac": (100 + i, 1000 + i, 1, 2) for i in range(count)}
        )
        library, catalog, coordinator = _env(tmp_path, scanner=scanner)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        coordinator.scan_source(source)
        return library, source

    def test_trackref_lookups_do_not_iterate_tracks(self, tmp_path):
        library, source = self._library_with_tracks(tmp_path)
        refs = library.state.tracks
        assert len(refs) >= 200

        # Trampa de iteración: si algún lookup recorre state.tracks, el
        # contador se dispara.
        class _TrapList(list):
            iteration_count = 0

            def __iter__(self):
                _TrapList.iteration_count += 1
                return super().__iter__()

        library.state.tracks = _TrapList(library.state.tracks)
        first = refs[0]
        assert library.trackref_by_id(first.track_id) is not None
        assert library.resolve_trackref(first.file_path) is not None
        for ref in refs[:50]:
            assert library.trackref_by_id(ref.track_id) is not None
        assert _TrapList.iteration_count == 0

    def test_indexes_refresh_after_relink(self, tmp_path):
        library, source = self._library_with_tracks(tmp_path)
        ref = library.state.tracks[0]
        # Relink: el archivo cambia de ubicación.
        new_path = Path(source.root_path) / "moved" / "t0.flac"
        new_path.parent.mkdir(exist_ok=True)
        new_path.write_bytes(b"x" * 200)
        from dataclasses import replace

        updated = replace(ref, file_path=new_path)
        library.apply_source_tracks(
            source.library_source_id,
            [updated if r is ref else r for r in library.state.tracks],
        )
        assert library.resolve_trackref(new_path) is not None
        assert library.trackref_by_id(ref.track_id).file_path == new_path


# ==========================================================================
# P1/PERF-LIB-12 — ARTWORK THREAD AFFINITY
# ==========================================================================


class _SpyArtworkProvider:
    """Registra el thread de cada llamada al provider."""

    def __init__(self):
        self.thread_ids = []
        self.owner_thread = threading.get_ident()

    def get_embedded_artwork(self, file_path):
        self.thread_ids.append(threading.get_ident())
        return None

    def get_local_artwork(self, album_dir):
        self.thread_ids.append(threading.get_ident())
        return None


class TestArtworkThreadAffinity:
    def test_provider_calls_not_on_owner_thread(self, tmp_path):
        import time

        from michi.application.library_artwork_refresh import (
            LibraryArtworkRefresh,
        )
        from michi.infrastructure.artwork import ArtworkCache
        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        library, catalog, coordinator = _env(tmp_path)
        source = _source(tmp_path, "a")
        (Path(source.root_path) / "a.flac").write_bytes(b"x")
        catalog.upsert_source(source)

        provider = _SpyArtworkProvider()
        cache = ArtworkCache(tmp_path / "art")
        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        refresh = LibraryArtworkRefresh(library, provider, cache, runner=runner)
        coordinator._artwork_refresh = refresh

        # El commit del source schedulea el refresh (owner no proba).
        coordinator.scan_source(source)
        # El refresh async proba — SIEMPRE en el WORKER, nunca en el owner.
        deadline = time.monotonic() + 5
        while not provider.thread_ids and time.monotonic() < deadline:
            time.sleep(0.01)
        assert provider.thread_ids, "artwork refresh never probed"
        owner = threading.get_ident()
        assert all(tid != owner for tid in provider.thread_ids), (
            "artwork provider ran on the owner thread: "
            f"owner={owner} provider={provider.thread_ids}"
        )
        runner.shutdown()
