from unittest.mock import MagicMock
from ui_qml_bridge.queue_bridge import QueueBridge


class TestQueueBridge:
    def test_create(self):
        bridge = QueueBridge(player_service=MagicMock())
        assert bridge is not None
