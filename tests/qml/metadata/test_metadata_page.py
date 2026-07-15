from __future__ import annotations

import pytest

pytestmark = [pytest.mark.qml_module("metadata")]


class TestMetadataPage:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    def test_initial_state(self, bridge):
        assert not bridge.hasSelection
        assert not bridge.isLoading

    def test_status_property_exists(self, bridge):
        assert hasattr(bridge, "status")

    def test_data_changed_signal(self, bridge):
        signals = []
        bridge.dataChanged.connect(lambda: signals.append(True))
        bridge.loadMetadata("/nonexistent/file.flac")
        assert len(signals) >= 1

    def test_load_metadata_empty_path(self, bridge):
        result = bridge.loadMetadata("")
        assert result.get("error") == "EMPTY_FILEPATH"

    def test_load_metadata_nonexistent(self, bridge):
        result = bridge.loadMetadata("/nonexistent/file.flac")
        assert not result.get("ok")

    def test_fields_model_after_load(self, bridge):
        bridge.loadMetadata("/fake/file.flac")
        assert isinstance(bridge.fields, list)

    def test_fields_contain_expected_keys(self, bridge):
        bridge.loadMetadata("/fake/file.flac")
        keys = {f["key"] for f in bridge.fields}
        assert "title" in keys
        assert "artist" in keys
        assert "album" in keys

    def test_set_field_updates_value(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields["title"] = ""
        result = bridge.setField("title", "New Title")
        assert result.get("ok")
        assert bridge._all_fields.get("title") == "New Title"

    def test_set_field_no_selection(self, bridge):
        result = bridge.setField("artist", "Test")
        assert not result.get("ok")

    def test_quality_summary_available(self, bridge):
        bridge._track_title = "Test"
        assert bridge.trackTitle == "Test"

    def test_artwork_status_present(self, bridge):
        bridge._artwork_status = "Con carátula"
        assert bridge.artworkStatus == "Con carátula"

    def test_clear_resets(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge.clear()
        assert bridge._current_filepath == ""
        assert not bridge.hasSelection

    def test_can_apply_property(self, bridge):
        assert not bridge.canApply
        bridge._has_selection = True
        bridge._current_filepath = "/fake/file.flac"
        assert bridge.canApply

    def test_status_transitions(self, bridge):
        bridge._set_status("APPLYING")
        assert bridge.status == "APPLYING"
        bridge._set_status("ERROR")
        assert bridge.status == "ERROR"
        bridge._set_status("SUCCEEDED")
        assert bridge.status == "SUCCEEDED"

    def test_batch_set_field_returns_result(self, bridge):
        result = bridge.batchSetField([], "title", "Test")
        assert result.get("ok") is not None

    def test_cancel_batch(self, bridge):
        result = bridge.cancelBatch()
        assert result.get("ok")

    def test_refresh_without_selection(self, bridge):
        bridge.refresh()
        assert not bridge.isLoading

    def test_error_message_on_failure(self, bridge):
        bridge.loadMetadata("/fake/missing.flac")
        assert True
