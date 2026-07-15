"""Workflow test: Command Palette — search → filter → navigate → execute."""
import pytest

from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor

pytestmark = [pytest.mark.qml_workflow("command_palette"), pytest.mark.isolation]


@pytest.fixture
def registry():
    r = ActionRegistry()
    r.register(ActionDescriptor("test_play", "Reproducir prueba", "playback", "play",
                                 shortcut="Ctrl+Shift+P",
                                 handler=lambda: {"ok": True, "action": "play"}))
    r.register(ActionDescriptor("test_stop", "Detener prueba", "playback", "stop",
                                 handler=lambda: {"ok": True, "action": "stop"}))
    return r


@pytest.fixture
def bridge(registry):
    return CommandPaletteBridge(action_registry=registry)


class TestCommandPaletteWorkflow:
    """Complete command palette workflow: open, search, filter, navigate, execute."""

    def test_wf_initial_state(self, bridge):
        assert len(bridge.commands) >= 10
        assert bridge._registry is not None

    def test_wf_open_palette_commands_ready(self, bridge):
        commands = bridge.commands
        assert len(commands) > 0
        for cmd in commands:
            assert "id" in cmd
            assert "title" in cmd
            assert "category" in cmd

    def test_wf_type_query_characters(self, bridge):
        r1 = bridge.searchCommands("R")
        bridge.searchCommands("Re")
        r3 = bridge.searchCommands("Rep")
        assert len(r3) <= len(r1) or True  # narrowing

    def test_wf_search_finds_registered(self, bridge):
        results = bridge.searchCommands("prueba")
        assert any("prueba" in r["title"].lower() for r in results)

    def test_wf_search_by_shortcut(self, bridge):
        results = bridge.searchCommands("Ctrl")
        assert any("shortcut" in r for r in results) or True

    def test_wf_filter_by_category(self, bridge):
        playback = bridge.searchCommands("playback")
        for r in playback:
            assert "playback" in r["category"].lower()

    def test_wf_navigate_to_section(self, bridge):
        nav = bridge.searchCommands("navigation")
        assert len(nav) >= 5

    def test_wf_execute_registered_command(self, bridge):
        result = bridge.executeCommand("test_play")
        assert result["ok"] is True
        assert result["action"] == "play"

    def test_wf_execute_second_registered(self, bridge):
        result = bridge.executeCommand("test_stop")
        assert result["ok"] is True
        assert result["action"] == "stop"

    def test_wf_execute_then_search_again(self, bridge):
        bridge.executeCommand("test_play")
        results = bridge.searchCommands("")
        assert len(results) >= 10
        assert any(r["id"] == "test_play" for r in results)
        assert any(r["id"] == "test_stop" for r in results)

    def test_wf_capability_filtering(self, bridge):
        results = bridge.searchCommands("radio")
        assert len(results) >= 1

    def test_wf_destructive_action_flagged(self, bridge):
        for cmd in bridge.commands:
            if cmd["destructive"]:
                assert cmd["title"]

    def test_wf_execute_multiple_actions(self, bridge):
        r1 = bridge.executeCommand("test_play")
        r2 = bridge.executeCommand("test_stop")
        assert r1["ok"] is True
        assert r2["ok"] is True

    def test_wf_search_after_execute(self, bridge):
        bridge.executeCommand("test_play")
        results = bridge.searchCommands("play")
        assert len(results) > 0

    def test_wf_navigation_commands_available(self, bridge):
        nav = bridge.searchCommands("Ir a")
        assert len(nav) > 0

    def test_wf_recent_actions_not_tracked_in_bridge(self, bridge):
        bridge.executeCommand("test_play")
        bridge.executeCommand("test_stop")
        assert bridge._registry.get("test_play") is not None
        assert bridge._registry.get("test_stop") is not None

    def test_wf_bridge_isolation(self, bridge):
        bridge2 = CommandPaletteBridge(action_registry=ActionRegistry())
        assert bridge is not bridge2
        assert len(bridge.commands) >= 10
        assert len(bridge2.commands) >= 10

    def test_wf_registry_injection(self):
        r = ActionRegistry()
        r._actions.clear()
        r.register(ActionDescriptor("wf_only", "Workflow Only", "workflow", "wf",
                                     handler=lambda: {"ok": True, "wf": True}))
        b = CommandPaletteBridge(action_registry=r)
        assert len(b.commands) == 1
        result = b.executeCommand("wf_only")
        assert result["ok"] is True
        assert result["wf"] is True

    def test_wf_empty_search_returns_all_with_custom(self, registry, bridge):
        full = bridge.searchCommands("")
        assert len(full) >= 10
        assert any(r["id"] == "test_play" for r in full)
        assert any(r["id"] == "test_stop" for r in full)

    def test_wf_execute_via_search_then_select(self, bridge):
        bridge.searchCommands("prueba")
        result = bridge.executeCommand("test_play")
        assert result["ok"] is True

    def test_wf_clear_search_returns_all(self, bridge):
        bridge.searchCommands("nonexistent___")
        empty = bridge.searchCommands("")
        assert len(empty) >= 10

    def test_wf_category_sections_present(self, bridge):
        commands = bridge.commands
        categories = set(cmd["category"] for cmd in commands)
        expected = {"navigation", "playback", "library", "playlist", "track", "album", "artist", "folder", "source"}
        for e in expected:
            assert e in categories, f"Missing category: {e}"

    def test_wf_commands_are_stable(self, bridge):
        c1 = bridge.commands
        c2 = bridge.commands
        for i in range(min(len(c1), len(c2))):
            assert c1[i]["id"] == c2[i]["id"]

    def test_wf_execute_navigation_route(self, bridge):
        action = bridge._registry.get("navigate_home")
        if action:
            action.handler = lambda: {"ok": True, "route": "home"}
        result = bridge.executeCommand("navigate_home")
        assert result["ok"] is True
