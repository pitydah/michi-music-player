from unittest.mock import MagicMock
from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge


class TestSmartTaggingBridge:
    def test_create(self):
        bridge = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        assert bridge is not None
