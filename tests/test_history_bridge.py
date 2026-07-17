from unittest.mock import MagicMock
from ui_qml_bridge.history_bridge import HistoryBridge


class TestHistoryBridge:
    def test_create(self):
        bridge = HistoryBridge(history_service=MagicMock())
        assert bridge is not None
