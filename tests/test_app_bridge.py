from ui_qml_bridge.app_bridge import AppBridge, get_app_version


class TestAppBridge:
    def test_create(self):
        bridge = AppBridge()
        assert bridge is not None

    def test_get_version(self):
        v = get_app_version()
        assert isinstance(v, str)
