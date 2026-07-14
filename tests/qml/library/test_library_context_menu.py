"""Tests for library context menu actions via ActionRegistry — 8+ tests."""
from __future__ import annotations

import pytest

from ui_qml_bridge.action_registry import ActionRegistry


@pytest.fixture
def registry():
    return ActionRegistry()


def test_context_menu_play_actions_exist(registry):
    for action_id in ["track_play_now", "track_play_next", "track_add_to_queue",
                      "track_replace_queue"]:
        desc = registry.get(action_id)
        assert desc is not None, f"Missing: {action_id}"
        assert desc.category == "track"


def test_context_menu_favorite_actions_exist(registry):
    for action_id in ["track_favorite", "track_unfavorite"]:
        desc = registry.get(action_id)
        assert desc is not None, f"Missing: {action_id}"
        assert desc.category == "track"


def test_context_menu_playlist_action(registry):
    desc = registry.get("track_add_to_playlist")
    assert desc is not None


def test_context_menu_navigation_actions_exist(registry):
    for action_id in ["track_open_album", "track_open_artist", "track_open_folder"]:
        desc = registry.get(action_id)
        assert desc is not None, f"Missing: {action_id}"
        assert desc.category == "track"


def test_context_menu_metadata_action(registry):
    desc = registry.get("track_edit_metadata")
    assert desc is not None
    assert desc.title == "Editar metadatos"


def test_context_menu_audio_lab_actions_exist(registry):
    for action_id in ["track_analyze_audio_lab", "track_convert",
                      "track_calculate_replaygain"]:
        desc = registry.get(action_id)
        assert desc is not None, f"Missing: {action_id}"
        assert desc.category == "track"


def test_context_menu_integrity_action(registry):
    desc = registry.get("track_check_integrity")
    assert desc is not None


def test_context_menu_device_sync_action(registry):
    desc = registry.get("track_send_to_device")
    assert desc is not None


def test_context_menu_properties_action(registry):
    desc = registry.get("track_show_properties")
    assert desc is not None


def test_context_menu_remove_action(registry):
    desc = registry.get("track_delete_from_library")
    assert desc is not None
    assert desc.destructive is True


def test_context_menu_all_actions_have_titles(registry):
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
