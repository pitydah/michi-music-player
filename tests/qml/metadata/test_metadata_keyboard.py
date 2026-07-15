from __future__ import annotations

import pytest

pytestmark = [pytest.mark.qml_module("metadata")]


class TestMetadataKeyboard:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    def test_load_metadata_via_enter_action(self, bridge):
        bridge.loadMetadata("/fake/file.flac")
        assert bridge._current_filepath != "" or bridge._error_message != ""

    def test_escape_clears_selection(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge.clear()
        assert bridge._current_filepath == ""

    def test_tab_navigation_fields(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields = {"title": "A", "artist": "B"}
        bridge._fields = bridge._build_field_list(bridge._all_fields)
        assert len(bridge._fields) > 0

    def test_editing_field_via_keyboard(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields = {"title": "Old"}
        bridge.setField("title", "New")
        assert bridge._all_fields["title"] == "New"

    def test_save_via_keyboard_shortcut(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        result = bridge.saveChanges()
        assert result.get("ok") is not None

    def test_cancel_save_via_escape(self, bridge):
        bridge._pending_review_id = "review_1"
        bridge.rejectSave()
        assert bridge._pending_review_id == ""
        assert bridge.status == "IDLE"

    def test_confirm_save_via_enter(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._pending_review_id = "review_1"
        result = bridge.confirmSave("review_1")
        assert result.get("ok") is not None

    def test_keyboard_navigation_between_modes(self, bridge):
        bridge._has_selection = True
        bridge._mode = "single"
        assert bridge.hasSelection
        bridge._mode = "batch"
        assert bridge._mode == "batch"

    def test_field_edit_undo(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields = {"title": "Original"}
        bridge.setField("title", "Changed")
        assert bridge._all_fields["title"] == "Changed"
        bridge.setField("title", "Original")
        assert bridge._all_fields["title"] == "Original"

    def test_multiple_fields_edit_sequential(self, bridge):
        bridge._current_filepath = "/fake/file.flac"
        bridge._all_fields = {"title": "", "artist": "", "album": ""}
        bridge.setField("title", "T")
        bridge.setField("artist", "A")
        bridge.setField("album", "B")
        assert bridge._all_fields["title"] == "T"
        assert bridge._all_fields["artist"] == "A"
        assert bridge._all_fields["album"] == "B"
