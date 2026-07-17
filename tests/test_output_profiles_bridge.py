from unittest.mock import MagicMock
from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge


class TestOutputProfilesBridge:
    def test_create(self):
        bridge = OutputProfilesBridge(player_service=MagicMock())
        assert bridge is not None
