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
    decode_snapshot,
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
        # The moved track is NOT newly added again: its original entry
        # survives BY IDENTITY (path projection updated), exactly once —
        # no duplicate, no re-entry. The brand-new file IS recent.
        recent = library.state.recently_added_paths
        assert str(root / "brand-new.flac") in recent
        assert recent.count(str(target_dir / "song.flac")) == 1
        assert len(recent) == 2


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
            _SessionRepo(db_path),
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


class _SessionRepo(SessionRepository):
    """Real SQLite-backed snapshot repository for restore tests."""

    def __init__(self, db_path) -> None:
        self._db_path = db_path

    def load(self):
        from michi.infrastructure.session_repository import (
            SqliteSessionRepository,
        )

        return SqliteSessionRepository(self._db_path).load()

    def save(self, snapshot) -> bool:
        return True


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


class TestGoldenResumeMovedTrack:
    def test_resume_backend_receives_current_path_for_moved_track(
        self, tmp_path
    ) -> None:
        """§18 golden: persist session at /A/song.flac + TrackId T; file
        moves to /B; restart → backend prepare_for_resume receives /B,
        TrackId preserved, position preserved, no autoplay."""

        from michi.domain.library_catalog import (
            LibrarySource,
            MediaAvailability,
            MediaFileRecord,
            TrackRecord,
            new_library_source_id,
            new_media_file_id,
            new_track_id,
        )
        from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="S",
            root_path=str(tmp_path / "music"),
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="A/song.flac",
            last_known_path=str(tmp_path / "music" / "A" / "song.flac"),
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))

        # Persist a V3 snapshot referencing the id at the OLD path.
        old_path = tmp_path / "music" / "A" / "song.flac"
        snapshot = PlaybackSessionSnapshot(
            format_version=3,
            queue_entries=(PersistedQueueEntry(str(old_path), "song", track.track_id),),
            context=PersistedSessionContext(
                context_type="queue",
                source_id=None,
                entries=(PersistedQueueEntry(str(old_path), "song", track.track_id),),
                current_index=0,
            ),
            playback_path=str(old_path),
            position_ms=4242,
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

        # The file MOVES before restart; the catalog reconciles the new path.
        new_path = tmp_path / "music" / "B" / "song.flac"
        new_path.parent.mkdir(parents=True)
        old_path.parent.mkdir(parents=True)
        old_path.write_bytes(b"x")
        catalog.apply_source_reconciliation(
            (
                MediaFileRecord(
                    media_file_id=media.media_file_id,
                    library_source_id=source.library_source_id,
                    relative_path="B/song.flac",
                    last_known_path=str(new_path),
                    availability=MediaAvailability.AVAILABLE,
                ),
            ),
            (),
        )

        # Restart: hydrated library + restore with a backend spy.
        from michi.application.persistence_coordinator import PersistenceCoordinator
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import PlaybackSessionService
        from michi.application.queue_service import QueueService
        from michi.application.settings_service import SettingsService

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

        class _ResumeSpyBackend(_FakeBackend):
            def __init__(self) -> None:
                self.loaded: list[Path] = []
                self.played = False

            def load(self, file_path: Path) -> None:
                self.loaded.append(file_path)

            def play(self) -> None:
                self.played = True

        backend = _ResumeSpyBackend()
        queue = QueueService()
        playback = PlaybackService(backend)
        session = PlaybackSessionService(playback, queue)
        from michi.application.library_track_resolver import LibraryTrackResolver

        persistence = PersistenceCoordinator(
            _SessionRepo(db_path),
            queue,
            session,
            playback,
            SettingsService(_NoopSettingsRepo()),
            track_resolver=LibraryTrackResolver(fresh_library),
        )
        persistence.restore(engine_available=True)

        # The backend received the CURRENT resolved path.
        assert backend.loaded and backend.loaded[-1] == new_path
        # No autoplay; identity + position preserved.
        assert backend.played is False
        assert session.state.current_entry.library_track_id == track.track_id
        assert persistence._last_persisted_position_ms == 4242


class TestResumeCoherenceTrackIdFirst:
    """P1-05 golden: TrackId equality, never path equality, in the resume
    lifecycle."""

    def test_moved_track_never_breaks_coherence(self, tmp_path) -> None:
        """Persisted T1@/Old@62s; catalog resolves /New; restore loads /New;
        the coherence check compares TrackId (never a false break); the next
        coherent checkpoint persists /New."""
        from michi.application.library_track_resolver import LibraryTrackResolver
        from michi.application.persistence_coordinator import PersistenceCoordinator
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import PlaybackSessionService
        from michi.application.queue_service import QueueService
        from michi.application.settings_service import SettingsService
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
            library_source_id=new_library_source_id(),
            display_name="S",
            root_path=str(tmp_path / "music"),
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="A/song.flac",
            last_known_path=str(tmp_path / "music" / "A" / "song.flac"),
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))

        old_path = tmp_path / "music" / "A" / "song.flac"
        snapshot = PlaybackSessionSnapshot(
            format_version=3,
            queue_entries=(PersistedQueueEntry(str(old_path), "song", track.track_id),),
            context=PersistedSessionContext(
                context_type="queue",
                source_id=None,
                entries=(PersistedQueueEntry(str(old_path), "song", track.track_id),),
                current_index=0,
            ),
            playback_path=str(old_path),
            position_ms=62_000,
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

        # File moved before startup; catalog reconciled to /New.
        new_path = tmp_path / "music" / "B" / "song.flac"
        new_path.parent.mkdir(parents=True)
        old_path.parent.mkdir(parents=True)
        old_path.write_bytes(b"x")
        catalog.apply_source_reconciliation(
            (
                MediaFileRecord(
                    media_file_id=media.media_file_id,
                    library_source_id=source.library_source_id,
                    relative_path="B/song.flac",
                    last_known_path=str(new_path),
                    availability=MediaAvailability.AVAILABLE,
                ),
            ),
            (),
        )

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

        class _SpyBackend(_FakeBackend):
            def __init__(self):
                self.loaded = []
                self.played = False

            def load(self, file_path):
                self.loaded.append(file_path)

            def play(self):
                self.played = True

        from michi.infrastructure.session_repository import (
            SqliteSessionRepository,
        )

        backend = _SpyBackend()
        queue = QueueService()
        playback = PlaybackService(backend)
        session = PlaybackSessionService(playback, queue)
        persistence = PersistenceCoordinator(
            SqliteSessionRepository(db_path),
            queue,
            session,
            playback,
            SettingsService(_NoopSettingsRepo()),
            track_resolver=LibraryTrackResolver(fresh_library),
        )
        persistence.restore(engine_available=True)

        # Loaded the CURRENT path; the identity is the same logical T.
        assert backend.loaded and backend.loaded[-1] == new_path
        assert backend.played is False
        # Coherence survives the move: the hybrid compares TrackId.
        assert persistence._hybrid_coherent() is True
        # A session-change event for the SAME TrackId is NOT a supersession.
        persistence._on_session_changed()
        assert persistence._restored_snapshot is not None  # authority held
        # The next coherent checkpoint persists the NEW path.
        persistence._last_persisted_position_ms = 62_000
        persistence.checkpoint()
        row = (
            sqlite3.connect(str(db_path))
            .execute("SELECT value FROM settings WHERE key = 'session_snapshot'")
            .fetchone()
        )
        persisted = decode_snapshot(row[0])
        assert persisted.playback_path == str(new_path)
        assert persisted.position_ms == 62_000


class TestWaitingPositionTrackIdFirst:
    """CORRECTIVE SEAL §7: WAITING_POSITION compares TrackId, never the
    historical path — a moved-file playback event is NOT a supersession."""

    def test_waiting_position_moved_path_keeps_authority(self, tmp_path) -> None:
        from michi.application.library_track_resolver import LibraryTrackResolver
        from michi.application.persistence_coordinator import PersistenceCoordinator
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import PlaybackSessionService
        from michi.application.queue_service import QueueService
        from michi.application.settings_service import SettingsService
        from michi.domain.library_catalog import (
            LibrarySource,
            MediaAvailability,
            MediaFileRecord,
            TrackRecord,
            new_library_source_id,
            new_media_file_id,
            new_track_id,
        )
        from michi.infrastructure.session_repository import SqliteSessionRepository

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="S",
            root_path=str(tmp_path / "music"),
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="A/song.flac",
            last_known_path=str(tmp_path / "music" / "A" / "song.flac"),
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))

        old_path = tmp_path / "music" / "A" / "song.flac"
        snapshot = PlaybackSessionSnapshot(
            format_version=3,
            queue_entries=(PersistedQueueEntry(str(old_path), "song", track.track_id),),
            context=PersistedSessionContext(
                context_type="queue",
                source_id=None,
                entries=(PersistedQueueEntry(str(old_path), "song", track.track_id),),
                current_index=0,
            ),
            playback_path=str(old_path),
            position_ms=10_000,
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

        new_path = tmp_path / "music" / "B" / "song.flac"
        new_path.parent.mkdir(parents=True)
        old_path.parent.mkdir(parents=True)
        old_path.write_bytes(b"x")
        catalog.apply_source_reconciliation(
            (
                MediaFileRecord(
                    media_file_id=media.media_file_id,
                    library_source_id=source.library_source_id,
                    relative_path="B/song.flac",
                    last_known_path=str(new_path),
                    availability=MediaAvailability.AVAILABLE,
                ),
            ),
            (),
        )

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

        class _AcceptBackend(_FakeBackend):
            def __init__(self):
                self.loaded = []

            def load(self, file_path):
                self.loaded.append(file_path)

            def position(self):
                return 10_000

        backend = _AcceptBackend()
        queue = QueueService()
        playback = PlaybackService(backend)
        session = PlaybackSessionService(playback, queue)
        persistence = PersistenceCoordinator(
            SqliteSessionRepository(db_path),
            queue,
            session,
            playback,
            SettingsService(_NoopSettingsRepo()),
            track_resolver=LibraryTrackResolver(fresh_library),
        )
        persistence.restore(engine_available=True)
        persistence._started = True
        assert backend.loaded and backend.loaded[-1] == new_path

        # Backend acceptance of the NEW path → WAITING_POSITION.
        playback._on_media_accepted(new_path)
        persistence._on_playback_changed()
        assert persistence._resume_phase.name == "WAITING_POSITION"

        # A playback event for the NEW path (moved identity) must NOT be a
        # supersession: the authority stays open.
        persistence._on_playback_changed()
        assert persistence._resume_phase.name == "WAITING_POSITION"

        # Position confirmation completes normally and persists the
        # CURRENT resolved path.
        persistence._on_resume_prepared(new_path, 10_000)
        row = (
            sqlite3.connect(str(db_path))
            .execute("SELECT value FROM settings WHERE key = 'session_snapshot'")
            .fetchone()
        )
        persisted = decode_snapshot(row[0])
        # §7 core: the final durable snapshot contains the CURRENT resolved
        # path (the moved identity) — never the historical one.
        assert persisted.playback_path == str(new_path)
        assert persisted.queue_entries[0].library_track_id == track.track_id

    def test_restore_guard_rejects_unrelated_snapshot_path(self, tmp_path) -> None:
        """§8: snapshot playback_path of a DIFFERENT identity than the
        persisted entry must not fabricate a resume relationship."""
        from michi.application.library_track_resolver import LibraryTrackResolver
        from michi.application.persistence_coordinator import PersistenceCoordinator
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import PlaybackSessionService
        from michi.application.queue_service import QueueService
        from michi.application.settings_service import SettingsService
        from michi.domain.library_catalog import (
            LibrarySource,
            MediaAvailability,
            MediaFileRecord,
            TrackRecord,
            new_library_source_id,
            new_media_file_id,
            new_track_id,
        )
        from michi.infrastructure.session_repository import SqliteSessionRepository

        db_path = tmp_path / "michi.db"
        catalog = SqliteLibraryCatalogRepository(db_path)
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="S",
            root_path=str(tmp_path / "music"),
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="A/song.flac",
            last_known_path=str(tmp_path / "music" / "A" / "song.flac"),
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))
        old_path = tmp_path / "music" / "A" / "song.flac"
        # CORRUPT snapshot: entry is T1 at /A, but playback_path points to
        # a DIFFERENT identity (/OTHER).
        other = tmp_path / "music" / "OTHER.flac"
        snapshot = PlaybackSessionSnapshot(
            format_version=3,
            queue_entries=(PersistedQueueEntry(str(old_path), "song", track.track_id),),
            context=PersistedSessionContext(
                context_type="queue",
                source_id=None,
                entries=(PersistedQueueEntry(str(old_path), "song", track.track_id),),
                current_index=0,
            ),
            playback_path=str(other),
            position_ms=5_000,
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
        old_path.parent.mkdir(parents=True)
        old_path.write_bytes(b"x")

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
        queue = QueueService()
        playback = PlaybackService(_FakeBackend())
        session = PlaybackSessionService(playback, queue)
        persistence = PersistenceCoordinator(
            SqliteSessionRepository(db_path),
            queue,
            session,
            playback,
            SettingsService(_NoopSettingsRepo()),
            track_resolver=LibraryTrackResolver(fresh_library),
        )
        from michi.application.persistence_coordinator import _ResumePhase

        persistence.restore(engine_available=True)
        # No fabricated resume: the unrelated playback_path never loads.
        assert persistence._resume_phase is _ResumePhase.NONE
        assert persistence._restored_snapshot is None
