from unittest.mock import MagicMock
from ui_qml_bridge.playback_bridge import PlaybackBridge


class TestPlaybackBridge:
    def test_create(self):
        bridge = PlaybackBridge(player_service=MagicMock())
        assert bridge is not None
