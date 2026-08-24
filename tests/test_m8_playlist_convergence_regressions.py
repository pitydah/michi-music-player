"""M8-R1F: convergence regression gates — end-to-end.

- Delete + recreate same name → NEW identity; old pinned/recent/navigation
  state dies with the old entity.
- Legacy V1 open → deterministic id → rename → persist → restart.
- Coordinator-level delete convergence.
"""

import json
import sqlite3

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.navigation import AppRoute
from michi.domain.playlist import legacy_playlist_id
from tests.conftest import FakeAudioPort
from tests.test_playlists import FakePlaylistsPort


def _build(repo=None):
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
    service = PlaylistService(
        playlists_port=repo if repo is not None else FakePlaylistsPort()
    )
    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    coord = PlaylistNavigationCoordinator(service, nav)
    PlaylistPlaybackCoordinator(service, session, queue)
    return service, nav, coord, queue


class TestDeleteRecreateSameName:
    def test_recreate_same_name_new_identity(self):
        service, nav, coord, _ = _build()
        a = service.create_playlist("Jazz")
        service.delete_playlist(a.playlist_id)
        b = service.create_playlist("Jazz")
        assert a.playlist_id != b.playlist_id

    def test_recreate_inherits_nothing(self):
        service, nav, coord, _ = _build()
        a = service.create_playlist("Jazz")
        service.pin_playlist(a.playlist_id)
        coord.open_playlist(a.playlist_id)
        assert service.navigation.pinned_ids == (a.playlist_id,)
        assert service.navigation.recent_ids == (a.playlist_id,)
        service.delete_playlist(a.playlist_id)
        # converge
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None
        assert service.navigation.pinned_ids == ()
        assert service.navigation.recent_ids == ()
        # recreate: fresh entity, nothing inherited
        b = service.create_playlist("Jazz")
        assert a.playlist_id != b.playlist_id
        assert b.playlist_id not in service.navigation.pinned_ids
        assert b.playlist_id not in service.navigation.recent_ids
        assert nav.state.playlist_id is None  # no stale navigation target


class TestLegacyOpenRenameRestart:
    def _seed_v1(self, db_path):
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_prefs ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO library_prefs(key, value) VALUES('playlists', ?)",
                (json.dumps([{"name": "Jazz", "track_paths": ["/a.flac"]}]),),
            )
            conn.commit()
        finally:
            conn.close()

    def test_legacy_open_recent_navigation_rename_restart(self, tmp_path):
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        db = tmp_path / "m.db"
        self._seed_v1(db)
        repo = SqlitePlaylistsRepository(db)
        service, nav, coord, _ = _build(repo)
        legacy = service.playlists[0]
        legacy_id = legacy_playlist_id("Jazz")
        assert legacy.playlist_id == legacy_id

        coord.open_playlist(legacy.playlist_id)
        assert service.navigation.recent_ids == (legacy_id,)
        assert nav.state.playlist_id == legacy_id

        service.rename_playlist(legacy.playlist_id, "Jazz Nocturno")
        assert service.playlists[0].playlist_id == legacy_id
        assert service.navigation.recent_ids == (legacy_id,)
        assert nav.state.playlist_id == legacy_id

        # legitimate mutation persists V2; restart keeps everything
        service.add_track(legacy.playlist_id, "/b.flac")
        service2, nav2, coord2, _ = _build(SqlitePlaylistsRepository(db))
        assert service2.playlists[0].playlist_id == legacy_id
        assert service2.playlists[0].name == "Jazz Nocturno"
        assert service2.navigation.recent_ids == (legacy_id,)


class TestCoordinatorDeleteConvergence:
    def test_end_to_end_delete_convergence(self):
        service, nav, coord, _ = _build()
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        assert nav.state.playlist_id == a.playlist_id
        assert a.playlist_id in service.navigation.recent_ids
        service.delete_playlist(a.playlist_id)
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None
        assert service.navigation.recent_ids == ()
