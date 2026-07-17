from unittest.mock import MagicMock
from ui_qml_bridge.selection_context_bridge import SelectionContextBridge


class TestSelectionContextBridge:
    def test_create(self):
        bridge = SelectionContextBridge()
        assert bridge is not None
