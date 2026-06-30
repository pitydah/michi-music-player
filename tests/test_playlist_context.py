"""Tests: playlist context events — PLAYLIST_CREATED, PLAYLIST_PLAYED, PLAYLIST_QUEUED."""

from unittest.mock import MagicMock

from core.context.context_events import AppEvent
from core.context import context_repository as repo


class TestPlaylistContextEvents:

    def teardown_method(self):
        repo.close()

    def test_playlist_created_event(self, tmp_path):
        import os
        db_path = os.path.join(str(tmp_path), "ctx.sqlite")
        repo.override_db_path(db_path)

        ctx_svc = MagicMock()
        ctx = MagicMock()
        ctx.context_svc = ctx_svc

        from ui.controllers.playlist_controller import PlaylistController
        ctrl = PlaylistController(window=MagicMock(_ctx=ctx))

        ctrl._record_playlist_created(1, "Test Playlist", 10)
        ctx_svc.record_event.assert_called_once()
        args = ctx_svc.record_event.call_args
        assert args[0][0] == AppEvent.PLAYLIST_CREATED
        assert args[0][1]["playlist_id"] == 1
        assert args[0][1]["name"] == "Test Playlist"

    def test_playlist_played_event(self, tmp_path):
        import os
        db_path = os.path.join(str(tmp_path), "ctx.sqlite")
        repo.override_db_path(db_path)

        ctx_svc = MagicMock()
        svc = MagicMock()
        svc.context_svc = ctx_svc
        svc.playback = MagicMock()

        db = MagicMock()
        db.get_playlist_items.return_value = []
        db.get_playlists.return_value = []

        ctx = MagicMock()
        ctx.db = db
        ctx.context_svc = ctx_svc

        from ui.controllers.playlist_controller import PlaylistController
        ctrl = PlaylistController(window=MagicMock(_ctx=ctx), services=svc)

        ctrl.hub_playlist_play(1)
        ctx_svc.record_playlist_played.assert_called_once()

    def test_playlist_queued_event(self, tmp_path):
        import os
        db_path = os.path.join(str(tmp_path), "ctx.sqlite")
        repo.override_db_path(db_path)

        ctx_svc = MagicMock()
        ctx = MagicMock()
        ctx.db = MagicMock()
        ctx.db.get_playlist_items.return_value = []
        ctx.context_svc = ctx_svc
        ctx.playback = MagicMock()

        from ui.controllers.playlist_controller import PlaylistController
        ctrl = PlaylistController(window=MagicMock(_ctx=ctx))

        ctrl.hub_playlist_queue(1)
        ctx_svc.record_playlist_queued.assert_called_once()
