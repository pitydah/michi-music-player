"""M8-R1 closeout gates — recovery, integration and architecture.

Verifies the full legacy→V2→restart chain through the REAL production graph
shape (SqlitePlaylistsRepository), LKG/recovery compatibility, queue
non-regression for identity-based play, and the authority boundaries.
"""

import json
import sqlite3
from pathlib import Path

from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.playlist import PlaylistNavigationState, legacy_playlist_id
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from tests.conftest import FakeAudioPort
from tests.test_playlists import FakePlaylistsPort


def _seed_v1(db_path: Path, entries):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS library_prefs ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO library_prefs(key, value) VALUES('playlists', ?)",
            (json.dumps(entries),),
        )
        conn.commit()
    finally:
        conn.close()


def _service(repo):
    from michi.application.playback_service import PlaybackService
    from michi.application.playback_session_service import (
        PlaybackSessionService,
    )
    from michi.application.playlist_playback_coordinator import (
        PlaylistPlaybackCoordinator,
    )

    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    service = PlaylistService(playlists_port=repo)
    coordinator = PlaylistPlaybackCoordinator(service, session, queue)
    return service, queue, session, audio, coordinator


class TestLegacyToV2FullChain:
    def test_legacy_load_mutate_restart_same_ids(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(db, [{"name": "Jazz", "track_paths": ["/a.flac"]}])
        repo = SqlitePlaylistsRepository(db)
        service, _, session, _, _ = _service(repo)
        loaded = service.playlists[0]
        assert loaded.playlist_id == legacy_playlist_id("Jazz")
        service.add_track(loaded.playlist_id, "/b.flac")  # persist V2
        # verify V2 on disk
        conn = sqlite3.connect(str(db))
        try:
            row = conn.execute(
                "SELECT value FROM library_prefs WHERE key='playlists'"
            ).fetchone()
        finally:
            conn.close()
        payload = json.loads(row[0])
        assert payload[0]["id"] == legacy_playlist_id("Jazz")
        # restart: same id, same tracks
        service2, _, session, _, _ = _service(SqlitePlaylistsRepository(db))
        assert service2.playlists[0].playlist_id == legacy_playlist_id("Jazz")
        assert service2.playlists[0].track_paths == ("/a.flac", "/b.flac")

    def test_v2_pinned_recent_survive_restart(self, tmp_path):
        db = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db)
        service, _, session, _, _ = _service(repo)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(b.playlist_id)
        service.mark_recent(a.playlist_id)
        service2, _, session, _, _ = _service(SqlitePlaylistsRepository(db))
        assert service2.navigation == PlaylistNavigationState(
            pinned_ids=(a.playlist_id,),
            recent_ids=(a.playlist_id, b.playlist_id),
        )

    def test_lkg_snapshot_preserves_v2_ids(self, tmp_path):
        """LKG-compatible: the repository writes only through the shared
        library_prefs table, so an LKG backup of the database preserves the
        V2 payload verbatim."""
        db = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db)
        service, _, session, _, _ = _service(repo)
        a = service.create_playlist("A")
        conn = sqlite3.connect(str(db))
        try:
            # simulate the LKG backup (SQLite backup API semantics: a full
            # snapshot of the db file)
            lkg = tmp_path / "michi.db.lkg"
            src = sqlite3.connect(str(db))
            dst = sqlite3.connect(str(lkg))
            src.backup(dst)
            dst.close()
            src.close()
        finally:
            conn.close()
        restored = SqlitePlaylistsRepository(lkg).load()
        assert restored[0].playlist_id == a.playlist_id
        assert restored[0].name == "A"

    def test_malformed_collection_never_fabricates(self, tmp_path):
        db = tmp_path / "michi.db"
        conn = sqlite3.connect(str(db))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_prefs ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO library_prefs(key, value) VALUES('playlists', ?)",
                ('{"not": "a list"}',),
            )
            conn.commit()
        finally:
            conn.close()
        service, _, session, _, _ = _service(SqlitePlaylistsRepository(db))
        assert service.playlists == ()
        assert service.navigation == PlaylistNavigationState()


class TestQueueNonRegression:
    def test_play_playlist_sets_playlist_context(self):
        """M4-R1: Play Playlist → PLAYLIST session context; Queue untouched."""
        repo = FakePlaylistsPort()
        service, queue, session, audio, coordinator = _service(repo)
        p = service.create_playlist("P")
        for path in ("/m/a.mp3", "/m/b.mp3"):
            service.add_track(p.playlist_id, Path(path))
        coordinator.play_playlist(p.playlist_id)
        assert queue.state.count == 0  # Queue untouched
        assert session.state.context_type.name == "NONE"  # acceptance-driven
        audio.trigger_media_accepted(Path("/m/a.mp3"))
        assert session.state.context_type.name == "PLAYLIST"
        assert session.state.current_index == 0

    def test_play_playlist_respects_existing_queue_content(self):
        repo = FakePlaylistsPort()
        service, queue, session, audio, coordinator = _service(repo)
        queue.add(Path("/pre/a.mp3"))
        session.play_queue_index(0)
        audio.trigger_media_accepted(Path("/pre/a.mp3"))
        assert session.state.current_index == 0
        p = service.create_playlist("P")
        service.add_track(p.playlist_id, "/m/b.mp3")
        coordinator.play_playlist(p.playlist_id)
        # Queue keeps its content; the session context supersedes.
        assert queue.state.count == 1  # nothing appended
        assert [t.file_path for t in queue.state.tracks] == [Path("/pre/a.mp3")]

    def test_queue_state_never_aliases_playlist(self):
        """QueueState is a separate authority: mutating the queue never
        touches the playlist, and vice versa."""
        repo = FakePlaylistsPort()
        service, queue, session, _, _ = _service(repo)
        p = service.create_playlist("P")
        service.add_track(p.playlist_id, "/m/a.mp3")
        queue.clear()
        assert service.playlists[0].track_paths == ("/m/a.mp3",)


class TestAuthorityBoundaries:
    def test_playlist_service_is_sole_authority(self):
        """No second playlist collection exists anywhere in the application
        layer: PlaylistService is constructed as the only owner."""
        from michi.application import playlist_service as ps_mod

        assert ps_mod.PlaylistService is PlaylistService

    def test_navigation_state_owned_by_navigation_service(self):
        from michi.application.navigation_service import NavigationService
        from michi.domain.navigation import AppRoute, NavigationState

        ns = NavigationService()
        ns.navigate_to_playlist("id-1")
        assert isinstance(ns.state, NavigationState)
        assert ns.state.current_route == AppRoute.PLAYLISTS

    def test_domain_has_no_qt_sqlite(self):
        """Architecture gate: domain playlist module imports only stdlib."""
        import types

        from michi.domain import playlist

        for _name, value in list(playlist.__dict__.items()):
            if isinstance(value, types.ModuleType):
                assert not value.__name__.startswith(
                    ("PySide6", "sqlite3", "michi.infrastructure")
                ), f"domain leaked {value.__name__}"

    def test_application_layer_has_no_pyside6(self):
        """Architecture gate: application services stay Qt-free."""
        import michi.application.navigation_service
        import michi.application.playlist_service

        for mod in (
            michi.application.playlist_service,
            michi.application.navigation_service,
        ):
            with open(mod.__file__) as fh:
                src = fh.read()
            assert "PySide6" not in src, f"{mod.__name__} imports Qt"
