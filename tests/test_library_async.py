"""M6.4 async library scan pipeline — Phase-1 RED tests.

On the current baseline the module-level imports of the new symbols fail at
collection (ImportError) — that IS the expected Phase-1 red evidence. The
tests encode the target contract and must pass once the M6.4 production
changes land:

- michi/domain/library.py: ``LibraryScanStatus`` enum + the scan-state fields
  on ``LibraryState`` (scan_status/scan_generation/scan_processed/scan_total/
  scan_progress/scan_current_path after composers)
- michi/domain/library_index.py: ``ScanResult`` (tracks/upserts/removed — the
  heavy-work output; the commit derives the state deltas on the owner thread)
- michi/application/ports.py: ``ScanProgress`` (mutable, thread-shared),
  ``ScanCancelToken`` (cooperative flag), ``ScanCancelled``, and the
  ``ScanPipelinePort`` abstract port (submit/cancel)
- michi/application/library_service.py: ``LibraryService.__init__`` gains
  ``scan_pipeline``; NEW ``start_scan``/``cancel_scan``/``_build_scan_work``/
  ``_run_scan_work``/``_on_scan_progress``/``_on_scan_done``; the scan()
  commit block is refactored into a shared private ``_commit_scan_result``
  used by both paths; the synchronous scan() is untouched (the sync path does
  NOT touch the scan-state contract — test_scan_without_pipeline_falls_back_sync)
- michi/presentation/library_bridge.py: the ``scan`` slot delegates to
  ``self._service.start_scan(directory)``
- michi/infrastructure/scan_runner.py: ``ScanRelay`` (QObject with
  progress/done signals) + ``ThreadScanRunner`` (spawns a worker thread,
  dispatches progress/done to the owner thread via the relay)

Coverage:
- Fresh-service scan-state defaults (IDLE / 0 / 0 / 0 / None / None)
- start_scan returns promptly (work NOT run synchronously), arms generation 1,
  status DISCOVERING, exactly one arming notify
- Async commit through the fake pipeline: atomic, derived-coherent, status
  COMPLETED, EXACTLY ONE notify for the commit transition
- Progress contract: processed monotonic non-decreasing, total == path count,
  scan_progress reaches 1.0, current_path reflects the last processed track
- Supersession: a newer start_scan arms a newer generation; a STALE
  generation's late work/on_done NEVER commits (no second notify); late
  progress is ignored
- Cooperative cancellation: token.cancelled aborts the work with
  ScanCancelled; the handler lands status CANCELLED and the previous library
  state stays INTACT; cancel_scan() forwards the current generation
- Failure path: LibraryFilesystemError(DIRECTORY_MISSING) -> FAILED +
  diagnostic, tracks/derived preserved
- Per-track MetadataExtractionError is isolated: the work completes with a
  stem-title fallback TrackRef and the scan commits (COMPLETED)
- The incremental index path works through the async flow: an unchanged
  rescan performs ZERO extractions
- Without a pipeline start_scan falls back to the synchronous scan()
  (tracks populated; scan-state contract untouched — status stays IDLE)
- ONE bounded real-async smoke test of ThreadScanRunner + ScanRelay with the
  offscreen QGuiApplication fixture (event-loop spin with a 2s deadline);
  the rest of the suite is driven deterministically through the fake
- The LibraryBridge scan slot delegates to service.start_scan (spy) and the
  service arms a generation
"""

import os
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.ports import (
    ScanCancelled,
    ScanCancelToken,
    ScanProgress,
)
from michi.application.queue_service import QueueService
from michi.domain.library import LibraryDiagnosticCode, LibraryScanStatus, TrackRef
from michi.domain.library_index import ScanResult
from michi.infrastructure.library_index import SqliteLibraryIndexRepository
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_incremental import CountingExtractor, StatScanner


class FakeScanPipeline:
    """Duck-typed ScanPipelinePort: records submit/cancel; NEVER runs the
    work synchronously (proven by ``ran_work``). The tests drive the recorded
    work + progress/done handlers deterministically."""

    def __init__(self) -> None:
        self.submits: list = []  # (generation, work, on_progress, on_done)
        self.cancels: list = []
        self.ran_work = False

    def submit(self, generation, work, on_progress, on_done) -> None:
        def recording_work(progress, token, report):
            self.ran_work = True
            return work(progress, token, report)

        self.submits.append((generation, recording_work, on_progress, on_done))

    def cancel(self, generation) -> None:
        self.cancels.append(generation)


