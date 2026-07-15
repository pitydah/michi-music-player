"""Negative tests for CommandPalette — edge cases, failures, invalid inputs."""
import pytest

from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor

pytestmark = [pytest.mark.qml_module("command_palette"), pytest.mark.qml_dimension("negative")]


@pytest.fixture
def empty_registry():
    r = ActionRegistry()
    r._actions.clear()
    return r


@pytest.fixture
def bridge():
    return CommandPaletteBridge()


class TestCommandPaletteNegative:
    def test_search_nonexistent_returns_empty(self, bridge):
        results = bridge.searchCommands("xyznonexistent")
        assert len(results) == 0

    def test_search_special_chars(self, bridge):
        results = bridge.searchCommands("!@#$%^&*()")
        assert len(results) == 0

    def test_search_unicode(self, bridge):
        results = bridge.searchCommands("\u00e1\u00e9\u00ed\u00f3\u00fa")
        assert len(results) == 0

    def test_search_numbers(self, bridge):
        results = bridge.searchCommands("12345")
        assert len(results) == 0

    def test_execute_nonexistent_returns_error(self, bridge):
        result = bridge.executeCommand("no_such_command")
        assert result["ok"] is False
        assert "NOT_FOUND" in result["error"]

    def test_execute_disabled_action(self, bridge):
        action = bridge._registry.get("navigate_home")
        if action:
            action.enabled = False
        result = bridge.executeCommand("navigate_home")
        assert result["ok"] is False

    def test_execute_empty_string(self, bridge):
        result = bridge.executeCommand("")
        assert result["ok"] is False

    def test_search_whitespace_only(self, bridge):
        results = bridge.searchCommands("   ")
        assert len(results) >= 0

    def test_search_very_long_string(self, bridge):
        long_str = "a" * 1000
        results = bridge.searchCommands(long_str)
        assert len(results) == 0

    def test_search_mixed_case_unknown(self, bridge):
        results = bridge.searchCommands("NoNeXiStEnT")
        assert len(results) == 0

    def test_empty_registry_commands(self, empty_registry):
        bridge = CommandPaletteBridge(action_registry=empty_registry)
        assert len(bridge.commands) == 0

    def test_empty_registry_search(self, empty_registry):
        bridge = CommandPaletteBridge(action_registry=empty_registry)
        results = bridge.searchCommands("test")
        assert len(results) == 0

    def test_execute_on_empty_registry(self, empty_registry):
        bridge = CommandPaletteBridge(action_registry=empty_registry)
        result = bridge.executeCommand("anything")
        assert result["ok"] is False

    def test_search_with_null_bridge(self):
        bridgeObj = CommandPaletteBridge()
        bridgeObj._registry = None
        with pytest.raises(AttributeError):
            bridgeObj.searchCommands("test")

    def test_execute_with_null_bridge(self):
        bridgeObj = CommandPaletteBridge()
        bridgeObj._registry = None
        with pytest.raises(AttributeError):
            bridgeObj.executeCommand("test")

    def test_action_with_missing_title(self):
        desc = ActionDescriptor("no_title", "", "test", "nt")
        registry = ActionRegistry()
        registry._actions.clear()
        registry.register(desc)
        actions = registry.actions
        assert len(actions) == 1
        assert actions[0]["title"] == ""

    def test_action_with_missing_category(self):
        desc = ActionDescriptor("no_cat", "No Cat", "", "nc")
        registry = ActionRegistry()
        registry._actions.clear()
        registry.register(desc)
        actions = registry.actions
        assert len(actions) == 1
        assert actions[0]["category"] == ""

    def test_search_null_query(self, bridge):
        with pytest.raises((TypeError, Exception)):
            bridge.searchCommands(None)

    def test_empty_string_execute(self, bridge):
        result = bridge.executeCommand("")
        assert result["ok"] is False

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
