from unittest.mock import MagicMock
from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge


class TestCoverProviderBridge:
    def test_create(self):
        bridge = CoverProviderBridge()
        assert bridge is not None
