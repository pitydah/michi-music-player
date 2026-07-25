from unittest.mock import MagicMock
from ui_qml_bridge.playlists_bridge import PlaylistsBridge


class TestPlaylistsBridge:
    def test_create(self) -> None:
        bridge = PlaylistsBridge(db=MagicMock(), playlist_service=MagicMock())  # DRIFT: playlist_service now required
        assert bridge is not None
