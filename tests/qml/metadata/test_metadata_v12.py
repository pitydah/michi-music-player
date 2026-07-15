"""Tests for Metadata v12 — MetadataBridge with MetadataService."""
from unittest.mock import MagicMock, patch

import pytest


class MockMetadataResult:
    def __init__(self, ok=True, data=None, code="", message=""):
        self.ok = ok
        self.data = data or {"fields": {
            "title": "Test", "artist": "Artist", "album": "Album",
            "format": "FLAC", "bitrate": 1411000, "sample_rate": 44100,
            "has_artwork": True,
        }}
        self.code = code
        self.message = message


class TestMetadataBridgeCreation:
    def test_requires_metadata_service(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        with pytest.raises(Exception):
            MetadataBridge()

    def test_creation(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge(metadata_service=MagicMock())
        assert mb is not None

    def test_no_selection_default(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge(metadata_service=MagicMock())
        assert mb.hasSelection is False

    def test_is_loading_default(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge(metadata_service=MagicMock())
        assert mb.isLoading is False


class TestMetadataLoading:
    def test_load_empty_path(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge(metadata_service=MagicMock())
        result = mb.loadMetadata("")
        assert not result.get("ok")

    def test_load_non_existent(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge(metadata_service=MagicMock())
        result = mb.loadMetadata("/nonexistent/file.mp3")
        assert not result.get("ok")

    def test_load_with_service(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        svc = MagicMock()
        svc.read.return_value = MockMetadataResult()
        mb = MetadataBridge(metadata_service=svc)
        result = mb.loadMetadata("/test/file.mp3")
        assert isinstance(result, dict)

    def test_set_field(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge(metadata_service=MagicMock())
        mb.loadMetadata("/test/file.mp3")
        result = mb.setField("title", "New Title")
        assert isinstance(result, dict)

    def test_has_artwork(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge(metadata_service=MagicMock())
        result = mb.hasArtwork()
        assert isinstance(result, dict)

    def test_clear(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge(metadata_service=MagicMock())
        mb.clear()
        assert mb.hasSelection is False
