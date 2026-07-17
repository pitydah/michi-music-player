from unittest.mock import MagicMock
from ui_qml_bridge.navigation_bridge import NavigationBridge


class TestNavigationBridge:
    def test_create(self):
        bridge = NavigationBridge()
        assert bridge._current_route == "home"
