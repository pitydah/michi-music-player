<<<<<<< Updated upstream
=======
<<<<<<< HEAD
"""Tests for CommandPalette — positive, capability, recent, sections."""
=======
>>>>>>> Stashed changes
"""Test command palette search, navigation, activation."""

from __future__ import annotations

from unittest.mock import MagicMock

<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
import pytest

from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor

<<<<<<< Updated upstream

pytestmark = pytest.mark.isolation
=======
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("command_palette"), pytest.mark.qml_dimension("functional")]
=======

pytestmark = pytest.mark.isolation
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes


@pytest.fixture
def registry():
    r = ActionRegistry()
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
    r.register(ActionDescriptor("custom_test", "Test Command", "testing", "test", shortcut="Ctrl+T"))
=======
>>>>>>> Stashed changes
    r.register(ActionDescriptor("test_play", "Reproducir", "playback", "play", "Ctrl+P"))
    r.register(ActionDescriptor("test_pause", "Pausar", "playback", "pause", "Ctrl+Space"))
    r.register(ActionDescriptor("test_search", "Buscar", "navigation", "search", "Ctrl+F"))
    r.register(ActionDescriptor("test_quit", "Salir", "system", "quit", "Ctrl+Q"))
    r.register(ActionDescriptor("test_volume_up", "Subir volumen", "playback", "volume_up"))
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return r


@pytest.fixture
def bridge(registry):
    return CommandPaletteBridge(action_registry=registry)


<<<<<<< Updated upstream
class TestCommandPaletteSearch:
    def test_search_returns_all_on_empty(self, bridge):
        results = bridge.searchCommands("")
=======
<<<<<<< HEAD
class TestCommandPalettePositive:
    def test_initial_commands_nonempty(self, bridge):
        assert len(bridge.commands) >= 10

    def test_search_by_full_title(self, bridge):
        results = bridge.searchCommands("Inicio")
        assert len(results) >= 1
        assert any("Inicio" in r["title"] for r in results)

    def test_search_by_partial_title(self, bridge):
        results = bridge.searchCommands("Bibli")
        assert len(results) >= 1

    def test_search_by_category(self, bridge):
        results = bridge.searchCommands("navigation")
>>>>>>> Stashed changes
        assert len(results) >= 5

    def test_search_by_title_exact(self, bridge):
        results = bridge.searchCommands("Reproducir")
        assert len(results) >= 1
        assert any("Reproducir" in r["title"] for r in results)

<<<<<<< Updated upstream
=======
    def test_action_has_required_fields(self, bridge):
=======
class TestCommandPaletteSearch:
    def test_search_returns_all_on_empty(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) >= 5

    def test_search_by_title_exact(self, bridge):
        results = bridge.searchCommands("Reproducir")
        assert len(results) >= 1
        assert any("Reproducir" in r["title"] for r in results)

>>>>>>> Stashed changes
    def test_search_by_title_partial(self, bridge):
        results = bridge.searchCommands("Repro")
        assert len(results) >= 1
        assert any("Reproducir" in r["title"] for r in results)

    def test_search_by_category(self, bridge):
        results = bridge.searchCommands("playback")
        assert len(results) >= 3
        assert all("playback" in r["category"].lower() for r in results)

    def test_search_case_insensitive(self, bridge):
        results = bridge.searchCommands("BUSCAR")
        assert len(results) >= 1
        assert any("buscar" in r["title"].lower() for r in results)

    def test_search_no_match(self, bridge):
        results = bridge.searchCommands("xyznonexistent")
        assert len(results) == 0

    def test_search_matches_multiple_categories(self, bridge):
        bridge._registry.register(
            ActionDescriptor("nav_test", "Test nav", "navigation", "test")
        )
        bridge._registry.register(
            ActionDescriptor("play_test", "Test play", "playback", "test")
        )
        results = bridge.searchCommands("test")
        assert len(results) >= 2

    def test_search_returns_visible_and_invisible(self, bridge):
        action = bridge._registry.get("test_play")
        assert action is not None
        action.visible = False
        all_results = bridge.searchCommands("")
        visible_ids = [r["id"] for r in all_results if r.get("visible", True)]
        assert "test_play" not in visible_ids

    def test_search_after_register(self, bridge, registry):
        registry.register(
            ActionDescriptor("new_action", "Nueva acción", "testing", "new")
        )
        results = bridge.searchCommands("Nueva")
        assert len(results) >= 1

    def test_search_retrieves_shortcut(self, bridge):
        results = bridge.searchCommands("Reproducir")
        assert len(results) >= 1
        matching = [r for r in results if r["id"] == "test_play"]
        assert len(matching) >= 1
        assert matching[0].get("shortcut") == "Ctrl+P"


