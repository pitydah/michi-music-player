from unittest.mock import MagicMock
from ui_qml_bridge.global_search_bridge import GlobalSearchBridge


class TestGlobalSearchBridge:
    def test_create(self):
        bridge = GlobalSearchBridge(search_engine=MagicMock())
        assert bridge is not None
