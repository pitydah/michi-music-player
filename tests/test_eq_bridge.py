from unittest.mock import MagicMock
from ui_qml_bridge.eq_bridge import EqBridge


class TestEqBridge:
    def test_create(self):
        bridge = EqBridge(player_service=MagicMock())
        assert bridge is not None
