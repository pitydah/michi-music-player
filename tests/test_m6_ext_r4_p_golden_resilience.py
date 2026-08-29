"""M6-EXT-R4-P — golden end-to-end resilience scenarios (prompt §90-94)."""

import sqlite3
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort, SessionRepository
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.domain.library import LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    new_library_source_id,
)
from michi.domain.session import (
    PersistedQueueEntry,
    PersistedSessionContext,
    PlaybackSessionSnapshot,
    RepeatMode,
    encode_snapshot,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_index import SqliteLibraryIndexRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache


class _StubPrefs(LibraryPrefsPort):
    def __init__(self) -> None:
        self.saved: list[LibraryPrefs] = []

    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        self.saved.append(prefs)


class _StubMetadata:
    def extract(self, file_path: Path):
        from michi.domain.library import TrackMetadata

        return TrackMetadata(
            title=file_path.stem,
            artist=file_path.parent.name,
            album="Album",
            duration_ms=1000,
        )


def _env(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    media_cache = SqliteLibraryMediaCache(db_path)
    index = SqliteLibraryIndexRepository(db_path)
    scanner = FilesystemLibrarySourceScanner()
    library = LibraryService(
        scanner, metadata_extractor=_StubMetadata(), library_prefs=_StubPrefs()
    )
    coordinator = SourceScanCoordinator(
        library,
        catalog,
        scanner,
        media_cache=media_cache,
        metadata_extractor=_StubMetadata(),
        index=index,
    )
    return library, catalog, coordinator, scanner, tmp_path, db_path


def _source(tmp_path, name="nas") -> LibrarySource:
    root = tmp_path / name
    root.mkdir()
    source = LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=str(root),
    )
    return source


class TestGoldenOfflineBrowse:
    def test_offline_startup_browses_cached_library_and_searches(
        self, tmp_path
    ) -> None:
        # 1. Scan while online (NAS present) → catalog + metadata cache.
        library, catalog, coordinator, scanner, tmp, db_path = _env(tmp_path)
        source = _source(tmp)
        catalog.upsert_source(source)
        root = Path(source.root_path)
        (root / "Miles").mkdir()
        (root / "Miles" / "Blue In Green.flac").write_bytes(b"x")
        coordinator.scan_source(source)
        assert len(library.state.tracks) == 1

        # 2. "Disconnect" the NAS and start the app fresh: hydration loads
        # the catalog WITHOUT any scan.
        import shutil

        shutil.rmtree(root)
        fresh_library = LibraryService(
            FilesystemLibrarySourceScanner(),
            metadata_extractor=_StubMetadata(),
            library_prefs=_StubPrefs(),
        )
        fresh_catalog = SqliteLibraryCatalogRepository(db_path)
        fresh_index = SqliteLibraryIndexRepository(db_path)
        fresh_coordinator = SourceScanCoordinator(
            fresh_library,
            fresh_catalog,
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(db_path),
            metadata_extractor=_StubMetadata(),
            index=fresh_index,
        )
        count = fresh_coordinator.hydrate_catalog()

        assert count == 1
        track = fresh_library.state.tracks[0]
        assert track.track_id  # identity preserved
        assert track.title == "Blue In Green"  # cached metadata preserved
        assert track.availability is MediaAvailability.AVAILABLE  # last observation
        # No TrackIds removed, album model present.
        assert fresh_library.state.albums

        # 3. M7 search still finds the offline cached track.
        fresh_library.search("miles")
        assert fresh_library.state.search_projection is not None
        assert fresh_library.state.search_active
        assert len(fresh_library.state.search_projection.tracks) == 1

    def test_offline_hydration_preserves_missing_observation(self, tmp_path) -> None:
        library, catalog, coordinator, scanner, tmp, db_path = _env(tmp_path)
        source = _source(tmp)
        catalog.upsert_source(source)
        path = Path(source.root_path) / "song.flac"
        path.write_bytes(b"x")
        coordinator.scan_source(source)
        path.unlink()
        coordinator.scan_source(source)  # now MISSING

        fresh_library = LibraryService(
            FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
        )
        fresh_coordinator = SourceScanCoordinator(
            fresh_library,
            SqliteLibraryCatalogRepository(db_path),
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(db_path),
            metadata_extractor=_StubMetadata(),
            index=SqliteLibraryIndexRepository(db_path),
        )
        fresh_coordinator.hydrate_catalog()
        assert fresh_library.state.tracks[0].availability is MediaAvailability.MISSING


class TestGoldenRecentlyAdded:
    def test_recently_added_ignores_move_modify_relink(self, tmp_path) -> None:
        library, catalog, coordinator, scanner, tmp, db_path = _env(tmp_path)
        source = _source(tmp)
        catalog.upsert_source(source)
        root = Path(source.root_path)
        path = root / "song.flac"
        path.write_bytes(b"old")
        coordinator.scan_source(source)
        recent_after_first = library.state.recently_added_paths
        assert len(recent_after_first) == 1  # the NEW track

        # Modify in place → NOT recently added again.
        import time

        time.sleep(0.01)
        path.write_bytes(b"new bytes")
        coordinator.scan_source(source)
        assert library.state.recently_added_paths == recent_after_first

        # Move (relink) → NOT recently added again.
        target_dir = root / "B"
        target_dir.mkdir()
        path.rename(target_dir / "song.flac")
        coordinator.scan_source(source)
        assert library.state.recently_added_paths == recent_after_first

        # A genuinely NEW unknown file → new TrackId → recently added.
        (root / "brand-new.flac").write_bytes(b"x")
        coordinator.scan_source(source)
        # The moved track did NOT re-enter recently added (its old-path
        # legacy entry falls out when the path moves — the TrackId-keyed
        # user state preserves it); the brand-new file IS recent.
        assert str(root / "brand-new.flac") in library.state.recently_added_paths
        assert str(target_dir / "song.flac") not in library.state.recently_added_paths


class TestGoldenSessionV3Restore:
    def test_restored_session_resolves_moved_track_by_identity(self, tmp_path) -> None:
        library, catalog, coordinator, scanner, tmp, db_path = _env(tmp_path)
        source = _source(tmp)
        catalog.upsert_source(source)
        root = Path(source.root_path)
        path = root / "A" / "song.flac"
        path.parent.mkdir()
        path.write_bytes(b"x")
        coordinator.scan_source(source)
        track_id = catalog.load_tracks()[0].track_id

        # Persist a V3 snapshot referencing the stable id at the OLD path.
        snapshot = PlaybackSessionSnapshot(
            format_version=3,
            queue_entries=(PersistedQueueEntry(str(path), "song", track_id),),
            context=PersistedSessionContext(
                context_type="queue",
                source_id=None,
                entries=(PersistedQueueEntry(str(path), "song", track_id),),
                current_index=0,
            ),
            playback_path=str(path),
            position_ms=100,
            repeat_mode=RepeatMode.NONE,
            shuffle_enabled=False,
            shuffle_seed=0,
        )
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('session_snapshot', ?)",
            (encode_snapshot(snapshot),),
        )
        conn.commit()
        conn.close()

        # The file MOVED before restart.
        target_dir = root / "B"
        target_dir.mkdir()
        path.rename(target_dir / "song.flac")
        coordinator.scan_source(source)
        new_path = root / "B" / "song.flac"
        assert catalog.load_tracks()[0].track_id == track_id

        # Restart: hydrate + restore → the CURRENT path resolves by identity.
        from michi.application.persistence_coordinator import PersistenceCoordinator
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import PlaybackSessionService
        from michi.application.queue_service import QueueService

        fresh_library = LibraryService(
            FilesystemLibrarySourceScanner(), library_prefs=_StubPrefs()
        )
        fresh_catalog = SqliteLibraryCatalogRepository(db_path)
        fresh_coordinator = SourceScanCoordinator(
            fresh_library,
            fresh_catalog,
            FilesystemLibrarySourceScanner(),
            media_cache=SqliteLibraryMediaCache(db_path),
            metadata_extractor=_StubMetadata(),
            index=SqliteLibraryIndexRepository(db_path),
        )
        fresh_coordinator.hydrate_catalog()

        class _Repo(SessionRepository):
            def __init__(self, db_path):
                self._db_path = db_path

            def load(self):
                from michi.infrastructure.session_repository import (
                    SqliteSessionRepository,
                )

                return SqliteSessionRepository(self._db_path).load()

            def save(self, snapshot) -> bool:
                return True

        queue = QueueService()
        playback = PlaybackService(_FakeBackend())
        session = PlaybackSessionService(playback, queue)
        from michi.application.settings_service import SettingsService

        settings = SettingsService(_NoopSettingsRepo())
        from michi.application.library_track_resolver import LibraryTrackResolver

        persistence = PersistenceCoordinator(
            _Repo(db_path),
            queue,
            session,
            playback,
            settings,
            track_resolver=LibraryTrackResolver(fresh_library),
        )
        persistence.restore()

        restored = session.state
        from michi.domain.playback_session import PlaybackContextType

        assert restored.context_type is PlaybackContextType.QUEUE
        current = restored.current_entry
        assert current is not None
        assert current.library_track_id == track_id
        assert current.file_path == new_path  # resolved CURRENT path, not old


class _NoopSettingsRepo:
    """Minimal SettingsRepository for the restore-only coordinator."""

    def load(self):
        from michi.domain.settings import SettingsState

        return SettingsState()

    def save(self, state) -> None: ...


class _FakeBackend:
    """Minimal AudioPort fake for session restore (no playback commands)."""

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
