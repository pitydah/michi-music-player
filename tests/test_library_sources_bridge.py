from unittest.mock import MagicMock
from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge


class TestLibrarySourcesBridge:
    def test_create(self):
        bridge = LibrarySourcesBridge(library_sources_service=MagicMock())
        assert bridge is not None
