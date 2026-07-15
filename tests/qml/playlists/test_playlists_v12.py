"""Tests for Playlists v12 — real PlaylistService, no CRUD directo DB."""
from unittest.mock import MagicMock

import pytest


class TestPlaylistsBridgeCreation:
    def test_requires_db(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        with pytest.raises(Exception):
            PlaylistsBridge()

    def test_creation_with_db(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=MagicMock())
        assert pb is not None

    def test_no_direct_db_crud(self):
        from ui_qml_bridge import playlists_bridge
        content = open(playlists_bridge.__file__).read()
        assert "conn.execute" not in content or "INSERT INTO playlists" not in content


class TestPlaylistOperations:
    def test_refresh(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=MagicMock())
        pb.refresh()
        assert True

    def test_create_playlist(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.create.return_value = {"ok": True, "id": 1}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.createPlaylist("Test")
        assert isinstance(result, dict)

    def test_rename_playlist(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.rename.return_value = {"ok": True}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.renamePlaylist(1, "New Name")
        assert isinstance(result, dict)

    def test_delete_playlist(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.delete.return_value = {"ok": True}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.deletePlaylist(1)
        assert isinstance(result, dict)

    def test_duplicate_playlist(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.duplicate.return_value = {"ok": True, "name": "Copy"}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.duplicatePlaylist(1)
        assert isinstance(result, dict)

    def test_clear_playlist(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.clear_playlist.return_value = {"ok": True}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.clearPlaylist(1)
        assert isinstance(result, dict)

    def test_add_track_to_playlist(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.add_track.return_value = {"ok": True}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.addTrackToPlaylist(1, filepath="/test/file.mp3")
        assert isinstance(result, dict)

    def test_remove_track(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.remove_track.return_value = {"ok": True}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.removeTrackFromPlaylist(1, 1)
        assert isinstance(result, dict)

    def test_get_detail(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.get_detail.return_value = {"ok": True, "tracks": []}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.getPlaylistDetail(1)
        assert isinstance(result, dict)

    def test_score(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=MagicMock())
        score = pb.playlistScore()
        assert isinstance(score, dict)
        assert "score" in score

    def test_play_playlist(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc._get_items_internal.return_value = [{"filepath": "/test/file.mp3"}]
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc, player_service=MagicMock())
        result = pb.playPlaylist(1)
        assert isinstance(result, dict)

    def test_import_m3u(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.import_preview.return_value = {"ok": True}
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.previewPlaylistImport("/test/file.m3u")
        assert isinstance(result, dict)

    def test_export_m3u(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc._get_items_internal.return_value = [{"filepath": "/test/file.mp3"}]
        pb = PlaylistsBridge(db=MagicMock(), playlist_service=svc)
        result = pb.exportM3U(1, "/test/export.m3u")
        assert isinstance(result, dict)
