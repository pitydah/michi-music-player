from unittest.mock import MagicMock
from ui_qml_bridge.metadata_bridge import MetadataBridge


class TestMetadataBridge:
    def test_create(self):
        bridge = MetadataBridge()
        assert bridge is not None
