from unittest.mock import MagicMock
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge


class TestNowPlayingBridge:
    def test_create(self):
        bridge = NowPlayingBridge(player_service=MagicMock())
        assert bridge is not None
