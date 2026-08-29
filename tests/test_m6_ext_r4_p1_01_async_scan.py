"""M6-EXT-R4 FINAL SEAL P1-01 — productive source scans are ASYNC.

The GUI slot must return BEFORE any filesystem/reconciliation work; the
heavy phase runs on the WORKER via the real M6.4 pipeline; the owner thread
commits after the generation gate; sources are serialized; stale/cancelled
generations never commit.
"""

import os
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryPrefs, TrackMetadata
from michi.domain.library_catalog import (
    LibrarySource,
    new_library_source_id,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache
from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner


class _StubPrefs(LibraryPrefsPort):
    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        del prefs


class _SlowMetadata:
    """Simulates a slow/degraded storage path: extraction takes 50ms."""

    def extract(self, file_path: Path) -> TrackMetadata:
        time.sleep(0.05)
        return TrackMetadata(title=file_path.stem, artist="A", album="B")


class _SlowScanner(FilesystemLibrarySourceScanner):
    """Enumerates with a detectable delay so the test can prove the slot
    returned before the work ran."""

    def discover(self, source):
        time.sleep(0.08)
        return super().discover(source)


def _env(tmp_path, *, slow=False):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    scanner = _SlowScanner() if slow else FilesystemLibrarySourceScanner()
    library = LibraryService(scanner, library_prefs=_StubPrefs())
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        scanner,
        media_cache=SqliteLibraryMediaCache(db_path),
        metadata_extractor=_SlowMetadata() if slow else None,
    )
    return library, catalog, coordinator


from michi.application.source_scan_coordinator import (  # noqa: E402
    SourceScanCoordinator,
)


def _source(tmp_path, name: str) -> LibrarySource:
    root = tmp_path / name
    root.mkdir()
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
    )


class _OwnerDispatcher:
    """Simulates the bootstrap wiring: relay signals delivered on the
    owner (test) thread via QueuedConnection semantics — deterministic
    delivery by calling the lifecycle handlers synchronously."""

    def __init__(self, lifecycle: SourceScanLifecycle) -> None:
        self._lifecycle = lifecycle

    def on_done(self, generation, plan, error) -> None:
        self._lifecycle.handle_done(generation, plan, error)

    def on_progress(self, generation, progress) -> None:
        self._lifecycle.handle_progress(generation, progress)


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


