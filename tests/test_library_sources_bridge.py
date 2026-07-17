from unittest.mock import MagicMock
from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge


class TestLibrarySourcesBridge:
    def test_create(self):
        bridge = LibrarySourcesBridge(service=MagicMock())
        assert bridge is not None
