from unittest.mock import MagicMock
from ui_qml_bridge.connections_bridge import ConnectionsBridge


class TestConnectionsBridge:
    def test_create(self):
        bridge = ConnectionsBridge(connection_manager=MagicMock())
        assert bridge is not None
