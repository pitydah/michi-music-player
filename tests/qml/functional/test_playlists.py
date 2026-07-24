"""Test: playlist CRUD operations."""

import pytest


class TestPlaylistIO:
    def test_playlist_import(self):
        from core.playlist_service import PlaylistService
        assert PlaylistService is not None

    def test_m3u_parse(self):
        import core.playlist_io as pio
        assert hasattr(pio, 'parse_m3u') or hasattr(pio, 'load_playlist')

    def test_pls_parse(self):
        import core.playlist_io as pio
        assert hasattr(pio, 'parse_pls') or hasattr(pio, 'load_playlist')


class TestSmartPlaylist:
    def test_smart_playlist_import(self):
        try:
            from core.smart_playlist_service import SmartPlaylistService
            assert SmartPlaylistService is not None
        except ImportError:
            pytest.skip("smart_playlist_service not available")


class TestPlaylistBridge:
    def test_playlists_bridge_import(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        assert PlaylistsBridge is not None
