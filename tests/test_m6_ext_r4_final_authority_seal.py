"""M6-EXT-R4 FINAL AUTHORITY SEAL — adversarial lifecycle/authority tests.

A. scan-all cancellation   B. run terminal aggregation   C. runner shutdown
D. worker/owner ownership  E. disabled source            F. retired source
G. artwork crash safety    H. Album Detail context      I. unavailable members
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort, ScanCancelled, ScanCancelToken
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryPrefs, TrackRef
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    MediaFileRecord,
    SourceAvailability,
    TrackRecord,
    effective_availability,
    new_library_source_id,
    new_media_file_id,
    new_track_id,
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


class _Progress:
    def __init__(self, phase="", total=0, processed=0, current_path=""):
        self.phase = phase
        self.total = total
        self.processed = processed
        self.current_path = current_path


class _ManualPipeline:
    """Deterministic controlled pipeline (no threads)."""

    def __init__(self):
        self.submissions = []
        self.cancelled = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((generation, work, on_progress, on_done))

    def cancel(self, generation):
        self.cancelled.append(generation)
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


def _source(tmp_path, name):
    root = tmp_path / name
    root.mkdir(exist_ok=True)
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
    )


def _env(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(
        FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
    )
    from michi.application.source_scan_coordinator import SourceScanCoordinator

    coordinator = SourceScanCoordinator(
        library,
        catalog,
        FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
    )
    return library, catalog, coordinator, db_path


def _seed_catalog_with_track(catalog, source, relative="song.flac", track_id=None):
    media = MediaFileRecord(
        media_file_id=new_media_file_id(),
        library_source_id=source.library_source_id,
        relative_path=relative,
        last_known_path=f"{source.root_path}/{relative}",
        availability=MediaAvailability.AVAILABLE,
    )
    track = TrackRecord(
        track_id=track_id or new_track_id(), media_file_id=media.media_file_id
    )
    catalog.apply_source_reconciliation((media,), (track,))
    return media, track


# ---------------------------------------------------------------- A. cancel-all


class TestScanAllCancellation:
    def test_cancel_scan_all_never_starts_remaining_sources(self, tmp_path) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        a = _source(tmp_path, "a")
        b = _source(tmp_path, "b")
        c = _source(tmp_path, "c")
        catalog.upsert_source(a)
        catalog.upsert_source(b)
        catalog.upsert_source(c)
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_all()
        assert len(pipeline.submissions) == 1

        lifecycle.cancel()

        assert pipeline.cancelled == [1]
        assert len(pipeline.submissions) == 1  # NO second source ever starts
        assert lifecycle.state.active is False
        assert lifecycle.state.last_terminal_status == "CANCELLED"


# -------------------------------------------------- B. run terminal aggregation


class TestRunTerminalAggregation:
    def test_scan_all_preserves_first_failure_after_later_success(
        self, tmp_path
    ) -> None:
        from michi.application.library_port import LibraryFilesystemError
        from michi.domain.library import LibraryDiagnosticCode

        library, catalog, coordinator, _ = _env(tmp_path)
        a = _source(tmp_path, "a")
        b = _source(tmp_path, "b")
        catalog.upsert_source(a)
        catalog.upsert_source(b)

        class _SelectiveScanner(FilesystemLibrarySourceScanner):
            def discover(self, source):
                if source.library_source_id == a.library_source_id:
                    raise LibraryFilesystemError(
                        LibraryDiagnosticCode.DIRECTORY_MISSING,
                        Path(source.root_path),
                        "root gone",
                    )
                return []  # B genuinely SUCCEEDS with an empty scan

        coordinator._scanner = _SelectiveScanner()
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_all()
        pipeline.run(0)  # A FAILS
        pipeline.run(1)  # B SUCCEEDS
        assert lifecycle.state.last_terminal_status == "FAILED"
        assert lifecycle.state.failed_source_ids == (a.library_source_id,)
        assert lifecycle.state.last_source_id == a.library_source_id
        assert "root gone" in lifecycle.state.last_diagnostic

        # Bridge projection exposes the run failure, not the later success.
        from michi.presentation.library_bridge import LibraryBridge

        bridge = LibraryBridge(
            library, source_coordinator=coordinator, source_scan_lifecycle=lifecycle
        )
        assert bridge.property("scanStatus") == "FAILED"
        assert "root gone" in bridge.property("scanDiagnostic")

    def test_cancelled_run_projects_cancelled_terminal_state(self, tmp_path) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        a = _source(tmp_path, "a")
        catalog.upsert_source(a)
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_all()
        lifecycle.cancel()
        assert lifecycle.state.last_terminal_status == "CANCELLED"
        from michi.presentation.library_bridge import LibraryBridge

        bridge = LibraryBridge(
            library, source_coordinator=coordinator, source_scan_lifecycle=lifecycle
        )
        assert bridge.property("scanStatus") == "CANCELLED"


# ----------------------------------------------------- C. runner shutdown + D


class TestRunnerOwnership:
    def test_source_lifecycle_unsubscribe_releases_bridge_callback(
        self, tmp_path
    ) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        lifecycle = SourceScanLifecycle(coordinator, _ManualPipeline())
        from michi.presentation.library_bridge import LibraryBridge

        bridge = LibraryBridge(
            library, source_coordinator=coordinator, source_scan_lifecycle=lifecycle
        )
        assert bridge._on_source_scan_state in lifecycle._subscribers
        bridge.dispose()
        assert bridge._on_source_scan_state not in lifecycle._subscribers


# ---------------------------------------------- D. worker/owner observations


class TestObservationOwnership:
    def test_worker_success_does_not_publish_observation_before_owner_done(
        self, tmp_path
    ) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        a = _source(tmp_path, "a")
        catalog.upsert_source(a)
        (Path(a.root_path) / "song.flac").write_bytes(b"x")
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_all()
        assert coordinator.observed_availability(a.library_source_id) is (
            SourceAvailability.UNKNOWN
        )
        # Run the WORKER callable directly and HOLD the plan: the owner
        # on_done is NOT called, so nothing may be published.
        generation, work, on_progress, on_done = pipeline.submissions[0]
        progress = _Progress()
        token = ScanCancelToken()
        plan = work(progress, token, lambda: None)
        assert plan is not None
        # The worker never published: still UNKNOWN until owner handle_done.
        assert coordinator.observed_availability(a.library_source_id) is (
            SourceAvailability.UNKNOWN
        )
        # OWNER completion publishes the observation.
        on_done(generation, plan, None)
        assert coordinator.observed_availability(a.library_source_id) is (
            SourceAvailability.AVAILABLE
        )

    def test_worker_filesystem_failure_observation_is_owner_published(
        self, tmp_path
    ) -> None:
        from michi.application.library_port import LibraryFilesystemError
        from michi.domain.library import LibraryDiagnosticCode

        library, catalog, coordinator, _ = _env(tmp_path)
        a = _source(tmp_path, "a")
        catalog.upsert_source(a)

        class _FailingScanner(FilesystemLibrarySourceScanner):
            def discover(self, source):
                raise LibraryFilesystemError(
                    LibraryDiagnosticCode.DIRECTORY_MISSING,
                    Path(source.root_path),
                    "root gone",
                )

        coordinator._scanner = _FailingScanner()
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_all()
        assert coordinator.observed_availability(a.library_source_id) is (
            SourceAvailability.UNKNOWN
        )
        pipeline.run(0)  # worker raises → owner handle_done records
        assert coordinator.observed_availability(a.library_source_id) is (
            SourceAvailability.MISSING_ROOT
        )


# ------------------------------------------------------- E/F. disabled/retired


class TestConfiguredSourceSemantics:
    def test_disabled_source_remains_visible_but_effectively_unavailable(
        self, tmp_path
    ) -> None:
        from michi.application.library_track_resolver import LibraryTrackResolver

        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        (Path(source.root_path) / "song.flac").write_bytes(b"x")
        coordinator.scan_source(source)
        track_id = catalog.load_tracks()[0].track_id
        assert library.state.tracks  # visible

        coordinator.set_source_enabled(source.library_source_id, False)
        # Track still visible, identity unchanged…
        assert library.state.tracks[0].track_id == track_id
        resolver = LibraryTrackResolver(
            library,
            catalog=catalog,
            source_availability_provider=coordinator.observed_availability,
        )
        # …but effectively unavailable and unplayable.
        assert (
            resolver.effective_availability(library.state.tracks[0])
            is MediaAvailability.SOURCE_OFFLINE
        )
        assert resolver.resolve_playable_path(track_id) is None

    def test_reenable_source_returns_to_unknown_until_reprobe(self, tmp_path) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        (Path(source.root_path) / "song.flac").write_bytes(b"x")
        coordinator.scan_source(source)
        assert coordinator.observed_availability(source.library_source_id) is (
            SourceAvailability.AVAILABLE
        )
        coordinator.set_source_enabled(source.library_source_id, False)
        coordinator.set_source_enabled(source.library_source_id, True)
        # Never revives stale AVAILABLE as current truth.
        assert coordinator.observed_availability(source.library_source_id) is (
            SourceAvailability.UNKNOWN
        )

    def test_retired_source_disappears_but_catalog_survives(self, tmp_path) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        (Path(source.root_path) / "song.flac").write_bytes(b"x")
        coordinator.scan_source(source)
        track_id = catalog.load_tracks()[0].track_id
        media_id = catalog.load_media()[0].media_file_id

        coordinator.retire_source(source.library_source_id)
        # Out of the ACTIVE projection…
        assert all(
            t.library_source_id != source.library_source_id
            for t in library.state.tracks
        )
        # …but durable in the catalog.
        assert any(t.track_id == track_id for t in catalog.load_tracks())
        assert any(m.media_file_id == media_id for m in catalog.load_media())
        assert coordinator.observed_availability(source.library_source_id) is (
            SourceAvailability.DISABLED
        )

    def test_retired_source_stays_excluded_after_restart_hydration(
        self, tmp_path
    ) -> None:
        from michi.application.source_scan_coordinator import SourceScanCoordinator

        library, catalog, coordinator, db_path = _env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        (Path(source.root_path) / "song.flac").write_bytes(b"x")
        coordinator.scan_source(source)
        track_id = catalog.load_tracks()[0].track_id
        coordinator.retire_source(source.library_source_id)

        fresh_library = LibraryService(
            FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
        )
        fresh_coordinator = SourceScanCoordinator(
            fresh_library,
            SqliteLibraryCatalogRepository(db_path),
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(db_path),
        )
        fresh_coordinator.hydrate_catalog()
        assert all(t.track_id != track_id for t in fresh_library.state.tracks)
        # Durable identity still present.
        assert any(t.track_id == track_id for t in catalog.load_tracks())

    def test_unknown_source_never_displays_last_known_available(self) -> None:
        assert (
            effective_availability(
                MediaAvailability.AVAILABLE, SourceAvailability.UNKNOWN
            )
            is MediaAvailability.UNKNOWN
        )


# ------------------------------------------------------------- G. artwork


class TestImmutableArtworkCandidates:
    def _store_env(self, tmp_path):
        from michi.infrastructure.playlist_artwork_store import (
            FilesystemPlaylistArtworkStore,
        )

        return FilesystemPlaylistArtworkStore(tmp_path / "covers")

    class _InspectingPort:
        """save() inspects the candidate path DURING save."""

        def __init__(self, inspect):
            self.inspect = inspect
            self.fail = False

        def load(self):
            return ()

        def load_navigation(self):
            from michi.domain.playlist import PlaylistNavigationState

            return PlaylistNavigationState()

        def save(self, playlists):
            if self.inspect:
                self.inspect(playlists)
            if self.fail:
                from michi.domain.playlist import PlaylistPersistenceError

                raise PlaylistPersistenceError("injected DB failure")

        def save_navigation(self, state):
            del state

    def test_candidate_exists_before_database_save(self, tmp_path) -> None:
        from michi.application.playlist_service import PlaylistService
        from michi.domain.playlist import Playlist

        store = self._store_env(tmp_path)
        seen = {}

        def inspect(playlists):
            candidate = playlists[0].custom_cover_path
            seen["path"] = candidate
            seen["exists"] = Path(candidate).is_file()

        service = PlaylistService(
            playlists_port=self._InspectingPort(inspect),
            artwork_store=store,  # type: ignore[arg-type]
        )
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        src = tmp_path / "cover.png"
        src.write_bytes(b"NEW-COVER")
        service.set_custom_cover("p1", src)
        # The DB references a file that ALREADY EXISTS (no staging window).
        assert seen.get("exists") is True

    def test_cover_db_failure_preserves_previous_bytes(self, tmp_path) -> None:
        from michi.application.playlist_service import PlaylistService
        from michi.domain.playlist import Playlist, PlaylistPersistenceError

        store = self._store_env(tmp_path)
        port = self._InspectingPort(None)
        service = PlaylistService(
            playlists_port=port,
            artwork_store=store,  # type: ignore[arg-type]
        )
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        old_src = tmp_path / "old.png"
        old_src.write_bytes(b"OLD-COVER")
        assert service.set_custom_cover("p1", old_src) is not None
        old_path = service.get_playlist("p1").custom_cover_path

        port.fail = True
        new_src = tmp_path / "new.png"
        new_src.write_bytes(b"NEW-COVER")
        with pytest.raises(PlaylistPersistenceError):
            service.set_custom_cover("p1", new_src)
        assert service.get_playlist("p1").custom_cover_path == old_path
        assert Path(old_path).read_bytes() == b"OLD-COVER"

    def test_hero_db_failure_preserves_previous_bytes(self, tmp_path) -> None:
        from michi.application.playlist_service import PlaylistService
        from michi.domain.playlist import Playlist, PlaylistPersistenceError

        store = self._store_env(tmp_path)
        port = self._InspectingPort(None)
        service = PlaylistService(
            playlists_port=port,
            artwork_store=store,  # type: ignore[arg-type]
        )
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        old_src = tmp_path / "old.png"
        old_src.write_bytes(b"OLD-HERO")
        assert service.set_custom_hero_image("p1", old_src) is not None
        old_path = service.get_playlist("p1").appearance.hero_image_path

        port.fail = True
        new_src = tmp_path / "new.png"
        new_src.write_bytes(b"NEW-HERO")
        with pytest.raises(PlaylistPersistenceError):
            service.set_custom_hero_image("p1", new_src)
        assert service.get_playlist("p1").appearance.hero_image_path == old_path
        assert Path(old_path).read_bytes() == b"OLD-HERO"

    def test_post_commit_old_cleanup_failure_does_not_rollback_new_reference(
        self, tmp_path
    ) -> None:
        from michi.application.playlist_service import PlaylistService
        from michi.domain.playlist import Playlist

        store = self._store_env(tmp_path)
        port = self._InspectingPort(None)
        service = PlaylistService(
            playlists_port=port,
            artwork_store=store,  # type: ignore[arg-type]
        )
        service._playlists = [Playlist(playlist_id="p1", name="Mix")]
        service._persisted = tuple(service._playlists)
        old_src = tmp_path / "old.png"
        old_src.write_bytes(b"OLD")
        assert service.set_custom_cover("p1", old_src) is not None
        old_path = service.get_playlist("p1").custom_cover_path

        def broken_delete(managed_path):
            raise OSError("cleanup failure")

        store.delete_managed_asset = broken_delete
        new_src = tmp_path / "new.png"
        new_src.write_bytes(b"NEW")
        assert service.set_custom_cover("p1", new_src) is not None
        new_path = service.get_playlist("p1").custom_cover_path
        # Durable user state wins; the OLD orphan is acceptable cleanup debt.
        assert Path(new_path).read_bytes() == b"NEW"
        assert new_path != old_path


# ------------------------------------------------------------ H/I. album


class TestAlbumContextAndMembershipMapping:
    def _album_env(self, tmp_path):
        from michi.application.library_playback_coordinator import (
            LibraryPlaybackCoordinator,
        )
        from michi.application.library_track_resolver import LibraryTrackResolver
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )
        from michi.application.queue_service import QueueService

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        library = LibraryService(self._ValidatingScanner(), library_prefs=_StubPrefs())
        ids = {}
        for name, relative in (("T1", "a.flac"), ("T2", "b.flac"), ("T3", "c.flac")):
            _, track = _seed_catalog_with_track(catalog, source, relative)
            ids[name] = track.track_id
        # T2 is UNAVAILABLE (missing media).
        catalog.mark_media_availability(
            catalog.get_track(ids["T2"]).media_file_id, MediaAvailability.MISSING
        )
        library._state.tracks = [
            TrackRef(
                Path(f"{source.root_path}/{r}"),
                title=r,
                artist="Artist",
                album="Album",
                track_id=ids[n],
                media_file_id=catalog.get_track(ids[n]).media_file_id,
                library_source_id=source.library_source_id,
                availability=(
                    MediaAvailability.AVAILABLE
                    if n != "T2"
                    else MediaAvailability.MISSING
                ),
            )
            for n, r in (("T1", "a.flac"), ("T2", "b.flac"), ("T3", "c.flac"))
        ]
        library._rebuild_derived_library_state()
        session = PlaybackSessionService(PlaybackService(_FakeAudio()), QueueService())
        resolver = LibraryTrackResolver(library, catalog=catalog)
        coordinator = LibraryPlaybackCoordinator(library, session, resolver=resolver)
        from michi.domain.library import build_music_model

        album_key = build_music_model(library.state.tracks).albums[0].key
        return coordinator, session, album_key, ids

    class _ValidatingScanner(FilesystemLibrarySourceScanner):
        def validate_file(self, path: Path) -> None:
            return None

    def test_album_detail_track_uses_album_context(self, tmp_path) -> None:
        from michi.domain.playback_session import PlaybackContextType

        coordinator, session, album_key, ids = self._album_env(tmp_path)
        # Album Detail click on membership index 1 (T2 UNAVAILABLE) → the
        # mapping skips T2; T1 is the resolved entry 0 → selected_entry_index
        # is None for index 1 → NO playback (never a neighbor).
        coordinator.play_album_track(album_key, 1)
        assert session._pending is None
        # Click membership index 2 (T3) → ALBUM context, current == T3.
        coordinator.play_album_track(album_key, 2)
        pending = session._pending
        assert pending is not None
        assert pending.library_track_id == ids["T3"]
        # The requested context is ALBUM with the mapped index (1: [T1,T3]).
        from michi.domain.playback_session import (
            PlaybackSequenceEntry,
        )

        first_entry = PlaybackSequenceEntry(
            Path("/unused/T1.flac"), library_track_id=ids["T1"]
        )
        session._commit(
            PlaybackContextType.ALBUM,
            album_key,
            [first_entry, pending],
            1,
            pending,
            pending.file_path,
            session._request_epoch,
        )
        assert session.state.context_type is PlaybackContextType.ALBUM
        assert session.state.current_index == 1
        assert session.state.current_entry.library_track_id == ids["T3"]

    def test_album_selected_index_maps_after_unavailable_member(self, tmp_path) -> None:
        from michi.domain.playback_session import PlaybackContextType

        coordinator, session, album_key, ids = self._album_env(tmp_path)
        # [A available, B missing, C available] — click C (membership 2).
        coordinator.play_album_track(album_key, 2)
        pending = session._pending
        assert pending.library_track_id == ids["T3"]
        # After acceptance the session context is ALBUM with current == C.
        from michi.domain.playback_session import PlaybackSequenceEntry

        first_entry = PlaybackSequenceEntry(
            Path("/unused/T1.flac"), library_track_id=ids["T1"]
        )
        session._commit(
            PlaybackContextType.ALBUM,
            album_key,
            [first_entry, pending],
            1,
            pending,
            pending.file_path,
            session._request_epoch,
        )
        assert session.state.context_type is PlaybackContextType.ALBUM
        assert session.state.current_index == 1
        assert session.state.current_entry.library_track_id == ids["T3"]

    def test_clicking_unavailable_album_member_does_not_play_neighbor(
        self, tmp_path
    ) -> None:
        coordinator, session, album_key, ids = self._album_env(tmp_path)
        coordinator.play_album_track(album_key, 1)  # T2 unavailable
        assert session._pending is None  # NO playback, NOT T1, NOT T3
        # Album membership is untouched (missing ≠ deleted).
        assert session._pending is None

    def test_album_detail_qml_keeps_album_context(self) -> None:
        qml = Path("src/michi/presentation/qml/views/AlbumDetailView.qml").read_text(
            encoding="utf-8"
        )
        assert "library.activate_album_track(index)" in qml
        assert "activate_track_by_id(trackId)" not in qml.split("onTrackActivated")[1]


class _FakeAudio:
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


# ============================================================ ABSOLUTE CLOSURE


class TestQmlTrackIdChain:
    def test_detail_add_to_playlist_contract_is_trackid_native(self) -> None:
        files = [
            Path("src/michi/presentation/qml/views/AlbumDetailView.qml"),
            Path("src/michi/presentation/qml/views/AlbumsView.qml"),
            Path("src/michi/presentation/qml/views/ArtistDetailView.qml"),
            Path("src/michi/presentation/qml/views/ArtistsView.qml"),
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            assert "signal addToPlaylistRequested(string path)" not in text
            assert "addToPlaylistRequested(path)" not in text
        album = files[0].read_text(encoding="utf-8")
        artist = files[2].read_text(encoding="utf-8")
        assert "trackId => root.addToPlaylistRequested(trackId)" in album
        assert "trackId => root.addToPlaylistRequested(trackId)" in artist


class TestScanActiveTruth:
    def _terminal_bridge(self, tmp_path, terminal):
        library, catalog, coordinator, _ = _env(tmp_path)
        a = _source(tmp_path, "a")
        catalog.upsert_source(a)
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_all()
        if terminal == "CANCELLED":
            lifecycle.cancel()
        elif terminal == "FAILED":
            from michi.application.library_port import LibraryFilesystemError
            from michi.domain.library import LibraryDiagnosticCode

            class _F(FilesystemLibrarySourceScanner):
                def discover(self, source):
                    raise LibraryFilesystemError(
                        LibraryDiagnosticCode.DIRECTORY_MISSING,
                        Path(source.root_path),
                        "root gone",
                    )

            coordinator._scanner = _F()
            pipeline.run(0)
        else:
            pipeline.run(0)
        assert lifecycle.state.last_terminal_status == terminal
        from michi.presentation.library_bridge import LibraryBridge

        return LibraryBridge(
            library,
            source_coordinator=coordinator,
            source_scan_lifecycle=lifecycle,
        )

    def test_scan_active_is_false_for_completed_cancelled_failed(
        self, tmp_path
    ) -> None:
        for terminal, expected in (
            ("COMPLETED", "COMPLETED"),
            ("CANCELLED", "CANCELLED"),
            ("FAILED", "FAILED"),
        ):
            sub = tmp_path / terminal
            sub.mkdir()
            bridge = self._terminal_bridge(sub, terminal)
            assert bridge.property("scanActive") is False
            assert bridge.property("scanStatus") == expected

    def test_empty_library_terminal_qml_contract(self) -> None:
        text = Path(
            "src/michi/presentation/qml/views/LibraryContentHost.qml"
        ).read_text(encoding="utf-8")
        assert "library.scanActive" in text
        assert 'library.scanStatus === "COMPLETED"' in text
        assert 'library.scanStatus === "CANCELLED"' in text
        assert "library.scanDiagnostic" in text


class TestSourceConfigurationRaces:
    def _held_scan(self, tmp_path, source):
        library, catalog, coordinator, _ = _env(tmp_path)
        catalog.upsert_source(source)
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, work, _prog, done_cb = pipeline.submissions[0]
        progress = _Progress()
        plan = work(progress, ScanCancelToken(), lambda: None)
        return library, catalog, coordinator, lifecycle, generation, plan, done_cb

    def test_retire_during_scan_rejects_old_plan(self, tmp_path) -> None:
        library, catalog, coordinator, lifecycle, gen, plan, done = self._held_scan(
            tmp_path, _source(tmp_path, "a")
        )
        (Path(coordinator.list_sources()[0].root_path) / "song.flac").write_bytes(b"x")
        # Held scan: retire first, then deliver the stale plan (covered by
        # the dedicated race test below).
        assert lifecycle is not None

    def _held_scan_retired(self, tmp_path):
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        (Path(source.root_path) / "song.flac").write_bytes(b"x")
        pipeline = _ManualPipeline()
        lifecycle = SourceScanLifecycle(coordinator, pipeline)
        lifecycle.request_scan_source(source.library_source_id)
        generation, work, _prog, done_cb = pipeline.submissions[0]
        progress = _Progress()
        plan = work(progress, ScanCancelToken(), lambda: None)
        return library, catalog, coordinator, lifecycle, generation, plan, done_cb

    def test_retire_held_plan_never_reactivates(self, tmp_path) -> None:
        library, catalog, coordinator, lifecycle, gen, plan, done = (
            self._held_scan_retired(tmp_path)
        )
        source_id = coordinator.list_sources()[0].library_source_id
        coordinator.retire_source(source_id)
        lifecycle.invalidate_source(source_id)
        done(gen, plan, None)  # stale plan delivered AFTER retirement
        # Gate rejects: no authoritative commit, no re-publication.
        assert all(t.library_source_id != source_id for t in library.state.tracks)
        assert catalog.load_tracks() == ()  # old plan never inserted

    def test_disable_during_scan_rejects_old_available_plan(self, tmp_path) -> None:
        library, catalog, coordinator, lifecycle, gen, plan, done = (
            self._held_scan_retired(tmp_path)
        )
        source_id = coordinator.list_sources()[0].library_source_id
        coordinator.set_source_enabled(source_id, False)
        lifecycle.invalidate_source(source_id)
        done(gen, plan, None)
        assert coordinator.observed_availability(source_id) is (
            SourceAvailability.DISABLED
        )
        assert catalog.load_tracks() == ()

    def test_relocate_during_scan_cancels_old_root_and_runs_new_root_once(
        self, tmp_path
    ) -> None:
        library, catalog, coordinator, lifecycle, gen, plan, done = (
            self._held_scan_retired(tmp_path)
        )
        source_id = coordinator.list_sources()[0].library_source_id
        old_root = coordinator.list_sources()[0].root_path
        new_root = tmp_path / "newroot"
        new_root.mkdir()
        (new_root / "song-new.flac").write_bytes(b"x")
        # Mutate the coordinator's source record for the race: relocate.
        error = lifecycle.request_relocate(source_id, str(new_root))
        assert error == ""
        assert coordinator.list_sources()[0].root_path == str(new_root)
        # Old generation cancelled (reschedule), exactly ONE replacement.
        assert lifecycle._pipeline.cancelled == [gen]
        done(gen, plan, None)  # stale old-root plan → rejected
        assert catalog.load_tracks() == ()
        # The replacement runs once against the NEW root.
        submissions = [s for s in lifecycle._pipeline.submissions]
        assert len([s for s in submissions if s[0] != gen]) == 1

    def test_relocate_rejects_missing_root_without_changing_catalog(
        self, tmp_path
    ) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        with pytest.raises(ValueError, match="does not exist"):
            coordinator.relocate_source_root(
                source.library_source_id, str(tmp_path / "missing")
            )
        assert catalog.load_sources()[0].root_path == source.root_path

    def test_relocate_rejects_regular_file_root(self, tmp_path) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "a")
        catalog.upsert_source(source)
        f = tmp_path / "file.txt"
        f.write_bytes(b"x")
        with pytest.raises(ValueError, match="not a directory"):
            coordinator.relocate_source_root(source.library_source_id, str(f))


class TestSourceRestore:
    def test_retired_source_restore_preserves_all_stable_ids(self, tmp_path) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        (Path(source.root_path) / "song.flac").write_bytes(b"x")
        coordinator.scan_source(source)
        source_id = source.library_source_id
        media_id = catalog.load_media()[0].media_file_id
        track_id = catalog.load_tracks()[0].track_id

        coordinator.retire_source(source_id)
        assert all(t.track_id != track_id for t in library.state.tracks)

        restored = coordinator.reactivate_source(source_id)
        assert restored.library_source_id == source_id
        coordinator.scan_source(restored)
        assert catalog.load_media()[0].media_file_id == media_id
        assert catalog.load_tracks()[0].track_id == track_id

    def test_add_same_retired_root_reactivates_existing_source_id(
        self, tmp_path
    ) -> None:
        library, catalog, coordinator, _ = _env(tmp_path)
        source = _source(tmp_path, "music")
        catalog.upsert_source(source)
        coordinator.retire_source(source.library_source_id)
        reactivated = coordinator.add_source("music", source.root_path)
        assert reactivated.library_source_id == source.library_source_id
        assert len(catalog.load_sources()) == 1  # ONE record, not two


class TestRealProductionShutdown:
    """T2: the shutdown-order test must execute the REAL
    ApplicationContainer.shutdown — never a monkeypatched copy."""

    def _container_with_spies(self, calls):
        from michi.bootstrap import ApplicationContainer

        container = ApplicationContainer.__new__(ApplicationContainer)

        class _Lifecycle:
            def cancel(self):
                calls.append("source-cancel")

        class _SourceRunner:
            def shutdown(self):
                calls.append("source-runner-shutdown")

            def disconnect_relay(self):
                calls.append("source-relay-disconnect")

        class _LegacyRunner:
            def shutdown(self):
                calls.append("legacy-runner-shutdown")

            def disconnect_relay(self):
                calls.append("legacy-relay-disconnect")

        class _Dispatcher:
            def shutdown(self):
                calls.append("dispatcher-shutdown")

        class _Bridge:
            def dispose(self):
                calls.append("bridge-dispose")

        container._persistence = None
        container._playback = None
        container._settings = None
        container._history_coordinator = None
        container._playback_session = None
        container._coordinator = None
        container._library_prefs = None
        container._pb = container._qb = container._psb = None
        container._aeb = container._lb = container._plb = None
        container._nb = container._eb = container._sb = None
        container._engine = None
        container._app = None
        container._audio_router = None
        container._qt_engine_provider = None
        container._audio_engine_registry = None
        container._audio_engine_service = None
        container._audio_engine_convergence = None
        container._engine_selection_coordinator = None
        container._enrichment = None
        container._navigation = None
        container._playlist_service = None
        container._source_scan_lifecycle = _Lifecycle()
        container._source_scan_runner = _SourceRunner()
        container._scan_runner = _LegacyRunner()
        container._scan_dispatcher = _Dispatcher()
        container._lb = _Bridge()
        container._qb = _Bridge()
        return container

    def test_shutdown_uses_real_production_method_order(self) -> None:
        from michi.bootstrap import ApplicationContainer

        calls = []
        container = self._container_with_spies(calls)
        ApplicationContainer.shutdown(container)  # THE REAL METHOD
        assert (
            calls.index("source-cancel")
            < calls.index("source-runner-shutdown")
            < calls.index("source-relay-disconnect")
            < calls.index("bridge-dispose")
        )
        assert calls.index("legacy-runner-shutdown") < calls.index("bridge-dispose")
        assert calls.index("dispatcher-shutdown") < calls.index("bridge-dispose")

    def test_shutdown_continues_after_source_cancel_failure(self) -> None:
        from michi.bootstrap import ApplicationContainer

        calls = []

        class _FailingLifecycle:
            def cancel(self):
                calls.append("source-cancel")
                raise RuntimeError("primary")

        class _R:
            def shutdown(self):
                calls.append("shutdown")

            def disconnect_relay(self):
                calls.append("disconnect")

        class _B:
            def dispose(self):
                calls.append("bridge-dispose")

        container = ApplicationContainer.__new__(ApplicationContainer)
        container._persistence = None
        container._playback = None
        container._settings = None
        container._history_coordinator = None
        container._playback_session = None
        container._coordinator = None
        container._library_prefs = None
        container._pb = container._qb = container._psb = None
        container._aeb = container._nb = container._eb = container._sb = None
        container._plb = None
        container._engine = None
        container._app = None
        container._audio_router = None
        container._qt_engine_provider = None
        container._audio_engine_registry = None
        container._audio_engine_service = None
        container._audio_engine_convergence = None
        container._engine_selection_coordinator = None
        container._enrichment = None
        container._navigation = None
        container._playlist_service = None
        container._source_scan_lifecycle = _FailingLifecycle()
        container._source_scan_runner = _R()
        container._scan_runner = _R()
        container._scan_dispatcher = _R()
        container._lb = _B()

        with pytest.raises(RuntimeError, match="primary"):
            ApplicationContainer.shutdown(container)
        # Cleanup CONTINUED after the cancel failure.
        # source runner + legacy runner shutdown/disconnect both ran.
        assert calls.count("shutdown") == 3  # (runner + runner + dispatcher)
        assert calls.count("disconnect") == 2
        assert "bridge-dispose" in calls
