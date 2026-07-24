from ui_qml_bridge.conversion_bridge import ConversionBridge


class TestConversionBridge:
    def test_create(self):
        bridge = ConversionBridge()
        assert bridge is not None