def _make_library(tmp_path, scanner, extractor, pipeline=None, with_index=True):
    """Build LibraryService with a real queue; optionally wire the index and
    the scan pipeline (same pattern as tests/test_library_incremental.py)."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    if with_index:
        repo = SqliteLibraryIndexRepository(tmp_path / "michi.db")
        library = LibraryService(
            scanner,
            metadata_extractor=extractor,
            library_index=repo,
            scan_pipeline=pipeline,
        )
        return library, repo
    library = LibraryService(
        scanner, metadata_extractor=extractor, scan_pipeline=pipeline
    )
    return library, None


def _music(tmp_path, names=("a.mp3", "b.mp3", "c.mp3")):
    """Create a music dir with one byte-sized file per name; return (dir, paths)."""
    music = tmp_path / "music"
    music.mkdir()
    paths = []
    for name in names:
        p = music / name
        p.write_bytes(b"x")
        paths.append(p)
    return music, paths


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestScanStateDefaults:
    def test_scan_state_defaults(self, tmp_path):
        scanner = StatScanner([])
        extractor = CountingExtractor()
        library, _ = _make_library(
            tmp_path, scanner, extractor, pipeline=None, with_index=False
        )

        assert library.state.scan_status is LibraryScanStatus.IDLE
        assert library.state.scan_generation == 0
        assert library.state.scan_processed == 0
        assert library.state.scan_total == 0
        assert library.state.scan_progress is None
        assert library.state.scan_current_path is None


class TestStartScan:
    def test_start_scan_returns_promptly_and_arms_generation(self, tmp_path):
        scanner = StatScanner([])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(
            tmp_path, scanner, extractor, pipeline=pipeline, with_index=False
        )
        notifies = []
        library.subscribe_changed(lambda: notifies.append(1))

        library.start_scan(str(tmp_path / "music"))

        # Returns promptly: exactly ONE submit, the work NOT run inline.
        assert len(pipeline.submits) == 1
        generation, work, _, _ = pipeline.submits[0]
        assert generation == 1
        assert pipeline.ran_work is False
        # Arming: generation bumped, status DISCOVERING, one arming notify.
        assert library.state.scan_generation == 1
        assert library.state.scan_status is LibraryScanStatus.DISCOVERING
        assert library.state.scan_processed == 0
        assert library.state.scan_total == 0
        assert library.state.scan_progress is None
        assert library.state.scan_current_path is None
        assert len(notifies) == 1

    def test_cancel_scan_public(self, tmp_path):
        scanner = StatScanner([])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(
            tmp_path, scanner, extractor, pipeline=pipeline, with_index=False
        )
        library.start_scan(str(tmp_path / "music"))
        assert pipeline.cancels == []

        library.cancel_scan()

        assert pipeline.cancels == [1]  # the CURRENT generation

    def test_scan_without_pipeline_falls_back_sync(self, tmp_path):
        music, (a, b) = _music(tmp_path, names=("a.mp3", "b.mp3"))
        scanner = StatScanner([a, b])
        extractor = CountingExtractor()
        library, _ = _make_library(
            tmp_path, scanner, extractor, pipeline=None, with_index=False
        )

        library.start_scan(str(music))

        # The synchronous scan ran (compat fallback)...
        assert [t.file_path for t in library.state.tracks] == [a, b]
        # ...and the sync path does NOT touch the scan-state contract.
        assert library.state.scan_status is LibraryScanStatus.IDLE
        assert library.state.scan_generation == 0
        assert library.state.scan_processed == 0
        assert library.state.scan_total == 0

    def test_bridge_scan_slot_uses_start_scan(self, tmp_path, monkeypatch):
        music, (a,) = _music(tmp_path, names=("a.mp3",))
        scanner = StatScanner([a])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)
        bridge = LibraryBridge(library)

        calls = []
        original = library.start_scan

        def spy(directory):
            calls.append(directory)
            return original(directory)

        monkeypatch.setattr(library, "start_scan", spy)
        bridge.scan(str(music))

        assert calls == [str(music)]  # the slot delegates to start_scan
        assert library.state.scan_generation == 1  # service armed a generation
        assert len(pipeline.submits) == 1
        bridge.dispose()


class TestAsyncCommit:
    def test_async_commit_atomic_single_notify(self, tmp_path):
        music, (a, b, c) = _music(tmp_path)
        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)
        notifies = []
        library.subscribe_changed(lambda: notifies.append(1))

        library.start_scan(str(music))
        generation, work, _, on_done = pipeline.submits[0]

        result = work(ScanProgress(), ScanCancelToken(), lambda: None)
        assert isinstance(result, ScanResult)
        assert len(result.tracks) == 3

        notifies.clear()  # the arming notify is behind us
        on_done(generation, result, None)

        assert [t.file_path for t in library.state.tracks] == [a, b, c]
        assert (
            sum(al.track_count for al in library.state.albums)
            == len(library.state.tracks)
            == 3
        )
        assert library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(notifies) == 1  # EXACTLY ONE notify for the commit transition

    def test_progress_monotonic_and_complete(self, tmp_path):
        music, (a, b, c) = _music(tmp_path)
        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)
        library.start_scan(str(music))
        generation, work, on_progress, _ = pipeline.submits[0]

        progress = ScanProgress()
        token = ScanCancelToken()
        snapshots = []

        def report():
            snapshots.append(
                (progress.processed, progress.total, progress.current_path)
            )
            on_progress(progress)  # the runner dispatches progress to the owner

        work(progress, token, report)

        assert len(snapshots) >= 3  # one report per extracted track
        processed_seq = [s[0] for s in snapshots]
        assert processed_seq == sorted(processed_seq)  # non-decreasing
        # The FINAL dispatched progress reflects a complete extraction.
        assert library.state.scan_total == 3
        assert library.state.scan_processed == 3
        assert library.state.scan_progress == 1.0
        assert library.state.scan_current_path == str(c)  # last processed track

    def test_metadata_failure_isolated(self, tmp_path):
        music, (a, b, c) = _music(tmp_path)
        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor()
        extractor.inner.failing = {b}  # track B raises MetadataExtractionError
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)
        library.start_scan(str(music))
        generation, work, _, on_done = pipeline.submits[0]

        result = work(ScanProgress(), ScanCancelToken(), lambda: None)
        assert len(result.tracks) == 3  # the work COMPLETES despite the failure
        on_done(generation, result, None)

        assert library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(library.state.tracks) == 3
        b_ref = next(t for t in library.state.tracks if t.file_path == b)
        assert b_ref.title == "b"  # stem-title fallback, scan continues

    def test_async_incremental_reuse(self, tmp_path):
        music, (a, b, c) = _music(tmp_path)
        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)

        library.start_scan(str(music))
        gen1, work1, _, on_done1 = pipeline.submits[0]
        on_done1(gen1, work1(ScanProgress(), ScanCancelToken(), lambda: None), None)
        assert extractor.calls == [a, b, c]  # initial scan extracts everything

        extractor.calls.clear()
        library.start_scan(str(music))
        gen2, work2, _, on_done2 = pipeline.submits[1]
        result2 = work2(ScanProgress(), ScanCancelToken(), lambda: None)
        on_done2(gen2, result2, None)

        # THE acceptance gate through the async flow: ZERO extractions.
        assert extractor.calls == []
        assert [t.file_path for t in library.state.tracks] == [a, b, c]
        assert library.state.scan_status is LibraryScanStatus.COMPLETED


class TestSupersession:
    def test_supersession_stale_generation_never_commits(self, tmp_path):
        music, (a, b, c, d) = _music(
            tmp_path, names=("a.mp3", "b.mp3", "c.mp3", "d.mp3")
        )
        scanner = StatScanner([a, b, c, d])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)

        library.start_scan(str(music))  # gen 1
        gen1, work1, _, on_done1 = pipeline.submits[0]

        scanner.paths = [a, b, c]  # gen 2 discovers a smaller set
        library.start_scan(str(music))  # gen 2 supersedes
        gen2, work2, _, on_done2 = pipeline.submits[1]
        assert gen2 == 2

        result2 = work2(ScanProgress(), ScanCancelToken(), lambda: None)
        on_done2(gen2, result2, None)
        assert [t.file_path for t in library.state.tracks] == [a, b, c]

        # gen 1's LATE work lands afterwards — it must be IGNORED.
        scanner.paths = [a, b, c, d]  # the stale world would commit 4 tracks
        result1 = work1(ScanProgress(), ScanCancelToken(), lambda: None)
        assert len(result1.tracks) == 4  # prove the stale result DIFFERS
        notifies = []
        library.subscribe_changed(lambda: notifies.append(1))
        on_done1(gen1, result1, None)

        assert [t.file_path for t in library.state.tracks] == [a, b, c]  # gen 2 intact
        assert library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(notifies) == 0  # NO second commit notify

    def test_late_progress_ignored(self, tmp_path):
        music, (a,) = _music(tmp_path, names=("a.mp3",))
        scanner = StatScanner([a])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)
        library.start_scan(str(music))  # gen 1
        gen1, _, on_progress1, _ = pipeline.submits[0]
        library.start_scan(str(music))  # gen 2 supersedes
        assert library.state.scan_generation == 2

        stale = ScanProgress()
        stale.phase = "EXTRACTING"
        stale.processed = 99
        stale.total = 100
        stale.current_path = str(a)
        on_progress1(stale)  # stale generation-1 progress arrives late

        assert library.state.scan_status is LibraryScanStatus.DISCOVERING
        assert library.state.scan_processed == 0
        assert library.state.scan_total == 0
        assert library.state.scan_progress is None
        assert library.state.scan_current_path is None


class TestCancellation:
    def test_cancellation_cooperative(self, tmp_path):
        music, (a, b, c) = _music(tmp_path)
        scanner = StatScanner([a, b, c])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)
        library.scan(str(music))  # a prior library via the sync path
        before_tracks = tuple(library.state.tracks)

        library.start_scan(str(music))
        generation, work, _, on_done = pipeline.submits[0]

        progress = ScanProgress()
        token = ScanCancelToken()
        token.cancelled = True  # cancelled BEFORE the extraction loop
        with pytest.raises(ScanCancelled):
            work(progress, token, lambda: None)

        notifies = []
        library.subscribe_changed(lambda: notifies.append(1))
        on_done(generation, None, ScanCancelled())

        assert library.state.scan_status is LibraryScanStatus.CANCELLED
        assert tuple(library.state.tracks) == before_tracks  # library INTACT
        assert len(notifies) == 1


class TestAsyncFailure:
    def test_async_scan_failure_preserves_state(self, tmp_path):
        music, (a, b) = _music(tmp_path, names=("a.mp3", "b.mp3"))
        scanner = StatScanner([a, b])
        extractor = CountingExtractor()
        pipeline = FakeScanPipeline()
        library, _ = _make_library(tmp_path, scanner, extractor, pipeline=pipeline)
        library.scan(str(music))  # a prior library via the sync path
        before = (
            tuple(library.state.tracks),
            library.state.albums,
            library.state.artists,
        )

        library.start_scan(str(music))
        generation, work, _, on_done = pipeline.submits[0]

        missing = music / "gone"
        error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=missing, detail="gone"
        )
        scanner.scan_error = error
        with pytest.raises(LibraryFilesystemError):
            work(ScanProgress(), ScanCancelToken(), lambda: None)

        on_done(generation, None, error)

        assert library.state.scan_status is LibraryScanStatus.FAILED
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING
        assert tuple(library.state.tracks) == before[0]  # tracks preserved
        assert library.state.albums == before[1]  # derived preserved
        assert library.state.artists == before[2]


class TestThreadRunner:
    def test_thread_scan_runner_smoke(self, qapp):
        from michi.infrastructure.scan_runner import ScanRelay, ThreadScanRunner

        relay = ScanRelay()
        runner = ThreadScanRunner(relay)
        done_entries = []
        progress_entries = []
        relay.done.connect(lambda gen, res, err: done_entries.append((gen, res, err)))
        relay.progress.connect(lambda gen, p: progress_entries.append(gen))

        def work(progress, token, report):
            progress.total = 1
            progress.processed = 1
            progress.current_path = "/tmp/fixed.mp3"
            report()
            return ScanResult(tracks=(TrackRef(file_path=Path("/tmp/fixed.mp3")),))

        runner.submit(1, work, lambda p: None, lambda g, r, e: None)

        # Bounded event-loop spin: the queued relay signal arrives on the
        # owner thread. Deadline 2s — the rest of the suite is deterministic.
        deadline = time.monotonic() + 2.0
        while not done_entries and time.monotonic() < deadline:
            QCoreApplication.processEvents()
            time.sleep(0.01)

        assert done_entries, "ThreadScanRunner did not deliver done within 2s"
        generation, result, error = done_entries[0]
        assert generation == 1
        assert error is None
        assert result is not None
        assert len(result.tracks) == 1
        assert progress_entries  # progress was relayed too
