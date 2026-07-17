from unittest.mock import MagicMock
from ui_qml_bridge.radio_bridge import RadioBridge


class TestRadioBridge:
    def test_create(self):
        bridge = RadioBridge(radio_manager=MagicMock())
        assert bridge is not None
