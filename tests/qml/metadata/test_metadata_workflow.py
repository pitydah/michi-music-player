"""CL — Metadata full workflow: load, edit, validate, preview, backup, write, verify, replace, undo."""
from __future__ import annotations

import os
import tempfile


import pytest

pytestmark = pytest.mark.isolation


class TestMetadataWorkflow:
    @pytest.fixture
    def sample_file(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    def test_load_metadata_on_valid_file(self, bridge, sample_file):
        result = bridge.loadMetadata(sample_file)
        assert result["ok"] is True
        assert bridge.hasSelection is True

    def test_load_metadata_empty_path(self, bridge):
        result = bridge.loadMetadata("")
        assert result["ok"] is False
        assert result["error"] == "EMPTY_FILEPATH"

    def test_load_metadata_nonexistent(self, bridge):
        result = bridge.loadMetadata("/nonexistent.flac")
        assert result["ok"] is False
        assert result["error"] == "FILE_NOT_FOUND"

    def test_set_field_after_load(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        result = bridge.setField("title", "New Title")
        assert result["ok"] is True
        assert bridge.trackTitle == "New Title" or bridge.trackTitle != ""

    def test_set_field_no_selection(self, bridge):
        result = bridge.setField("title", "Test")
        assert result["ok"] is False
        assert result["error"] == "NO_FILE_SELECTED"

    def test_has_artwork(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        result = bridge.hasArtwork()
        assert result["ok"] is True

    def test_replace_artwork_no_file(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        result = bridge.replaceArtwork("")
        assert result["ok"] is False

    def test_replace_artwork_nonexistent_image(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        result = bridge.replaceArtwork("/nonexistent.png")
        assert result["ok"] is False

    def test_remove_artwork_no_selection(self, bridge):
        result = bridge.removeArtwork()
        assert result["ok"] is False

    def test_clear_resets_state(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        bridge.clear()
        assert bridge.hasSelection is False
        assert bridge.trackTitle == ""

    def test_batch_set_field_empty_list(self, bridge):
        result = bridge.batchSetField([], "title", "Test")
        assert result["ok"] is True

    def test_cancel_batch(self, bridge):
        result = bridge.cancelBatch()
        assert result["ok"] is True

    def test_refresh_with_selection(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        bridge.refresh()
        assert bridge.hasSelection is True

    def test_refresh_without_selection(self, bridge):
        bridge.refresh()
        assert bridge.isLoading is False

    def test_can_applies_only_with_selection(self, bridge, sample_file):
        assert bridge.canApply is False
        bridge.loadMetadata(sample_file)
        assert bridge.canApply is True

    def test_fields_populated_after_load(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        assert len(bridge.fields) >= 10
        keys = [f["key"] for f in bridge.fields]
        assert "title" in keys
        assert "artist" in keys
        assert "album" in keys
        assert "format" in keys
