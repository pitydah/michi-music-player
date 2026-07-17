from unittest.mock import MagicMock
from ui_qml_bridge.playlists_bridge import PlaylistsBridge


class TestPlaylistsBridge:
    def test_create(self):
        bridge = PlaylistsBridge(db=MagicMock())
        assert bridge is not None
