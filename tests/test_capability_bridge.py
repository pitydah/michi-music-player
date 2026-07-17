from ui_qml_bridge.capability_bridge import CapabilityBridge


class TestCapabilityBridge:
    def test_create(self):
        bridge = CapabilityBridge()
        assert bridge is not None
