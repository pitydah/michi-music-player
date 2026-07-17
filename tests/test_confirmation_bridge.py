from unittest.mock import MagicMock
from ui_qml_bridge.confirmation_bridge import ConfirmationBridge


class TestConfirmationBridge:
    def test_create(self):
        bridge = ConfirmationBridge()
        assert bridge is not None