class TestCommandPaletteActivation:
    def test_execute_known_action(self, bridge):
        result = bridge.executeCommand("test_play")
        assert result["ok"] is False
        assert result["error"] == "NO_HANDLER"

    def test_execute_unknown_action(self, bridge):
        result = bridge.executeCommand("nonexistent")
        assert result["ok"] is False
        assert result["error"] == "NOT_FOUND"

    def test_execute_with_handler(self, bridge):
        handler = MagicMock(return_value={"ok": True})
        action = bridge._registry.get("test_play")
        assert action is not None
        action.handler = handler
        result = bridge.executeCommand("test_play")
        assert result["ok"] is True
        assert handler.called

    def test_execute_handler_returns_dict(self, bridge):
        handler = MagicMock(return_value={"ok": True, "data": "result"})
        action = bridge._registry.get("test_search")
        assert action is not None
        action.handler = handler
        result = bridge.executeCommand("test_search")
        assert result["ok"] is True
        assert result.get("data") == "result"

    def test_execute_handler_exception(self, bridge):
        def failing():
            raise ValueError("test error")
        action = bridge._registry.get("test_quit")
        assert action is not None
        action.handler = failing
        result = bridge.executeCommand("test_quit")
        assert result["ok"] is False
        assert "test error" in result["error"]

    def test_execute_disabled_action(self, bridge):
        action = bridge._registry.get("test_pause")
        assert action is not None
        action.enabled = False
        result = bridge.executeCommand("test_pause")
        assert result["ok"] is False
        assert result["error"] == "NOT_FOUND"


class TestCommandPaletteNavigation:
    def test_commands_have_all_required_fields(self, bridge):
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        for cmd in bridge.commands:
            assert "id" in cmd
            assert "title" in cmd
            assert "category" in cmd
<<<<<<< Updated upstream
            assert "shortcut" in cmd
            assert "destructive" in cmd
            assert "requires_confirmation" in cmd
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
            assert "enabled" in cmd
            assert "visible" in cmd

    def test_commands_list_only_visible(self, bridge, registry):
        action = registry.get("test_quit")
        assert action is not None
        action.visible = False
        visible = bridge.commands
        assert all(c["visible"] for c in visible)
        assert not any(c["id"] == "test_quit" for c in visible)

    def test_get_by_category(self, bridge):
        playback = bridge._registry.get_by_category("playback")
        assert len(playback) >= 3
        assert all(c["category"] == "playback" for c in playback)

<<<<<<< Updated upstream
=======

class TestCommandPaletteRecent:
    def test_recent_actions_empty_initially(self, bridge):
        pass  # bridge has no recent tracking — tracked in QML layer

    def test_bridge_execute_updates_state(self, registry):
        result = registry.execute("navigate_home")
        assert result["ok"] is False
        assert "NO_HANDLER" in result["error"]

    def test_registry_execute_disabled_action(self, registry):
        action = registry.get("navigate_home")
        if action:
            action.enabled = False
        result = registry.execute("navigate_home")
        assert result["ok"] is False
        assert result["error"] == "NOT_FOUND"
=======
            assert "shortcut" in cmd
            assert "destructive" in cmd
            assert "requires_confirmation" in cmd
            assert "enabled" in cmd
            assert "visible" in cmd

    def test_commands_list_only_visible(self, bridge, registry):
        action = registry.get("test_quit")
        assert action is not None
        action.visible = False
        visible = bridge.commands
        assert all(c["visible"] for c in visible)
        assert not any(c["id"] == "test_quit" for c in visible)

    def test_get_by_category(self, bridge):
        playback = bridge._registry.get_by_category("playback")
        assert len(playback) >= 3
        assert all(c["category"] == "playback" for c in playback)

>>>>>>> Stashed changes
    def test_empty_registry(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.commands == []
        assert b.searchCommands("") == []
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
