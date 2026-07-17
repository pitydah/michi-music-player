from unittest.mock import MagicMock
from ui_qml_bridge.radio_bridge import RadioBridge


class TestRadioBridge:
    def test_create(self):
        bridge = RadioBridge(player_service=MagicMock())
        assert bridge is not None
