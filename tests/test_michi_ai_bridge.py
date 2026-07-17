from unittest.mock import MagicMock
from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


class TestMichiAIBridge:
    def test_create(self):
        bridge = MichiAIBridge(michi_ai_service=MagicMock())
        assert bridge is not None
