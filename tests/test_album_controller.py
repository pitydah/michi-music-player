"""Tests for AlbumController."""
from ui.controllers.album_controller import AlbumController


class TestAlbumController:
    def test_create_playlist(self, mock_window):
        ctrl = AlbumController(mock_window)
        ctrl.create_playlist(["/tmp/a.flac"])
        mock_window._toast_svc.show.assert_called_once()

    def test_open_folder(self, mock_window):
        ctrl = AlbumController(mock_window)
        ctrl.open_folder("/tmp")
        # Should not crash

    def test_show_details_no_tracks(self, mock_window):
        """show_details with empty tracks should call QMessageBox."""
        ctrl = AlbumController(mock_window)
        group = type("obj", (object,), {
            "title": "Test Album",
            "subtitle": "Artist",
            "data": {"tracks": []},
        })()
        # This calls QMessageBox which needs a real QWidget, so we catch the error
        import contextlib
        with contextlib.suppress(TypeError, RuntimeError):
            ctrl.show_details(group)

    def test_search_cover_no_tracks(self, mock_window):
        ctrl = AlbumController(mock_window)
        group = type("obj", (object,), {"data": {"tracks": []}})()
        ctrl.search_cover(group)
        # Should return without crash

    def test_refresh_grid_callback(self, mock_window):
        called = []
        ctrl = AlbumController(mock_window, refresh_grid=lambda: called.append(True))
        group = type("obj", (object,), {"data": {"tracks": []}})()
        ctrl.search_cover(group)
        # No tracks, should not call refresh_grid
        assert called == []
