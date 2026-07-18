from unittest.mock import MagicMock
from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2


class TestSettingsBridge:
    def test_create(self):
        bridge = SettingsBridgeV2(service=MagicMock())
        assert bridge is not None
