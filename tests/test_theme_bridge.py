from unittest.mock import MagicMock
from ui_qml_bridge.theme_bridge import ThemeBridge


class TestThemeBridge:
    def test_create(self):
        bridge = ThemeBridge()
        assert bridge is not None
