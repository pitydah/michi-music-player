from unittest.mock import MagicMock
from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge


class TestCommandPaletteBridge:
    def test_create(self):
        bridge = CommandPaletteBridge()
        assert bridge is not None
