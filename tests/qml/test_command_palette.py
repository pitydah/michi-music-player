from __future__ import annotations
"""Test command palette search, navigation, activation."""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor


@pytest.fixture
def registry():
    r = ActionRegistry()
    r.register(ActionDescriptor("test_play", "Reproducir", "playback", "play", "Ctrl+P"))
    r.register(ActionDescriptor("test_pause", "Pausar", "playback", "pause", "Ctrl+Space"))
    r.register(ActionDescriptor("test_search", "Buscar", "navigation", "search", "Ctrl+F"))
    r.register(ActionDescriptor("test_quit", "Salir", "system", "quit", "Ctrl+Q"))
    r.register(ActionDescriptor("test_volume_up", "Subir volumen", "playback", "volume_up"))
    return r


@pytest.fixture
def bridge(registry):
    return CommandPaletteBridge(action_registry=registry)


class TestCommandPalette:

    def test_search_all_commands(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) >= 5

    def test_search_by_title_exact(self, bridge):
        results = bridge.searchCommands("Reproducir")
        assert len(results) >= 1
        assert any("Reproducir" in r["title"] for r in results)

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
        for cmd in bridge.commands:
            assert "id" in cmd
            assert "title" in cmd
            assert "category" in cmd
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

    def test_empty_registry(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.commands == []
        assert b.searchCommands("") == []
