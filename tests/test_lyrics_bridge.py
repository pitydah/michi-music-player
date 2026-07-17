from unittest.mock import MagicMock
from ui_qml_bridge.lyrics_bridge import LyricsBridge


class TestLyricsBridge:
    def test_create(self):
        bridge = LyricsBridge(worker_manager=MagicMock())
        assert bridge is not None
