from unittest.mock import MagicMock
from core.queue_service import QueueService
from ui_qml_bridge.queue_bridge import QueueBridge


class TestQueueBridge:
    def test_create(self):
        bridge = QueueBridge(
            player_service=MagicMock(),
            queue_service=QueueService(),
        )
        assert bridge is not None
