"""Test: metadata tag reading, writing, and model integrity."""
import os
import tempfile
import wave

import pytest


@pytest.fixture
def sample_wav():
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * 44100)
    yield path
    os.unlink(path)


class TestTagReader:
    def test_read_tags_returns_model(self, sample_wav):
        from metadata.tag_reader import read_tags
        tags = read_tags(sample_wav)
        assert tags is not None
        assert tags.filepath == sample_wav

    def test_read_returns_fields(self, sample_wav):
        from metadata.tag_reader import read_tags
        tags = read_tags(sample_wav)
        assert hasattr(tags, "title")
        assert hasattr(tags, "artist")
        assert hasattr(tags, "album")
        assert hasattr(tags, "duration")
        assert hasattr(tags, "sample_rate")

    def test_read_nonexistent_file(self):
        from metadata.tag_reader import read_tags
        tags = read_tags("/nonexistent/file.flac")
        assert tags is not None
        assert "no encontrado" in tags.error.lower() or tags.error != ""

    def test_read_empty_path(self):
        from metadata.tag_reader import read_tags
        tags = read_tags("")
        assert tags is not None
        assert tags.error != ""


class TestTagWriter:
    def test_write_no_file(self):
        from metadata.tag_model import TrackTags
        from metadata.tag_writer import write_tags
        tags = TrackTags(filepath="/nonexistent/file.flac")
        result = write_tags(tags)
        assert not result


class TestTagModel:
    def test_track_tags_defaults(self):
        from metadata.tag_model import TrackTags
        tags = TrackTags(filepath="")
        assert tags.title == ""
        assert tags.artist == ""
        assert not tags.dirty
        assert tags.dirty_fields == set()

    def test_track_tags_text_fields_defined(self):
        from metadata.tag_model import TrackTags
        assert len(TrackTags.TEXT_FIELDS) > 0
        assert "title" in TrackTags.TEXT_FIELDS
        assert "artist" in TrackTags.TEXT_FIELDS
        assert "album" in TrackTags.TEXT_FIELDS

    def test_track_tags_dirty_after_set(self):
        from metadata.tag_model import TrackTags
        tags = TrackTags(filepath="")
        tags.set_field("title", "New Title")
        assert tags.dirty
        assert "title" in tags.dirty_fields
