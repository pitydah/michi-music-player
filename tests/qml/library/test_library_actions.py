"""Tests for library actions via ActionRegistry — 15+ tests."""
from __future__ import annotations


import pytest

from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor
import pytest
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def registry():
    return ActionRegistry()


def test_action_registry_init(registry):
    assert registry.get("navigate_home") is not None
    assert registry.get("playback_playpause") is not None


def test_action_registry_track_actions(registry):
    actions = ["track_play_now", "track_play_next", "track_add_to_queue",
               "track_favorite", "track_radio", "track_open_album",
               "track_show_properties", "track_analyze_audio_lab",
               "track_check_integrity", "track_relocate"]
    for a in actions:
        desc = registry.get(a)
        assert desc is not None, f"Missing action: {a}"
        assert desc.category == "track"


def test_action_registry_album_actions(registry):
    actions = ["album_play", "album_shuffle", "album_queue",
               "album_favorite", "album_edit_metadata", "album_change_artwork",
               "album_analyze", "album_sync", "album_open_folder"]
    for a in actions:
        desc = registry.get(a)
        assert desc is not None, f"Missing action: {a}"
        assert desc.category == "album"


def test_action_registry_artist_actions(registry):
    actions = ["artist_play", "artist_shuffle", "artist_queue",
               "artist_add_to_playlist", "artist_radio"]
    for a in actions:
        desc = registry.get(a)
        assert desc is not None, f"Missing action: {a}"
        assert desc.category == "artist"


def test_action_registry_folder_actions(registry):
    actions = ["folder_play", "folder_queue", "folder_open_filesystem",
               "folder_exclude", "folder_rescan"]
    for a in actions:
        desc = registry.get(a)
        assert desc is not None, f"Missing action: {a}"
        assert desc.category == "folder"


def test_action_registry_source_actions(registry):
    actions = ["source_add", "source_edit", "source_remove", "source_enable",
               "source_disable", "source_scan", "source_cancel_scan"]
    for a in actions:
        desc = registry.get(a)
        assert desc is not None, f"Missing action: {a}"
        assert desc.category == "source"


def test_destructive_actions(registry):
    assert registry.get("track_delete_from_disk").destructive is True
    assert registry.get("track_delete_from_disk").requires_confirmation is True
    assert registry.get("track_exclude").destructive is True
    assert registry.get("source_remove").destructive is True
    assert registry.get("folder_exclude").destructive is True


def test_register_custom_action(registry):
    desc = ActionDescriptor("test_action", "Test", "test", handler=lambda: {"ok": True})
    registry.register(desc)
    assert registry.get("test_action") is not None


def test_execute_action_no_handler(registry):
    result = registry.execute("navigate_home")
    assert result["ok"] is False
    assert result["error"] == "NO_HANDLER"


def test_execute_action_with_handler(registry):
    def handler():
        return {"ok": True, "data": "done"}
    desc = ActionDescriptor("test_ok", "Test", "test", handler=handler)
    registry.register(desc)
    result = registry.execute("test_ok")
    assert result["ok"] is True
    assert result["data"] == "done"


def test_execute_nonexistent(registry):
    result = registry.execute("nonexistent")
    assert result["ok"] is False


def test_execute_disabled(registry):
    desc = ActionDescriptor("disabled_action", "Disabled", "test")
    desc.enabled = False
    registry.register(desc)
    result = registry.execute("disabled_action")
    assert result["ok"] is False


def test_get_by_category(registry):
    nav_actions = registry.get_by_category("navigation")
    assert len(nav_actions) > 0
    for a in nav_actions:
        assert a["category"] == "navigation"


def test_actions_property(registry):
    all_actions = registry.actions
    assert len(all_actions) > 0
    for a in all_actions:
        assert "id" in a
        assert "title" in a
        assert "category" in a


def test_visible_actions_only(registry):
    desc = registry.get("app_quit")
    desc.visible = False
    actions = registry.actions
    assert not any(a["id"] == "app_quit" for a in actions)


def test_track_analyze_actions(registry):
    for action_id in ["track_analyze_audio_lab", "track_convert",
                      "track_calculate_replaygain", "track_check_integrity",
                      "track_find_duplicates", "track_send_to_device"]:
        desc = registry.get(action_id)
        assert desc is not None, f"Missing action: {action_id}"


def test_track_delete_actions(registry):
    desc = registry.get("track_delete_from_library")
    assert desc is not None
    assert desc.destructive is True
    desc2 = registry.get("track_delete_from_disk")
    assert desc2 is not None
    assert desc2.destructive is True
    assert desc2.requires_confirmation is True
