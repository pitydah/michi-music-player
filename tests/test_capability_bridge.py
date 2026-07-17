from unittest.mock import MagicMock
from ui_qml_bridge.capability_bridge import CapabilityBridge


class TestCapabilityBridge:
    def test_create(self):
        bridge = CapabilityBridge(feature_manager=MagicMock())
        assert bridge is not None
