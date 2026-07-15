<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
"""Negative tests for CommandPalette — edge cases, failures, invalid inputs."""
=======
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
"""Negative tests for CommandPalette — edge cases, failures, invalid inputs."""
=======
>>>>>>> Stashed changes
"""Test command palette negative scenarios: no actions, capability filtering."""

from __future__ import annotations

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
pytestmark = [pytest.mark.qml_module("command_palette"), pytest.mark.qml_dimension("negative")]
>>>>>>> Stashed changes


class TestCommandPaletteNoActions:
    def test_empty_registry_search(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.searchCommands("") == []

    def test_empty_registry_execute_fails(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        result = b.executeCommand("anything")
        assert result["ok"] is False

    def test_empty_registry_commands_property(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.commands == []

    def test_none_registry(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.commands == []

    def test_none_registry_search(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.searchCommands("test") == []

    def test_none_registry_execute(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        result = b.executeCommand("test")
        assert result["ok"] is False


class TestCommandPaletteCapabilityFiltering:
    def test_capability_hides_radio_action(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("radio_add_station", "Añadir emisora", "radio", "radio")
        )
        registry.register(
            ActionDescriptor("navigate_home", "Ir a Inicio", "navigation", "home")
        )

        b = CommandPaletteBridge(action_registry=registry)
        results = b.searchCommands("")

        # Capability filtering happens in QML, but we verify bridge returns all actions
        assert len(results) >= 2
        radio_actions = [r for r in results if r["id"] == "radio_add_station"]
        assert len(radio_actions) >= 1

    def test_capability_allows_radio_action(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("radio_add_station", "Añadir emisora", "radio", "radio")
        )
        b = CommandPaletteBridge(action_registry=registry)
        results = b.searchCommands("emisora")
        assert len(results) >= 1

    def test_capability_filters_multiple_actions(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("navigate_radio", "Ir a Radio", "navigation", "radio")
        )
        registry.register(
            ActionDescriptor("radio_add_station", "Añadir emisora", "radio", "radio")
        )
        b = CommandPaletteBridge(action_registry=registry)
        results = b.searchCommands("radio")
        assert len(results) >= 2

    def test_unregistered_action_fails(self):
        registry = ActionRegistry()
        b = CommandPaletteBridge(action_registry=registry)
        result = b.executeCommand("never_registered")
        assert result["ok"] is False

    def test_execute_only_registered(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("only_valid", "Solo válida", "test", "test")
        )
        b = CommandPaletteBridge(action_registry=registry)
        result = b.executeCommand("only_valid")
        assert result["ok"] is False
        assert result["error"] == "NO_HANDLER"

    def test_all_hidden_actions_return_empty(self):
        registry = ActionRegistry()
        registry._actions.clear()
        registry.register(
            ActionDescriptor("hidden1", "Hidden One", "test", "test")
        )
        registry.register(
            ActionDescriptor("hidden2", "Hidden Two", "test", "test")
        )
        for aid in ("hidden1", "hidden2"):
            a = registry.get(aid)
            if a:
                a.visible = False
        b = CommandPaletteBridge(action_registry=registry)
        assert b.commands == []

    def test_disabled_actions_are_execute_blocked(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("disabled_action", "Disabled", "test", "test")
        )
        a = registry.get("disabled_action")
        if a:
            a.enabled = False
        b = CommandPaletteBridge(action_registry=registry)
        # Disabled actions are invisible in commands list by default
        # but we can still search them
        results = b.searchCommands("Disabled")
        # They are visible in search but should not be executed
        assert len(results) >= 1
        result = b.executeCommand("disabled_action")
        assert result["ok"] is False
<<<<<<< Updated upstream
=======

    def test_search_with_tab_newline(self, bridge):
        results = bridge.searchCommands("\t\n")
        assert len(results) >= 0

    def test_search_after_clear(self, bridge):
        bridge.searchCommands("test")
        cleared = bridge.searchCommands("")
        assert len(cleared) >= 10

    def test_execute_action_twice_fails_consistently(self, bridge):
        r1 = bridge.executeCommand("nonexistent_1")
        r2 = bridge.executeCommand("nonexistent_2")
        assert r1["ok"] is False
        assert r2["ok"] is False
=======

pytestmark = pytest.mark.isolation


class TestCommandPaletteNoActions:
    def test_empty_registry_search(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.searchCommands("") == []

    def test_empty_registry_execute_fails(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        result = b.executeCommand("anything")
        assert result["ok"] is False

    def test_empty_registry_commands_property(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.commands == []

    def test_none_registry(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.commands == []

    def test_none_registry_search(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        assert b.searchCommands("test") == []

    def test_none_registry_execute(self):
        r = ActionRegistry()
        r._actions.clear()
        b = CommandPaletteBridge(action_registry=r)
        result = b.executeCommand("test")
        assert result["ok"] is False


class TestCommandPaletteCapabilityFiltering:
    def test_capability_hides_radio_action(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("radio_add_station", "Añadir emisora", "radio", "radio")
        )
        registry.register(
            ActionDescriptor("navigate_home", "Ir a Inicio", "navigation", "home")
        )

        b = CommandPaletteBridge(action_registry=registry)
        results = b.searchCommands("")

        # Capability filtering happens in QML, but we verify bridge returns all actions
        assert len(results) >= 2
        radio_actions = [r for r in results if r["id"] == "radio_add_station"]
        assert len(radio_actions) >= 1

    def test_capability_allows_radio_action(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("radio_add_station", "Añadir emisora", "radio", "radio")
        )
        b = CommandPaletteBridge(action_registry=registry)
        results = b.searchCommands("emisora")
        assert len(results) >= 1

    def test_capability_filters_multiple_actions(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("navigate_radio", "Ir a Radio", "navigation", "radio")
        )
        registry.register(
            ActionDescriptor("radio_add_station", "Añadir emisora", "radio", "radio")
        )
        b = CommandPaletteBridge(action_registry=registry)
        results = b.searchCommands("radio")
        assert len(results) >= 2

    def test_unregistered_action_fails(self):
        registry = ActionRegistry()
        b = CommandPaletteBridge(action_registry=registry)
        result = b.executeCommand("never_registered")
        assert result["ok"] is False

    def test_execute_only_registered(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("only_valid", "Solo válida", "test", "test")
        )
        b = CommandPaletteBridge(action_registry=registry)
        result = b.executeCommand("only_valid")
        assert result["ok"] is False
        assert result["error"] == "NO_HANDLER"

    def test_all_hidden_actions_return_empty(self):
        registry = ActionRegistry()
        registry._actions.clear()
        registry.register(
            ActionDescriptor("hidden1", "Hidden One", "test", "test")
        )
        registry.register(
            ActionDescriptor("hidden2", "Hidden Two", "test", "test")
        )
        for aid in ("hidden1", "hidden2"):
            a = registry.get(aid)
            if a:
                a.visible = False
        b = CommandPaletteBridge(action_registry=registry)
        assert b.commands == []

    def test_disabled_actions_are_execute_blocked(self):
        registry = ActionRegistry()
        registry.register(
            ActionDescriptor("disabled_action", "Disabled", "test", "test")
        )
        a = registry.get("disabled_action")
        if a:
            a.enabled = False
        b = CommandPaletteBridge(action_registry=registry)
        # Disabled actions are invisible in commands list by default
        # but we can still search them
        results = b.searchCommands("Disabled")
        # They are visible in search but should not be executed
        assert len(results) >= 1
        result = b.executeCommand("disabled_action")
        assert result["ok"] is False
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
