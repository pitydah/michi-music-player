"""Tests for PlaylistImportDialog and PlaylistExportDialog: import/export flows."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.playlists_bridge import PlaylistsBridge

pytestmark = [pytest.mark.qml_module("playlists")]


class TestPlaylistImportExport:

    def test_import_preview_no_service(self):
        bridge = PlaylistsBridge()
        result = bridge.previewPlaylistImport("/tmp/test.m3u")
        assert result["ok"] is False
        assert result["error"] == "NO_SERVICE"

    def test_import_preview_with_service(self):
        svc = MagicMock()
        svc.import_preview.return_value = {"ok": True, "total_entries": 10, "valid_entries": 8, "missing_entries": 2}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.previewPlaylistImport("/tmp/test.m3u")
        assert result["ok"] is True
        assert result["total_entries"] == 10
        assert result["valid_entries"] == 8

    def test_import_preview_service_error(self):
        svc = MagicMock()
        svc.import_preview.return_value = {"ok": False, "error": "INVALID_FORMAT"}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.previewPlaylistImport("/tmp/bad.pls")
        assert result["ok"] is False
        assert result["error"] == "INVALID_FORMAT"

    def test_confirm_import_no_service(self):
        bridge = PlaylistsBridge()
        result = bridge.confirmPlaylistImport("/tmp/test.m3u")
        assert result["ok"] is False
        assert result["error"] == "NO_SERVICE"

    def test_confirm_import_with_service(self):
        svc = MagicMock()
        svc.import_confirm.return_value = {"ok": True, "name": "Imported", "count": 8}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.confirmPlaylistImport("/tmp/test.m3u", "My Playlist")
        assert result["ok"] is True
        assert result["count"] == 8

    def test_import_m3u_alias(self):
        svc = MagicMock()
        svc.import_confirm.return_value = {"ok": True, "name": "Test", "count": 5}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.importM3U("/tmp/test.m3u")
        assert result["ok"] is True
        assert result["count"] == 5

    def test_import_m3u8_alias(self):
        svc = MagicMock()
        svc.import_confirm.return_value = {"ok": True, "name": "Test", "count": 5}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.importM3U8("/tmp/test.m3u8")
        assert result["ok"] is True

    def test_cancel_import_no_service(self):
        bridge = PlaylistsBridge()
        result = bridge.cancelPlaylistImport("import_1")
        assert result["ok"] is True

    def test_cancel_import_with_service(self):
        svc = MagicMock()
        svc.import_cancel.return_value = {"ok": True, "cancelled": True}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.cancelPlaylistImport("import_1")
        assert result["ok"] is True
        svc.import_cancel.assert_called_once_with("import_1")

    def test_export_m3u_no_service(self):
        bridge = PlaylistsBridge()
        result = bridge.exportM3U(1, "/tmp/export.m3u")
        assert result["ok"] is False
        assert result["error"] == "NO_SERVICE"

    def test_export_m3u_with_service(self):
        svc = MagicMock()
        svc.export.return_value = {"ok": True, "count": 10}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.exportM3U(1, "/tmp/export.m3u")
        assert result["ok"] is True
        assert result["count"] == 10
        svc.export.assert_called_once_with(1, "/tmp/export.m3u")

    def test_export_m3u8_alias(self):
        svc = MagicMock()
        svc.export.return_value = {"ok": True, "count": 5}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.exportM3U8(1, "/tmp/export.m3u8")
        assert result["ok"] is True

    def test_export_service_error(self):
        svc = MagicMock()
        svc.export.return_value = {"ok": False, "error": "WRITE_FAILED"}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.exportM3U(1, "/tmp/fail.m3u")
        assert result["ok"] is False
        assert result["error"] == "WRITE_FAILED"

    def test_play_imported_playlist(self):
        db = MagicMock()
        items = [
            MagicMock(id=1, track_uid="u1", filepath="/m/s1.mp3",
                      title="S1", artist="A", album="Al", duration=200),
        ]
        db.get_playlist_items.return_value = items
        bridge = PlaylistsBridge(db=db, player_service=MagicMock())
        result = bridge.playPlaylist(1)
        assert result["ok"] is True
        assert result["count"] == 1

    def test_play_playlist_no_tracks(self):
        db = MagicMock()
        db.get_playlist_items.return_value = []
        bridge = PlaylistsBridge(db=db)
        result = bridge.playPlaylist(1)
        assert result["ok"] is False
        assert result["error"] == "NO_TRACKS"

    def test_play_from_index(self):
        db = MagicMock()
        items = [
            MagicMock(id=1, track_uid="u1", filepath="/m/s1.mp3",
                      title="S1", artist="A", album="Al", duration=200),
            MagicMock(id=2, track_uid="u2", filepath="/m/s2.mp3",
                      title="S2", artist="B", album="Bl", duration=180),
        ]
        db.get_playlist_items.return_value = items
        player = MagicMock()
        bridge = PlaylistsBridge(db=db, player_service=player)
        result = bridge.playPlaylistFromIndex(1, 1)
        assert result["ok"] is True
