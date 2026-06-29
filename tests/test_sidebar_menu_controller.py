"""Tests for SidebarMenuController — context menu, playlist CRUD."""
from unittest.mock import MagicMock, patch

import pytest

from ui.controllers.sidebar_menu_controller import SidebarMenuController


@pytest.fixture
def win(qapp):
        w = MagicMock()
        w._sidebar = MagicMock()
        w._sidebar._container = MagicMock()
        w._db = MagicMock()
        w._srv_ctrl = MagicMock()
        w._toast_svc = MagicMock()
        w._load_library = MagicMock()
        w._rebuild_sidebar = MagicMock()
        w._delete_playlist = MagicMock()
        return w


@pytest.fixture
def ctrl(win):
    return SidebarMenuController(win)


class TestSidebarMenuController:
    def test_context_menu_no_item(self, ctrl, win):
        with patch.object(win._sidebar, 'childAt', return_value=None):
            ctrl.show_context_menu(MagicMock())

    def test_context_menu_no_crash(self, ctrl, win):
        mock_item = MagicMock()
        mock_item.key = "pl:42"
        mock_item.parentWidget.return_value = None
        with patch.object(win._sidebar, 'childAt', return_value=mock_item):
            ctrl.show_context_menu(MagicMock())

    def test_create_playlist_with_name(self, ctrl, win):
        with patch("ui.controllers.sidebar_menu_controller.QInputDialog.getText",
                   return_value=("My Playlist", True)):
            ctrl.create_playlist()
        win._db.create_playlist.assert_called_with("My Playlist")
        win._rebuild_sidebar.assert_called_once()

    def test_create_playlist_cancelled(self, ctrl, win):
        with patch("ui.controllers.sidebar_menu_controller.QInputDialog.getText",
                   return_value=("", False)):
            ctrl.create_playlist()
        win._db.create_playlist.assert_not_called()

    def test_create_playlist_empty_name(self, ctrl, win):
        with patch("ui.controllers.sidebar_menu_controller.QInputDialog.getText",
                   return_value=("   ", True)):
            ctrl.create_playlist()
        win._db.create_playlist.assert_not_called()

    def test_delete_playlist(self, ctrl, win):
        ctrl.delete_playlist(1)
        win._db.delete_playlist.assert_called_with(1)
        win._rebuild_sidebar.assert_called_once()
        win._load_library.assert_called_once()

    def test_edit_playlist_dialog_with_existing(self, ctrl, win):
        from PySide6.QtWidgets import QDialog
        win._db.get_playlists.return_value = [{"id": 1, "name": "Test", "description": "Desc"}]
        with patch("ui.controllers.sidebar_menu_controller.QDialog") as mock_dlg, \
             patch("ui.controllers.sidebar_menu_controller.QFormLayout"):
            dlg_instance = MagicMock(spec=QDialog)
            mock_dlg.return_value = dlg_instance
            ctrl.edit_playlist_dialog(1)
            mock_dlg.assert_called_once_with(win)

    def test_edit_playlist_dialog_not_found(self, ctrl, win):
        win._db.get_playlists.return_value = []
        ctrl.edit_playlist_dialog(1)

    def test_change_playlist_cover(self, ctrl, win):
        with patch("ui.controllers.sidebar_menu_controller.QFileDialog.getOpenFileName",
                   return_value=("/path/cover.jpg", "Images (*.jpg)")), \
             patch("ui.services.playlist_cover_service.copy_custom_cover",
                   return_value="/cached/cover.jpg"):
            ctrl.change_playlist_cover(1)
        win._db.update_playlist.assert_called_with(1, cover_path="/cached/cover.jpg", cover_type="custom")
        win._toast_svc.show.assert_called()

    def test_change_playlist_cover_cancelled(self, ctrl, win):
        with patch("ui.controllers.sidebar_menu_controller.QFileDialog.getOpenFileName",
                   return_value=("", "")):
            ctrl.change_playlist_cover(1)
        win._db.update_playlist.assert_not_called()

    def test_remove_playlist_cover(self, ctrl, win):
        with patch("ui.services.playlist_cover_service.remove_custom_cover") as mock_remove:
            ctrl.remove_playlist_cover(1)
        mock_remove.assert_called_with(1)
        win._db.update_playlist.assert_called_with(1, cover_path="", cover_type="mosaic")
        win._toast_svc.show.assert_called()

    def test_save_playlist_edit(self, ctrl, win):
        dlg = MagicMock()
        ctrl.save_playlist_edit(1, "New Name", "New Desc", dlg)
        win._db.update_playlist.assert_called_with(1, name="New Name", description="New Desc")
        win._rebuild_sidebar.assert_called_once()
        win._toast_svc.show.assert_called()
        dlg.accept.assert_called_once()
