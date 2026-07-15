from __future__ import annotations

import pytest

pytestmark = [pytest.mark.qml_module("metadata")]


class TestMetadataNegative:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    def test_load_metadata_empty_string(self, bridge):
        result = bridge.loadMetadata("")
        assert not result.get("ok")
        assert result.get("error") == "EMPTY_FILEPATH"

    def test_load_metadata_nonexistent(self, bridge):
        result = bridge.loadMetadata("/dev/null/nonexistent.flac")
        assert not result.get("ok")

    def test_set_field_with_no_file(self, bridge):
        result = bridge.setField("title", "Test")
        assert not result.get("ok")
        assert result.get("error") == "NO_FILE_SELECTED"

    def test_save_changes_with_no_file(self, bridge):
        result = bridge.saveChanges()
        assert not result.get("ok")

    def test_save_changes_no_selection(self, bridge):
        result = bridge.saveChanges()
        assert not result.get("ok")

    def test_replace_artwork_no_file_selected(self, bridge):
        result = bridge.replaceArtwork("/fake/image.png")
        assert not result.get("ok")

    def test_replace_artwork_nonexistent_image(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        result = bridge.replaceArtwork("/nonexistent/image.png")
        assert not result.get("ok")

    def test_remove_artwork_no_file(self, bridge):
        result = bridge.removeArtwork()
        assert not result.get("ok")

    def test_batch_set_field_empty_list(self, bridge):
        result = bridge.batchSetField([], "title", "")
        assert result.get("ok") is True

    def test_cancel_batch_returns_ok(self, bridge):
        result = bridge.cancelBatch()
        assert result.get("ok")

    def test_clear_resets_all(self, bridge):
        bridge._has_selection = True
        bridge._current_filepath = "/fake/file.flac"
        bridge._is_loading = True
        bridge._error_message = "Error"
        bridge.clear()
        assert not bridge._has_selection
        assert bridge._current_filepath == ""
        assert not bridge._is_loading
        assert bridge._error_message == ""

    def test_confirm_save_invalid_token(self, bridge):
        result = bridge.confirmSave("invalid_token")
        assert not result.get("ok")

    def test_reject_save_returns_ok(self, bridge):
        result = bridge.rejectSave()
        assert result.get("ok")

    def test_has_artwork_works_without_file(self, bridge):
        result = bridge.hasArtwork()
        assert result.get("ok")
        assert "has_artwork" in result

    def test_batch_set_field_with_special_values(self, bridge):
        result = bridge.batchSetField(["/fake/1.flac", "/fake/2.flac"], "comment", "")
        assert result.get("ok") is not None

    def test_status_not_affected_by_clear(self, bridge):
        bridge._set_status("APPLYING")
        bridge.clear()
        assert bridge.status == "IDLE"

    def test_set_field_multiple_times_tracks_changes(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields = {}
        bridge.setField("title", "A")
        bridge.setField("title", "B")
        bridge.setField("title", "C")
        assert bridge._all_fields["title"] == "C"
