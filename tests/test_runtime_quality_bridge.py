from unittest.mock import MagicMock
from ui_qml_bridge.runtime_quality_bridge import RuntimeQualityBridge


class TestRuntimeQualityBridge:
    def test_create(self):
        bridge = RuntimeQualityBridge(quality_service=MagicMock())
        assert bridge is not None
