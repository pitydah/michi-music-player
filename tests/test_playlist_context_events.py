"""Tests: Playlist context events — IMPORTED, EXPORTED, no paths."""

from unittest.mock import MagicMock


class TestPlaylistContextEvents:

    def test_import_m3u_records_playlist_imported(self):
        ctx = MagicMock()
        win = MagicMock()
        win._services.context_svc = ctx
        win._ctx.context_svc = ctx
        win._ctx.db = MagicMock()
        win._ctx.rebuild_sidebar = MagicMock()
        win._toast = MagicMock()
        win._current_playlist = None

        from ui.controllers.playlist_controller import PlaylistController
        ctrl = PlaylistController(win)

        ctrl._context = lambda: ctx
        ctrl._record_playlist_created = MagicMock()

        pid = 42
        ctrl._ctx.db.create_playlist.return_value = pid

        ctrl.import_m3u()

        ctx.record_playlist_imported.assert_called_once()
        call_kwargs = ctx.record_playlist_imported.call_args
        assert call_kwargs[0][0] == pid  # playlist_id

    def test_export_playlists_records_playlist_exported(self):
        ctx = MagicMock()
        win = MagicMock()
        win._services.context_svc = ctx
        win._ctx.context_svc = ctx
        win._ctx.db = MagicMock()
        win._ctx.rebuild_sidebar = MagicMock()
        win._toast = MagicMock()
        win._current_playlist = None

        playlists = [{"id": 1, "name": "Test"}]
        win._ctx.db.get_playlists.return_value = playlists
        win._ctx.db.get_playlist_items.return_value = []

        from ui.controllers.playlist_controller import PlaylistController
        ctrl = PlaylistController(win)

        ctrl._context = lambda: ctx
        ctrl._record_playlist_created = MagicMock()

        def mock_save(*a, **kw):
            return ("/tmp/test.m3u", "")
        import PySide6.QtWidgets
        original = PySide6.QtWidgets.QFileDialog.getSaveFileName
        PySide6.QtWidgets.QFileDialog.getSaveFileName = mock_save
        try:
            ctrl.export_playlists()
            ctx.record_playlist_exported.assert_called_once()
        finally:
            PySide6.QtWidgets.QFileDialog.getSaveFileName = original
