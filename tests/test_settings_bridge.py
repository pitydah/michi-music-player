from unittest.mock import MagicMock
from ui_qml_bridge.settings_bridge import SettingsBridge


class TestSettingsBridge:
    def test_create(self):
        bridge = SettingsBridge(settings_service=MagicMock())
        assert bridge is not None
