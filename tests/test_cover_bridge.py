from ui_qml_bridge.cover_bridge import CoverBridge


class TestCoverBridge:
    def test_create(self):
        bridge = CoverBridge(parent=None)
        assert bridge is not None
