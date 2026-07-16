"""Tests for PlaylistController."""
from legacy_widgets.ui.controllers.legacy_controllers.playlist_controller import PlaylistController


class TestPlaylistController:
    def test_create_from_album(self, mock_window):
        """Create playlist from album should work when library has items."""
        ctrl = PlaylistController(mock_window)
        # With no library items, it shows a toast
        ctrl.create_from_album()
        mock_window._toast_svc.show.assert_called_once()

    def test_create_from_artist(self, mock_window):
        ctrl = PlaylistController(mock_window)
        ctrl.create_from_artist()
        mock_window._toast_svc.show.assert_called()

    def test_create_from_genre(self, mock_window):
        ctrl = PlaylistController(mock_window)
        ctrl.create_from_genre()
        mock_window._toast_svc.show.assert_called()

    def test_export_playlists(self, mock_window):
        """Export with no playlists shows toast."""
        ctrl = PlaylistController(mock_window)
        mock_window._ctx.db.get_playlists.return_value = []
        ctrl.export_playlists()
        mock_window._toast_svc.show.assert_called_once()

    def test_open_smart_playlist(self, mock_window):
        ctrl = PlaylistController(mock_window)
        ctrl.open_smart_playlist("favorites")
        mock_window._ctx.navigate_sidebar.assert_called_with("mix_favorites")

    def test_refresh_library(self, mock_window):
        ctrl = PlaylistController(mock_window)
        ctrl.refresh_library()
        mock_window._ctx.load_library.assert_called()
