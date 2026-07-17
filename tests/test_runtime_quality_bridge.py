from ui_qml_bridge.runtime_quality_bridge import RuntimeQualityBridge


class TestRuntimeQualityBridge:
    def test_create(self):
        bridge = RuntimeQualityBridge()
        assert bridge is not None
