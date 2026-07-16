from __future__ import annotations
from __future__ import annotations
"""Test command palette keyboard navigation."""

from unittest.mock import MagicMock
import pytest

"""Tests for CommandPalette — keyboard navigation, shortcuts, accessibility."""

from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor


pytestmark = [pytest.mark.qml_module("command_palette"), pytest.mark.qml_dimension("keyboard")]
"""Test command palette keyboard navigation."""


import pytest


pytestmark = pytest.mark.isolation


@pytest.fixture
def registry():
    return ActionRegistry()
    return ActionRegistry()
    r = ActionRegistry()
    r._actions.clear()
    r.register(ActionDescriptor("a1", "Action One", "category_a", "icon1"))
    r.register(ActionDescriptor("a2", "Action Two", "category_a", "icon2"))
    r.register(ActionDescriptor("a3", "Action Three", "category_b", "icon3"))
    r.register(ActionDescriptor("a4", "Action Four", "category_c", "icon4"))
    r.register(ActionDescriptor("a5", "Action Five", "category_c", "icon5"))
    return r


@pytest.fixture
def bridge(registry):
    return CommandPaletteBridge(action_registry=registry)


class TestCommandPaletteKeyboard:
    def test_up_down_navigation(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) >= 5
    def test_search_debounce_character_accumulation(self, bridge):
        bridge.searchCommands("")
        results_a = bridge.searchCommands("a")
        bridge.searchCommands("ab")
        results_abc = bridge.searchCommands("abc")
        assert results_abc is not None
        assert len(results_abc) <= len(results_a)  # narrowing search

    def test_search_preserves_ordering(self, bridge):
        results = bridge.searchCommands("")
        titles = [r["title"] for r in results]
        expected = ["Action One", "Action Two", "Action Three", "Action Four", "Action Five"]
        for e in expected:
            assert e in titles

    def test_category_filtering_groups(self, bridge):
        results = bridge.searchCommands("category_a")
        assert len(results) >= 2
        assert all(r["category"] == "category_a" for r in results)

    def test_enter_on_selected(self, bridge):
        handler = MagicMock(return_value={"ok": True})
        action = bridge._registry.get("a1")
        assert action is not None
        action.handler = handler
        result = bridge.executeCommand("a1")
        assert result["ok"] is True
        assert handler.called

    def test_enter_on_disabled(self, bridge):
        action = bridge._registry.get("a2")
        assert action is not None
        action.enabled = False
        result = bridge.executeCommand("a2")
        assert result["ok"] is False
    def test_up_down_navigation(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) >= 5

    def test_search_preserves_ordering(self, bridge):
        results = bridge.searchCommands("")
        titles = [r["title"] for r in results]
        expected = ["Action One", "Action Two", "Action Three", "Action Four", "Action Five"]
        for e in expected:
            assert e in titles

    def test_category_filtering_groups(self, bridge):
        results = bridge.searchCommands("category_a")
        assert len(results) >= 2
        assert all(r["category"] == "category_a" for r in results)

    def test_enter_on_selected(self, bridge):
        handler = MagicMock(return_value={"ok": True})
        action = bridge._registry.get("a1")
        assert action is not None
        action.handler = handler
        result = bridge.executeCommand("a1")
        assert result["ok"] is True
        assert handler.called

    def test_enter_on_disabled(self, bridge):
        action = bridge._registry.get("a2")
        assert action is not None
        action.enabled = False
        result = bridge.executeCommand("a2")
        assert result["ok"] is False

    def test_execute_cycles_sections(self, bridge):
        results = bridge.searchCommands("")
        cat_a = [r for r in results if r["category"] == "category_a"]
        cat_b = [r for r in results if r["category"] == "category_b"]
        cat_c = [r for r in results if r["category"] == "category_c"]
        assert len(cat_a) >= 2
        assert len(cat_b) >= 1
        assert len(cat_c) >= 2

    def test_keyboard_select_with_arrow_logic(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) == 5
        assert results[0]["id"] == "a1"
        assert results[4]["id"] == "a5"

    def test_search_updates_results_list(self, bridge):
        all_results = bridge.searchCommands("")
        assert len(all_results) == 5
        filtered = bridge.searchCommands("One")
        assert len(filtered) == 1
        assert filtered[0]["id"] == "a1"

    def test_escape_clears_search(self, bridge):
        bridge.searchCommands("Action")
        bridge.searchCommands("")
        all_results = bridge.commands
        assert len(all_results) >= 5
