from unittest.mock import MagicMock
from core.queue_service import QueueService
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge


class TestNowPlayingBridge:
    def test_create(self):
        bridge = NowPlayingBridge(
            player_service=MagicMock(),
            queue_service=QueueService(),
            audio_quality_adapter=MagicMock(),
        )
        assert bridge is not None
