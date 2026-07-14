import pytest

from core.metadata.models import (
    MetadataDocument,
)
from core.metadata.registry import MetadataFormatRegistry
from core.metadata.writer import MetadataWriter


@pytest.fixture
def registry():
    return MetadataFormatRegistry.default_registry()


class TestMetadataWriter:
    def test_write_nonexistent_file(self, registry):
        writer = MetadataWriter(registry)
        result = writer.write("/nonexistent/file.mp3", MetadataDocument())
        assert result.ok is False

    def test_write_unsupported_format(self, registry):
        writer = MetadataWriter(registry)
        result = writer.write("test.wav", MetadataDocument())
        assert result.ok is False

    def test_create_backup(self, registry):
        import tempfile
        writer = MetadataWriter(registry)
        fd, path = tempfile.mkstemp(suffix=".txt")
        import os
        os.close(fd)
        result = writer._create_backup(path)
        os.unlink(path)
        assert result.ok is True
    def test_changed_tracker(self):
        from core.metadata.writer import _ChangedTracker
        t = _ChangedTracker()
        t.mark("title")
        t.mark("artist")
        assert "title" in t.marked_fields
        assert "artist" in t.marked_fields
        assert "album" not in t.marked_fields
