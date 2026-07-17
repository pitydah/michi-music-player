from unittest.mock import MagicMock
from ui_qml_bridge.library_bridge import LibraryBridge


class TestLibraryBridge:
    def test_create(self):
        bridge = LibraryBridge(query_service=MagicMock())
        assert bridge is not None
