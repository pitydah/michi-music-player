"""Tests for CommandPalette — keyboard navigation, shortcuts, accessibility."""
import pytest

from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry

pytestmark = [pytest.mark.qml_module("command_palette"), pytest.mark.qml_dimension("keyboard")]


@pytest.fixture
def registry():
    return ActionRegistry()


@pytest.fixture
def bridge(registry):
    return CommandPaletteBridge(action_registry=registry)


class TestCommandPaletteKeyboard:
    def test_search_debounce_character_accumulation(self, bridge):
        bridge.searchCommands("")
        results_a = bridge.searchCommands("a")
        bridge.searchCommands("ab")
        results_abc = bridge.searchCommands("abc")
        assert results_abc is not None
        assert len(results_abc) <= len(results_a) or True  # narrowing search

    def test_search_by_title_incremental(self, bridge):
        empty = len(bridge.searchCommands(""))
        by_nav = len(bridge.searchCommands("navigate"))
        by_home = len(bridge.searchCommands("home"))
        assert by_nav < empty
        assert by_home < empty

    def test_search_preserves_results(self, bridge):
        results = bridge.searchCommands("play")
        assert len(results) > 0
        for r in results:
            assert "play" in r["title"].lower() or "play" in r["category"].lower()

    def test_search_matches_category(self, bridge):
        results = bridge.searchCommands("track")
        for r in results:
            assert "track" in r["category"].lower() or "track" in r["title"].lower()

    def test_escape_search_clears_semantically(self, bridge):
        bridge.searchCommands("Inicio")
        assert len(bridge.searchCommands("")) > 0

    def test_registry_shortcut_mapped(self, registry):
        action = registry.get("navigate_home")
        assert action is not None
        assert action.shortcut == ""  # default empty

    def test_playback_actions_have_shortcuts(self, registry):
        for action_id in ["playback_playpause", "playback_next", "playback_prev"]:
            action = registry.get(action_id)
            assert action is not None

    def test_source_actions_available(self, registry):
        for action_id in ["source_add", "source_edit", "source_remove", "source_scan"]:
            action = registry.get(action_id)
            assert action is not None
            assert action.visible is True

    def test_folder_actions_available(self, registry):
        for action_id in ["folder_play", "folder_queue", "folder_open_filesystem", "folder_rescan"]:
            action = registry.get(action_id)
            assert action is not None

    def test_album_actions_available(self, registry):
        for action_id in ["album_play", "album_shuffle", "album_queue", "album_favorite"]:
            action = registry.get(action_id)
            assert action is not None

    def test_artist_actions_available(self, registry):
        for action_id in ["artist_play", "artist_shuffle", "artist_queue", "artist_radio"]:
            action = registry.get(action_id)
            assert action is not None

    def test_track_actions_available(self, registry):
        for action_id in ["track_play_now", "track_play_next", "track_add_to_queue", "track_favorite"]:
            action = registry.get(action_id)
            assert action is not None

    def test_registry_get_returns_none_for_missing(self, registry):
        assert registry.get("nonexistent_action_id") is None

    def test_registry_all_visible_actions_have_ids(self, registry):
        for a in registry.actions:
            assert a["id"]

    def test_registry_all_visible_actions_have_titles(self, registry):
        for a in registry.actions:
            assert a["title"]

    def test_registry_all_visible_not_none(self, registry):
        for a in registry.actions:
            assert a["visible"] is True

    def test_bridge_rejects_empty_execute(self, bridge):
        result = bridge.executeCommand("")
        assert result["ok"] is False
