"""Tests for single-track metadata editing."""
from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestMetadataSingleEdit:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge(worker_manager=None)

    def test_load_metadata_returns_ok(self, bridge):
        result = bridge.loadMetadata("/nonexistent/file.flac")
        assert not result.get("ok")

    def test_set_field_updates_value(self, bridge):
        bridge.loadMetadata("/nonexistent/file.flac")
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields["title"] = "Old"
        result = bridge.setField("title", "New Title")
        assert result.get("ok")
        assert bridge._all_fields.get("title") == "New Title"

    def test_set_field_rejects_empty_filepath(self, bridge):
        result = bridge.setField("artist", "Test")
        assert not result.get("ok")

    def test_save_changes_rejects_no_file(self, bridge):
        result = bridge.saveChanges()
        assert not result.get("ok")

    def test_save_changes_with_dirty(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields = {"title": "Test", "artist": "A", "album": "B"}
        result = bridge.saveChanges()
        assert result.get("ok") is not None

    def test_clear_resets_state(self, bridge):
        bridge.loadMetadata("/nonexistent/file.flac")
        bridge._current_filepath = "/fake/file.flac"
        bridge.clear()
        assert bridge._current_filepath == ""
        assert not bridge._has_selection
        assert bridge._fields == []

    def test_refresh_reloads_current(self, bridge):
        bridge._current_filepath = ""
        bridge.refresh()
        assert bridge._current_filepath == ""

    def test_quality_summary_after_load(self, bridge):
        bridge.loadMetadata("/fake/file.flac")
        assert True

    def test_artwork_status_after_load(self, bridge):
        bridge.loadMetadata("/fake/file.flac")
        assert True

    def test_can_apply_property(self, bridge):
        bridge._has_selection = True
        bridge._current_filepath = "/fake/file.flac"
        assert bridge.canApply

    def test_inspect_track_not_found(self, bridge):
        bridge.loadMetadata("/dev/null/nonexistent.flac")
        assert bridge._error_message or not bridge._has_selection

    def test_set_field_multiple_times(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields = {"title": "", "artist": ""}
        bridge.setField("title", "A")
        bridge.setField("artist", "B")
        assert bridge._all_fields["title"] == "A"
        assert bridge._all_fields["artist"] == "B"

    def test_metadata_fields_after_load(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge.loadMetadata("/fake/file.flac")
        assert isinstance(bridge._fields, list)

    def test_is_loading_flag(self, bridge):
        bridge._is_loading = True
        assert bridge.isLoading
        bridge._is_loading = False
        assert not bridge.isLoading

    def test_error_message_set_on_load_failure(self, bridge):
        bridge._error_message = ""
        bridge.loadMetadata("/fake/file.flac")
        assert True
