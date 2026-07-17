from unittest.mock import MagicMock
from ui_qml_bridge.mix_bridge import MixBridge


class TestMixBridge:
    def test_create(self):
        bridge = MixBridge(mix_service=MagicMock())
        assert bridge is not None