class TestProductiveAsyncScan:
    def test_slot_returns_before_heavy_work_runs(self, qapp, tmp_path) -> None:
        """The GUI slot returns immediately; the heavy phase runs on the
        worker afterwards."""
        library, catalog, coordinator = _env(tmp_path, slow=True)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        root = Path(source.root_path)
        for i in range(3):
            (root / f"song{i}.flac").write_bytes(b"x")

        relay = ScanRelay()
        pipeline = ThreadScanRunner(relay)
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        dispatcher = _OwnerDispatcher(lifecycle)
        relay.done.connect(dispatcher.on_done)
        relay.progress.connect(dispatcher.on_progress)

        started = time.monotonic()
        lifecycle.request_scan_all()
        returned = time.monotonic() - started
        # The slot returns BEFORE the worker finished (slow scanner ~240ms).
        assert returned < 0.1
        assert lifecycle.state.active is True

        # Wait for the async completion on the owner side.
        deadline = time.monotonic() + 5
        while lifecycle.state.active and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert lifecycle.state.status == "IDLE"
        assert len(catalog.load_tracks()) == 3  # committed
        assert len(library.state.tracks) == 3  # published
        pipeline._closed = True

    def test_scan_all_serializes_sources(self, qapp, tmp_path) -> None:
        """Sources are scanned ONE AT A TIME (never parallel): the lifecycle
        never starts source B before source A completed."""
        library, catalog, coordinator = _env(tmp_path, slow=True)
        order: list[str] = []
        a = _source(tmp_path, "a")
        b = _source(tmp_path, "b")
        catalog.upsert_source(a)
        catalog.upsert_source(b)
        (Path(a.root_path) / "a1.flac").write_bytes(b"x")
        (Path(b.root_path) / "b1.flac").write_bytes(b"x")

        original = coordinator.compute_source_reconciliation

        def tracking(source, discovered):
            order.append(source.library_source_id)
            time.sleep(0.02)
            return original(source, discovered)

        coordinator.compute_source_reconciliation = tracking
        relay = ScanRelay()
        pipeline = ThreadScanRunner(relay)
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        dispatcher = _OwnerDispatcher(lifecycle)
        relay.done.connect(dispatcher.on_done)
        relay.progress.connect(dispatcher.on_progress)

        lifecycle.request_scan_all()
        deadline = time.monotonic() + 5
        while lifecycle.state.active and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert order == [a.library_source_id, b.library_source_id]
        assert len(catalog.load_tracks()) == 2
        pipeline._closed = True

    def test_cancel_mid_scan_never_commits(self, qapp, tmp_path) -> None:
        library, catalog, coordinator = _env(tmp_path, slow=True)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        root = Path(source.root_path)
        for i in range(5):
            (root / f"song{i}.flac").write_bytes(b"x")

        relay = ScanRelay()
        pipeline = ThreadScanRunner(relay)
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        dispatcher = _OwnerDispatcher(lifecycle)
        relay.done.connect(dispatcher.on_done)
        relay.progress.connect(dispatcher.on_progress)

        lifecycle.request_scan_all()
        time.sleep(0.05)  # mid-scan
        lifecycle.cancel()
        deadline = time.monotonic() + 5
        while lifecycle.state.active and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        # Cancelled: ZERO authoritative commit, ZERO publication.
        assert catalog.load_tracks() == ()
        assert library.state.tracks == []
        pipeline._closed = True

    def test_stale_completion_never_commits(self, qapp, tmp_path) -> None:
        """A completion carrying an OLD generation (superseded scan) must
        not commit — the gate compares against the current generation."""
        library, catalog, coordinator = _env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        (Path(source.root_path) / "song.flac").write_bytes(b"x")

        relay = ScanRelay()
        pipeline = ThreadScanRunner(relay)
        lifecycle = SourceScanLifecycle(coordinator, pipeline)

        # A REAL plan computed for the source…
        discovered = coordinator._scanner.discover(source)
        plan = coordinator.compute_source_reconciliation(source, discovered)
        assert plan.upsert_media  # the plan WOULD add a track

        # …delivered for an OLD generation while the lifecycle is on a NEW
        # generation: the gate rejects it, nothing commits.
        lifecycle._generation = 7
        lifecycle._active = True
        lifecycle.handle_done(6, plan, None)
        assert catalog.load_tracks() == ()
        assert library.state.tracks == []
        pipeline._closed = True

    def test_scan_failure_reports_without_commit(self, qapp, tmp_path) -> None:
        from michi.application.library_port import LibraryFilesystemError
        from michi.domain.library import LibraryDiagnosticCode

        class _BrokenScanner(FilesystemLibrarySourceScanner):
            def discover(self, source):
                raise LibraryFilesystemError(
                    LibraryDiagnosticCode.DIRECTORY_MISSING,
                    Path(source.root_path),
                    "root gone",
                )

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        library = LibraryService(_BrokenScanner(), library_prefs=_StubPrefs())
        coordinator = SourceScanCoordinator(library, catalog, _BrokenScanner())
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)

        relay = ScanRelay()
        pipeline = ThreadScanRunner(relay)
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        dispatcher = _OwnerDispatcher(lifecycle)
        relay.done.connect(dispatcher.on_done)
        relay.progress.connect(dispatcher.on_progress)

        lifecycle.request_scan_all()
        deadline = time.monotonic() + 5
        while lifecycle.state.active and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert lifecycle.state.status == "IDLE"
        assert catalog.load_tracks() == ()  # no partial commit
        pipeline._closed = True
