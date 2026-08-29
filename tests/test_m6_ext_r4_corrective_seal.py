"""M6-EXT-R4 FINAL CORRECTIVE SEAL — adversarial tests.

§1 Locate Source async (zero sync heavy work, exactly one scan).
§2 Unified cancel intent.
§3 Unified scan status/progress projection.
§4 Cancellation during metadata extraction cannot commit.
§5 Isolated relay/runner provenance.
§6 Terminal failure state stays observable.
"""

import os
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort, ScanCancelToken
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


class _StubPrefs(LibraryPrefsPort):
    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        del prefs


class _BlockingMetadata:
    """Blocks the FIRST extraction call until released (deterministic
    cancel-during-extraction)."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def extract(self, file_path: Path) -> TrackMetadata:
        self.calls += 1
        if self.calls == 1:
            self.entered.set()
            if not self.release.wait(timeout=10):
                raise TimeoutError("test never released the extractor")
        return TrackMetadata(title=file_path.stem, artist="A", album="B")


def _source(tmp_path, name: str, files=("song.flac",)) -> LibrarySource:
    root = tmp_path / name
    root.mkdir()
    for f in files:
        (root / f).write_bytes(b"x")
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
    )


class _SyncPipeline:
    def __init__(self):
        self.cancelled = []

    def submit(self, generation, work, on_progress, on_done):
        progress = _Progress()
        token = ScanCancelToken()
        try:
            plan = work(progress, token, lambda: None)
        except BaseException as exc:  # noqa: BLE001
            on_done(generation, None, exc)
            return
        on_done(generation, plan, None)

    def cancel(self, generation):
        self.cancelled.append(generation)


def _sync_pipeline():
    return _SyncPipeline()


class _Progress:
    def __init__(self, phase="", total=0, processed=0, current_path=""):
        self.phase = phase
        self.total = total
        self.processed = processed
        self.current_path = current_path


class _HoldingPipeline(_SyncPipeline):
    """Keeps the scan ACTIVE until released (deterministic cancel/progress)."""

    def __init__(self):
        super().__init__()
        self.release_work = threading.Event()
        self.entered_work = threading.Event()

    def submit(self, generation, work, on_progress, on_done):
        self.cancelled.clear()

        def run():
            progress = _Progress()
            token = ScanCancelToken()
            self.entered_work.set()
            if not self.release_work.wait(timeout=10):
                raise TimeoutError("test never released the scan")
            try:
                plan = work(progress, token, lambda: None)
            except BaseException as exc:  # noqa: BLE001
                on_done(generation, None, exc)
                return
            on_done(generation, plan, None)

        threading.Thread(target=run, daemon=True).start()

    def cancel(self, generation):
        self.cancelled.append(generation)
        self.release_work.set()


class TestLocateSourceAsync:
    def _env(self, tmp_path):
        from michi.application.source_scan_coordinator import SourceScanCoordinator

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        library = LibraryService(
            FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
        )
        coordinator = SourceScanCoordinator(
            library,
            catalog,
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(db_path),
            metadata_extractor=_BlockingMetadata(),
        )
        return library, catalog, coordinator

    def test_a_locate_returns_before_slow_scan_and_scans_exactly_once(
        self, tmp_path
    ) -> None:
        """Locate must return immediately and enqueue ONE async scan."""
        library, catalog, coordinator = self._env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        submitted = []

        class _CountingPipeline(_SyncPipeline):
            def submit(self, generation, work, on_progress, on_done):
                submitted.append(generation)
                super().submit(generation, work, on_progress, on_done)

        pipeline = _CountingPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        started = time.monotonic()
        error = lifecycle.request_relocate(
            source.library_source_id, str(tmp_path / "newroot")
        )
        elapsed = time.monotonic() - started
        assert error == ""
        # Zero heavy work: the root remap is a single cheap upsert.
        assert elapsed < 0.5
        # EXACTLY ONE async reconciliation enqueued.
        assert len(submitted) == 1

    def test_c_root_updated_before_async_scan(self, tmp_path) -> None:
        library, catalog, coordinator = self._env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        pipeline = _sync_pipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_relocate(source.library_source_id, str(tmp_path / "newroot"))
        # The catalog root is ALREADY updated (the scan only reconciles).
        assert catalog.load_sources()[0].root_path == str(tmp_path / "newroot")

    def test_e_overlap_still_rejected(self, tmp_path) -> None:
        library, catalog, coordinator = self._env(tmp_path)
        a = _source(tmp_path, "a")
        b = _source(tmp_path, "b")
        catalog.upsert_source(a)
        catalog.upsert_source(b)
        # Relocating A inside B's root must be rejected (overlap policy).
        inside_b = tmp_path / "b" / "sub"
        inside_b.mkdir()
        pipeline = _sync_pipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        error = lifecycle.request_relocate(a.library_source_id, str(inside_b))
        assert "overlap" in error.lower()
        assert catalog.load_sources()[0].root_path == str(tmp_path / "a")


class TestUnifiedCancel:
    def test_bridge_cancel_cancels_source_lifecycle(self, tmp_path) -> None:
        from michi.application.source_scan_coordinator import SourceScanCoordinator
        from michi.presentation.library_bridge import LibraryBridge

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        library = LibraryService(
            FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
        )
        coordinator = SourceScanCoordinator(
            library,
            catalog,
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(db_path),
            metadata_extractor=_BlockingMetadata(),
        )
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        pipeline = _HoldingPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        bridge = LibraryBridge(
            library, source_coordinator=coordinator, source_scan_lifecycle=lifecycle
        )
        bridge.scan_all_sources()
        assert pipeline.entered_work.wait(timeout=5)
        assert lifecycle.state.active is True
        bridge.cancel_scan()  # UNIFIED intent: cancels the SOURCE lifecycle
        deadline = time.monotonic() + 5
        while lifecycle.state.active and time.monotonic() < deadline:
            time.sleep(0.005)
        assert pipeline.cancelled  # the SOURCE generation token was cancelled
        # No authoritative commit ever happened.
        assert catalog.load_tracks() == ()
        assert library.state.tracks == []


class TestUnifiedProgressProjection:
    def test_bridge_projects_source_progress(self, tmp_path) -> None:
        from michi.application.source_scan_coordinator import SourceScanCoordinator
        from michi.presentation.library_bridge import LibraryBridge

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        library = LibraryService(
            FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
        )
        coordinator = SourceScanCoordinator(
            library,
            catalog,
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(db_path),
        )
        source = _source(
            tmp_path, "music", files=tuple(f"s{i}.flac" for i in range(10))
        )
        catalog.upsert_source(source)

        class _ControlledPipeline:
            def __init__(self):
                self.current = None

            def submit(self, generation, work, on_progress, on_done):
                self.current = (generation, work, on_progress, on_done)

            def cancel(self, generation):
                del generation

        pipeline = _HoldingPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        bridge = LibraryBridge(
            library, source_coordinator=coordinator, source_scan_lifecycle=lifecycle
        )
        bridge.scan_all_sources()
        assert pipeline.entered_work.wait(timeout=5)
        # Owner-thread progress for the ACTIVE source scan.
        lifecycle.handle_progress(
            lifecycle._generation,
            _Progress(
                phase="RECONCILING", total=10, processed=3, current_path="/Music/A.flac"
            ),
        )
        # The UNIFIED projection exposes the SOURCE values, not legacy idle.
        assert bridge.property("scanStatus") == "RECONCILING"
        assert bridge.property("scanProcessed") == 3
        assert bridge.property("scanTotal") == 10
        assert bridge.property("scanCurrentPath") == "/Music/A.flac"
        assert bridge.property("scanProgress") == pytest.approx(0.3)


class TestCancelDuringExtraction:
    def test_cancel_mid_extraction_never_commits(self, tmp_path) -> None:
        """§4 deterministic: discover completes; the FIRST metadata
        extraction blocks; cancel; reconciliation resumes; ScanCancelled;
        ZERO catalog commit; ZERO publication."""
        from michi.application.source_scan_coordinator import SourceScanCoordinator

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        extractor = _BlockingMetadata()
        library = LibraryService(
            FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
        )
        coordinator = SourceScanCoordinator(
            library,
            catalog,
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(db_path),
            metadata_extractor=extractor,
        )
        source = _source(tmp_path, "music", files=("a.flac", "b.flac", "c.flac"))
        catalog.upsert_source(source)

        class _ExtractionPipeline:
            def __init__(self):
                self.token = None

            def submit(self, generation, work, on_progress, on_done):
                progress = _Progress()
                self.token = ScanCancelToken()

                # Run the work on a worker thread (deterministic handoff).
                def run():
                    try:
                        plan = work(progress, self.token, lambda: None)
                    except BaseException as exc:  # noqa: BLE001
                        on_done(generation, None, exc)
                        return
                    on_done(generation, plan, None)

                threading.Thread(target=run, daemon=True).start()

            def cancel(self, generation):
                del generation
                self.token.cancelled = True

        pipeline = _ExtractionPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_all()
        # Wait until extraction BEGAN (discover complete, extraction blocked).
        assert extractor.entered.wait(timeout=5)
        lifecycle.cancel()
        extractor.release.set()
        # Wait for the async completion.
        deadline = time.monotonic() + 5
        while lifecycle.state.active and time.monotonic() < deadline:
            time.sleep(0.005)
        # Cancelled during extraction → ZERO authoritative mutation.
        assert catalog.load_tracks() == ()
        assert library.state.tracks == []
        # P1-03: a cancelled run exposes the CANCELLED terminal truth.
        assert lifecycle.state.last_terminal_status == "CANCELLED"


class TestIsolatedProvenance:
    def test_bootstrap_uses_two_isolated_relays(self, tmp_path) -> None:
        from michi.bootstrap import _build_services

        class _FakeBackend:
            def load(self, file_path): ...
            def play(self): ...
            def pause(self): ...
            def resume(self): ...
            def stop(self): ...
            def set_volume(self, value): ...
            def set_muted(self, muted): ...
            def seek(self, position_ms): ...
            def position(self):
                return 0

            def duration(self):
                return 0

            def subscribe_end_of_media(self, cb): ...
            def unsubscribe_end_of_media(self, cb): ...
            def subscribe_position_changed(self, cb): ...
            def unsubscribe_position_changed(self, cb): ...
            def subscribe_duration_changed(self, cb): ...
            def unsubscribe_duration_changed(self, cb): ...
            def subscribe_media_accepted(self, cb): ...
            def unsubscribe_media_accepted(self, cb): ...
            def subscribe_media_rejected(self, cb): ...
            def unsubscribe_media_rejected(self, cb): ...
            def subscribe_playback_state_changed(self, cb): ...
            def unsubscribe_playback_state_changed(self, cb): ...

        graph = _build_services(tmp_path / "michi.db", backend=_FakeBackend())
        # Structurally distinct relay/runner instances.
        assert graph.source_scan_runner is not graph.runner
        assert graph.relay is not graph.source_scan_runner._relay
        # The source lifecycle is wired to ITS OWN runner.
        assert graph.source_scan_lifecycle._pipeline is graph.source_scan_runner


class TestTerminalFailureObservable:
    def test_directory_missing_stays_observable(self, tmp_path) -> None:
        from michi.application.library_port import LibraryFilesystemError
        from michi.application.source_scan_coordinator import SourceScanCoordinator
        from michi.domain.library import LibraryDiagnosticCode

        class _Broken(FilesystemLibrarySourceScanner):
            def discover(self, source):
                raise LibraryFilesystemError(
                    LibraryDiagnosticCode.DIRECTORY_MISSING,
                    Path(source.root_path),
                    "root gone",
                )

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        library = LibraryService(_Broken(), library_prefs=_StubPrefs())
        coordinator = SourceScanCoordinator(library, catalog, _Broken())
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        pipeline = _sync_pipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_all()
        # The terminal failure REMAINS observable after the callback.
        assert lifecycle.state.status == "IDLE"
        assert lifecycle.state.last_terminal_status == "FAILED"
        assert "root gone" in lifecycle.state.last_diagnostic
        assert lifecycle.state.last_source_id == source.library_source_id


class TestTrackIdFirstIntents:
    """CORRECTIVE SEAL §11/§12: identity-sensitive intents send TrackId and
    never infer a TrackId to be a path."""

    def test_track_id_validation_accepts_moved_track(self, tmp_path) -> None:
        from michi.application.library_collection_coordinators import (
            LibraryPlaylistCoordinator,
            LibraryQueueCoordinator,
        )
        from michi.application.library_playback_coordinator import (
            LibraryPlaybackCoordinator,
        )
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )
        from michi.application.playlist_service import PlaylistService
        from michi.application.queue_service import QueueService
        from michi.domain.library_catalog import (
            LibrarySource,
            MediaAvailability,
            MediaFileRecord,
            TrackRecord,
            new_library_source_id,
            new_media_file_id,
            new_track_id,
        )
        from michi.presentation.library_bridge import LibraryBridge

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="S",
            root_path="/Music",
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="A.flac",
            last_known_path="/Music/A.flac",
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))
        library = LibraryService(
            _StubPrefs() if False else FilesystemLibrarySourceScanner(),
            library_prefs=_StubPrefs(),
        )
        library._state.tracks = [
            __import__("michi.domain.library", fromlist=["TrackRef"]).TrackRef(
                Path("/Music/NEW/A.flac"),  # moved path
                title="A",
                track_id=track.track_id,
                media_file_id=media.media_file_id,
                library_source_id=source.library_source_id,
                availability=MediaAvailability.AVAILABLE,
            )
        ]
        library._rebuild_derived_library_state()
        queue = QueueService()
        playlists = PlaylistService()
        session = PlaybackSessionService(PlaybackService(_FakeAudio()), queue)
        bridge = LibraryBridge(
            library,
            playback_coordinator=LibraryPlaybackCoordinator(library, session),
            queue_coordinator=LibraryQueueCoordinator(library, queue),
            playlist_coordinator=LibraryPlaylistCoordinator(library, playlists),
        )
        # The moved TrackId is ACCEPTED by the TrackId-first validation.
        bridge.request_tracks_playlist_target([track.track_id])
        # A UUID-string that looks nothing like a path still validates.
        assert bridge._track_id_resolvable(track.track_id) is True
        # An unknown id is rejected; a raw path is NOT inferred from ids.
        assert bridge._track_id_resolvable("no-such-id") is False

    class _ValidatingScanner(FilesystemLibrarySourceScanner):
        def validate_file(self, path: Path) -> None:
            return None

    def test_playlist_playback_resolves_current_path_for_moved_track(
        self, tmp_path
    ) -> None:
        from michi.application.library_playback_coordinator import (
            LibraryPlaybackCoordinator,
        )
        from michi.application.library_track_resolver import LibraryTrackResolver
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )
        from michi.application.queue_service import QueueService
        from michi.domain.library import TrackRef as TrackRefModel
        from michi.domain.library_catalog import (
            LibrarySource,
            MediaAvailability,
            MediaFileRecord,
            TrackRecord,
            new_library_source_id,
            new_media_file_id,
            new_track_id,
        )

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(), display_name="S", root_path="/"
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="a.flac",
            last_known_path="/Old/a.flac",
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))
        library = LibraryService(self._ValidatingScanner(), library_prefs=_StubPrefs())
        library._state.tracks = [
            TrackRefModel(
                Path("/New/a.flac"),
                title="a",
                track_id=track.track_id,
                media_file_id=media.media_file_id,
                library_source_id=source.library_source_id,
                availability=MediaAvailability.AVAILABLE,
            )
        ]
        library._rebuild_derived_library_state()
        session = PlaybackSessionService(PlaybackService(_FakeAudio()), QueueService())
        coordinator = LibraryPlaybackCoordinator(
            library, session, resolver=LibraryTrackResolver(library)
        )
        # play_album via TrackId membership (moved album member).
        from michi.domain.library import build_music_model

        album_key = build_music_model(library.state.tracks).albums[0].key
        coordinator.play_album(album_key)
        pending = session._pending
        assert pending is not None
        assert pending.file_path == Path("/New/a.flac")
        assert pending.library_track_id == track.track_id


class _FakeAudio:
    """Minimal AudioPort fake for playback intents."""

    def load(self, file_path): ...
    def play(self): ...
    def pause(self): ...
    def resume(self): ...
    def stop(self): ...
    def set_volume(self, value): ...
    def set_muted(self, muted): ...
    def seek(self, position_ms): ...
    def position(self):
        return 0

    def duration(self):
        return 0

    def subscribe_end_of_media(self, cb): ...
    def unsubscribe_end_of_media(self, cb): ...
    def subscribe_position_changed(self, cb): ...
    def unsubscribe_position_changed(self, cb): ...
    def subscribe_duration_changed(self, cb): ...
    def unsubscribe_duration_changed(self, cb): ...
    def subscribe_media_accepted(self, cb): ...
    def unsubscribe_media_accepted(self, cb): ...
    def subscribe_media_rejected(self, cb): ...
    def unsubscribe_media_rejected(self, cb): ...
    def subscribe_playback_state_changed(self, cb): ...
    def unsubscribe_playback_state_changed(self, cb): ...
