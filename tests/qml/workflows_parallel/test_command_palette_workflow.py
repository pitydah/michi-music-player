<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
"""Workflow test: Command Palette — search → filter → navigate → execute."""
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
"""Workflow test: Command Palette — search → filter → navigate → execute."""
=======
>>>>>>> Stashed changes
"""Workflow test: Open → search → navigate → activate."""

from __future__ import annotations

from unittest.mock import MagicMock

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
import pytest

from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor

<<<<<<< Updated upstream
<<<<<<< Updated upstream

pytestmark = pytest.mark.isolation
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_workflow("command_palette"), pytest.mark.isolation]
=======

pytestmark = pytest.mark.isolation
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes


@pytest.fixture
def registry():
    r = ActionRegistry()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    r.register(ActionDescriptor("test_play", "Reproducir prueba", "playback", "play",
                                 shortcut="Ctrl+Shift+P",
                                 handler=lambda: {"ok": True, "action": "play"}))
    r.register(ActionDescriptor("test_stop", "Detener prueba", "playback", "stop",
                                 handler=lambda: {"ok": True, "action": "stop"}))
=======
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    r._actions.clear()
    r.register(ActionDescriptor("navigate_home", "Ir a Inicio", "navigation", "home"))
    r.register(ActionDescriptor("navigate_library", "Ir a Biblioteca", "navigation", "library"))
    r.register(ActionDescriptor("playback_play", "Reproducir", "playback", "play"))
    r.register(ActionDescriptor("playback_pause", "Pausar", "playback", "pause"))
    r.register(ActionDescriptor("library_scan", "Escanear", "library", "scan"))
    r.register(ActionDescriptor("app_quit", "Salir", "system", "quit"))
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return r


@pytest.fixture
def bridge(registry):
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    nav = MagicMock()
    return CommandPaletteBridge(action_registry=registry, navigation_bridge=nav)


@pytest.fixture
def handler_registry(registry):
    for action_id in ("navigate_home", "playback_play", "app_quit"):
        a = registry.get(action_id)
        if a:
            a.handler = MagicMock(return_value={"ok": True})
    return registry
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    return CommandPaletteBridge(action_registry=registry)
>>>>>>> Stashed changes


class TestCommandPaletteWorkflow:
    def test_workflow_open_search(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) >= 6

    def test_workflow_search_filter_navigation(self, bridge):
        results = bridge.searchCommands("Ir a")
        assert len(results) >= 2
        assert all("ir a" in r["title"].lower() for r in results)

    def test_workflow_search_by_category(self, bridge):
        results = bridge.searchCommands("playback")
        assert len(results) >= 2
        assert all(r["category"] == "playback" for r in results)

    def test_workflow_navigate_to_activate(self, bridge, handler_registry):
        bridge._registry.get("navigate_home").handler = MagicMock(return_value={"ok": True})
        result = bridge.executeCommand("navigate_home")
        assert result["ok"] is True
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
=======
    nav = MagicMock()
    return CommandPaletteBridge(action_registry=registry, navigation_bridge=nav)


@pytest.fixture
def handler_registry(registry):
    for action_id in ("navigate_home", "playback_play", "app_quit"):
        a = registry.get(action_id)
        if a:
            a.handler = MagicMock(return_value={"ok": True})
    return registry


class TestCommandPaletteWorkflow:
    def test_workflow_open_search(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) >= 6

    def test_workflow_search_filter_navigation(self, bridge):
        results = bridge.searchCommands("Ir a")
        assert len(results) >= 2
        assert all("ir a" in r["title"].lower() for r in results)

    def test_workflow_search_by_category(self, bridge):
        results = bridge.searchCommands("playback")
        assert len(results) >= 2
        assert all(r["category"] == "playback" for r in results)

    def test_workflow_navigate_to_activate(self, bridge, handler_registry):
        bridge._registry.get("navigate_home").handler = MagicMock(return_value={"ok": True})
        result = bridge.executeCommand("navigate_home")
        assert result["ok"] is True
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

    def test_workflow_full_cycle_open_search_activate(self, bridge, handler_registry):
        bridge._registry.get("playback_play").handler = MagicMock(return_value={"ok": True})
        results = bridge.searchCommands("Reproducir")
        assert len(results) >= 1
        result = bridge.executeCommand("playback_play")
        assert result["ok"] is True

    def test_workflow_search_nonexistent(self, bridge):
        results = bridge.searchCommands("xyznonexistent")
        assert len(results) == 0

    def test_workflow_execute_invalid_after_search(self, bridge):
        results = bridge.searchCommands("playback")
        assert len(results) >= 2
        result = bridge.executeCommand("nonexistent")
        assert result["ok"] is False

    def test_workflow_search_empty_then_execute(self, bridge):
        bridge.searchCommands("")
        result = bridge.executeCommand("navigate_home")
        assert result["ok"] is False

    def test_workflow_search_cycle_results(self, bridge):
        all_results = bridge.searchCommands("")
        assert len(all_results) == 6
        playback = [r for r in all_results if r["category"] == "playback"]
        assert len(playback) == 2

    def test_workflow_execute_with_handler_success(self, bridge, handler_registry):
        handler = MagicMock(return_value={"ok": True})
        bridge._registry.get("navigate_home").handler = handler
        result = bridge.executeCommand("navigate_home")
        assert result["ok"] is True
        handler.assert_called_once()

    def test_workflow_execute_quit(self, bridge, handler_registry):
        handler = MagicMock()
        bridge._registry.get("app_quit").handler = handler
        bridge.executeCommand("app_quit")
        assert handler.called

    def test_workflow_multiple_searches(self, bridge):
        r1 = bridge.searchCommands("Ir a Inicio")
        assert len(r1) >= 1
        r2 = bridge.searchCommands("playback")
        assert len(r2) >= 2
        r3 = bridge.searchCommands("")
        assert len(r3) >= 6
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
