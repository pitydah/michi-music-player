from ui_qml_bridge.settings_bridge import SettingsBridge


class TestSettingsBridge:
    def test_create(self):
        bridge = SettingsBridge()
        assert bridge is not None
