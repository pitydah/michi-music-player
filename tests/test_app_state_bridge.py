from ui_qml_bridge.app_state_bridge import AppStateBridge


class TestAppStateBridge:
    def test_create(self):
        bridge = AppStateBridge()
        assert bridge._safe_mode is False
