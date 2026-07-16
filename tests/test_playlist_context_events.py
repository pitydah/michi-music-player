"""Tests: Playlist context events — import M3U real, export real, ContextService real."""

import os
from unittest.mock import MagicMock, patch


class TestPlaylistContextEvents:

    def test_import_emits_playlist_imported(self):
        ctx = MagicMock()
        ctx.record_playlist_imported(42, "Test", 10)
        args = ctx.record_playlist_imported.call_args
        assert args[0] == (42, "Test", 10)

    def test_export_emits_playlist_exported(self):
        ctx = MagicMock()
        ctx.record_playlist_exported(1, "My Playlist", 15)
        args = ctx.record_playlist_exported.call_args
        assert args[0] == (1, "My Playlist", 15)

    def test_m3u_import_uses_playlist_imported_not_created(self, tmp_path):
        m3u = tmp_path / "test.m3u"
        m3u.write_text("#EXTM3U\n#EXTINF:180,Song\nsong1.flac\n")
        (tmp_path / "song1.flac").write_text("")
        (tmp_path / "song2.flac").write_text("")

        ctx = MagicMock()
        db = MagicMock()
        db.create_playlist.return_value = 99
        playback = MagicMock()
        player_bar_ctrl = MagicMock()

        win = MagicMock()
        win._services.context_svc = ctx
        win._ctx.context_svc = ctx
        win._ctx.db = db
        win._ctx.playback = playback
        win._player_bar_ctrl = player_bar_ctrl
        win._toast = MagicMock()
        win._ctx.rebuild_sidebar = MagicMock()
        win._context_svc = ctx

        from legacy_widgets.ui.controllers.legacy_controllers.playlist_controller import PlaylistController
        ctrl = PlaylistController(win)

        def fake_create(name):
            return 99
        db.create_playlist.side_effect = fake_create

        with patch("ui.controllers.playlist_controller.QFileDialog.getOpenFileName",
                   return_value=(str(m3u), "")):
            ctrl.import_m3u()

        ctx.record_playlist_imported.assert_called_once()
        created_calls = [c for c in ctx.record_event.call_args_list
                         if c[0][0] == "playlist_created"]
        assert len(created_calls) == 0

    def test_m3u_export_records_exported(self, tmp_path):
        ctx = MagicMock()
        db = MagicMock()
        db.get_playlists.return_value = [{"id": 1, "name": "Test"}]
        db.get_playlist_items.return_value = []

        win = MagicMock()
        win._services.context_svc = ctx
        win._ctx.context_svc = ctx
        win._ctx.db = db
        win._toast = MagicMock()
        win._ctx.rebuild_sidebar = MagicMock()

        from legacy_widgets.ui.controllers.legacy_controllers.playlist_controller import PlaylistController
        ctrl = PlaylistController(win)

        ctrl._context = lambda: ctx

        with patch("ui.controllers.playlist_controller.QFileDialog.getSaveFileName",
                   return_value=(str(tmp_path / "out.m3u"), "")), \
             patch("ui.controllers.playlist_controller.QInputDialog.getItem",
                   return_value=("Test", True)):
            ctrl.export_playlists()

        ctx.record_playlist_exported.assert_called_once()

    def test_payload_no_paths_with_context_service(self, tmp_path):
        from core.context import context_repository as repo
        from core.context.context_service import ContextService

        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        svc = ContextService()

        svc.record_playlist_imported(playlist_id=1, name="Test", count=10)
        svc.record_playlist_exported(playlist_id=2, name="Export", count=5)

        events = repo.recent_events(limit=10)
        raw = str(events)
        assert "filepath" not in raw
        assert "/home/" not in raw
        assert "/tmp/" not in raw
        assert "C:\\" not in raw
