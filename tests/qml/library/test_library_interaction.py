from __future__ import annotations
"""Tests for library context menu, selection bar, keyboard actions — 12+ tests."""

import pytest

from ui_qml_bridge.selection_controller import SelectionController
from ui_qml_bridge.action_registry import ActionRegistry


class TestLibraryInteraction:
    @pytest.fixture
    def registry(self):
        return ActionRegistry()

    @pytest.fixture
    def sel(self):
        return SelectionController()

    def test_context_menu_play(self, registry):
        desc = registry.get("track_play_now")
        assert desc is not None
        assert desc.category == "track"

    def test_context_menu_add_to_queue(self, registry):
        desc = registry.get("track_add_to_queue")
        assert desc is not None
        assert desc.category == "track"

    def test_context_menu_add_to_playlist(self, registry):
        desc = registry.get("track_add_to_playlist")
        assert desc is not None

    def test_context_menu_go_to_album(self, registry):
        desc = registry.get("track_open_album")
        assert desc is not None
        assert desc.category == "track"

    def test_context_menu_go_to_artist(self, registry):
        desc = registry.get("track_open_artist")
        assert desc is not None

    def test_context_menu_edit_metadata(self, registry):
        desc = registry.get("track_edit_metadata")
        assert desc is not None

    def test_context_menu_show_in_folder(self, registry):
        desc = registry.get("track_open_folder")
        assert desc is not None

    def test_context_menu_properties(self, registry):
        desc = registry.get("track_show_properties")
        assert desc is not None

    def test_selection_bar_play_selected(self, registry):
        desc = registry.get("track_play_now")
        assert desc is not None
        result = registry.execute("track_play_now")
        assert result is not None

    def test_selection_bar_add_to_queue(self, registry):
        desc = registry.get("track_add_to_queue")
        assert desc is not None
        result = registry.execute("track_add_to_queue")
        assert result is not None

    def test_selection_bar_add_to_playlist(self, registry):
        desc = registry.get("track_add_to_playlist")
        assert desc is not None
        result = registry.execute("track_add_to_playlist")
        assert result is not None

    def test_selection_bar_remove_from_library(self, registry):
        desc = registry.get("track_delete_from_library")
        assert desc is not None
        assert desc.destructive

    def test_selection_controller_toggle(self, sel):
        sel.toggle(5)
        assert sel.count == 1
        assert 5 in sel.selectedIds

    def test_selection_controller_clear(self, sel):
        sel.replace([1, 2, 3])
        assert sel.count == 3
        sel.clear()
        assert sel.count == 0

    def test_selection_controller_replace(self, sel):
        sel.replace([10, 20, 30])
        assert sel.count == 3
        assert list(sel.selectedIds) == [10, 20, 30]

    def test_selection_controller_has_selection(self, sel):
        assert not sel.hasSelection
        sel.add(1)
        assert sel.hasSelection

    def test_selection_controller_generation(self, sel):
        gen0 = sel.generation
        sel.toggle(1)
        assert sel.generation > gen0

    def test_context_menu_all_actions_exist(self, registry):
        actions = [
            "track_play_now", "track_add_to_queue", "track_add_to_playlist",
            "track_open_album", "track_open_artist", "track_open_folder",
            "track_edit_metadata", "track_show_properties", "track_delete_from_library",
        ]
        for action_id in actions:
            desc = registry.get(action_id)
            assert desc is not None, f"Missing: {action_id}"
            assert desc.title, f"Empty title for: {action_id}"
