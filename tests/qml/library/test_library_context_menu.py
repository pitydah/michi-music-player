"""Advanced tests for LibraryTrackContextMenu via ActionRegistry — 10+ tests."""
from __future__ import annotations

import pytest

from ui_qml_bridge.action_registry import ActionRegistry
import pytest
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def registry():
    return ActionRegistry()


class TestLibraryContextMenu:
    def test_context_menu_play_actions_exist(self, registry):
        for action_id in ["track_play_now", "track_play_next", "track_add_to_queue",
                          "track_replace_queue"]:
            desc = registry.get(action_id)
            assert desc is not None, f"Missing: {action_id}"
            assert desc.category == "track"

    def test_context_menu_favorite_actions_exist(self, registry):
        for action_id in ["track_favorite", "track_unfavorite"]:
            desc = registry.get(action_id)
            assert desc is not None, f"Missing: {action_id}"
            assert desc.category == "track"

    def test_context_menu_playlist_action(self, registry):
        desc = registry.get("track_add_to_playlist")
        assert desc is not None
        assert desc.title == "Añadir a playlist"

    def test_context_menu_navigation_actions_exist(self, registry):
        for action_id in ["track_open_album", "track_open_artist", "track_open_folder"]:
            desc = registry.get(action_id)
            assert desc is not None, f"Missing: {action_id}"
            assert desc.category == "track"

    def test_context_menu_metadata_action(self, registry):
        desc = registry.get("track_edit_metadata")
        assert desc is not None
        assert desc.title == "Editar metadatos"

    def test_context_menu_audio_lab_actions_exist(self, registry):
        for action_id in ["track_analyze_audio_lab", "track_convert",
                          "track_calculate_replaygain"]:
            desc = registry.get(action_id)
            assert desc is not None, f"Missing: {action_id}"
            assert desc.category == "track"

    def test_context_menu_integrity_action(self, registry):
        desc = registry.get("track_check_integrity")
        assert desc is not None
        assert desc.title == "Verificar integridad"

    def test_context_menu_device_sync_action(self, registry):
        desc = registry.get("track_send_to_device")
        assert desc is not None
        assert desc.title == "Enviar a dispositivo"

    def test_context_menu_properties_action(self, registry):
        desc = registry.get("track_show_properties")
        assert desc is not None
        assert desc.title == "Propiedades"

    def test_context_menu_remove_action(self, registry):
        desc = registry.get("track_delete_from_library")
        assert desc is not None
        assert desc.destructive is True

    def test_context_menu_all_actions_have_titles(self, registry):
        track_actions = [
            "track_play_now", "track_play_next", "track_add_to_queue",
            "track_replace_queue", "track_favorite", "track_unfavorite",
            "track_add_to_playlist", "track_open_album", "track_open_artist",
            "track_open_folder", "track_edit_metadata", "track_analyze_audio_lab",
            "track_convert", "track_calculate_replaygain", "track_check_integrity",
            "track_send_to_device", "track_show_properties", "track_delete_from_library",
        ]
        for action_id in track_actions:
            desc = registry.get(action_id)
            assert desc is not None, f"Missing: {action_id}"
            assert desc.title, f"Empty title for: {action_id}"

    def test_context_menu_actions_not_destructive_by_default(self, registry):
        non_destructive = ["track_play_now", "track_add_to_queue", "track_favorite",
                           "track_open_album", "track_edit_metadata"]
        for action_id in non_destructive:
            desc = registry.get(action_id)
            assert desc is not None
            assert not desc.destructive, f"{action_id} should not be destructive"

    def test_context_menu_delete_is_destructive(self, registry):
        desc = registry.get("track_delete_from_library")
        assert desc is not None
        assert desc.destructive is True

    def test_context_menu_no_library_sort_menu_actions(self, registry):
        sort_actions = [a for a in registry.actions if "sort" in a.get("id", "")]
        assert len(sort_actions) == 0, "SortMenu actions should not be in context menu registry"
