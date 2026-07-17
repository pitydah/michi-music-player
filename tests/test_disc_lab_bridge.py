from unittest.mock import MagicMock
from ui_qml_bridge.disc_lab_bridge import DiscLabBridge


class TestDiscLabBridge:
    def test_create(self):
        bridge = DiscLabBridge(disc_lab_service=MagicMock())
        assert bridge is not None
