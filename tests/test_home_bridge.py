from unittest.mock import MagicMock
from ui_qml_bridge.home_bridge import HomeBridge


class TestHomeBridge:
    def test_create(self):
        bridge = HomeBridge(dashboard_service=MagicMock())
        assert bridge is not None
