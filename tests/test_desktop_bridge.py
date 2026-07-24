from ui_qml_bridge.desktop_bridge import DesktopBridge


class TestDesktopBridge:
    def test_create(self):
        bridge = DesktopBridge()
        assert bridge is not None
