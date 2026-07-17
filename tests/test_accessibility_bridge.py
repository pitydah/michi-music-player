from unittest.mock import MagicMock
from ui_qml_bridge.accessibility_bridge import AccessibilityBridge


class TestAccessibilityBridge:
    def test_create(self):
        bridge = AccessibilityBridge(playback_service=MagicMock())
        assert bridge is not None
