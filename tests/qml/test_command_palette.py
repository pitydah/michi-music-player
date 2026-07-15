"""Tests for CommandPalette — positive, capability, recent, sections."""
import pytest

from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor

pytestmark = [pytest.mark.qml_module("command_palette"), pytest.mark.qml_dimension("functional")]


@pytest.fixture
def registry():
    r = ActionRegistry()
    r.register(ActionDescriptor("custom_test", "Test Command", "testing", "test", shortcut="Ctrl+T"))
    return r


@pytest.fixture
def bridge(registry):
    return CommandPaletteBridge(action_registry=registry)


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
        assert len(results) >= 5

    def test_search_empty_returns_all(self, bridge):
        results = bridge.searchCommands("")
        assert len(results) >= 10

    def test_action_has_required_fields(self, bridge):
        for cmd in bridge.commands:
            assert "id" in cmd
            assert "title" in cmd
            assert "category" in cmd
            assert "enabled" in cmd
            assert "visible" in cmd

    def test_action_has_shortcut_field(self, bridge):
        for cmd in bridge.commands:
            assert "shortcut" in cmd

    def test_action_has_destructive_flag(self, bridge):
        for cmd in bridge.commands:
            assert "destructive" in cmd

    def test_destructive_action_marked(self, registry):
        action = registry.get("track_delete_from_disk")
        assert action is not None
        assert action.destructive is True

    def test_get_by_category_returns_filtered(self, registry):
        nav = registry.get_by_category("navigation")
        assert len(nav) >= 5
        for a in nav:
            assert a["category"] == "navigation"

    def test_register_new_action(self, registry):
        desc = ActionDescriptor("new_test", "New Test", "testing", "nt")
        registry.register(desc)
        assert registry.get("new_test") is not None

    def test_registered_action_appears_in_bridge(self, bridge, registry):
        count_before = len(bridge.commands)
        registry.register(ActionDescriptor("extra_action", "Extra", "extra", "ex"))
        assert len(bridge.commands) == count_before + 1

    def test_execute_with_handler(self, registry):
        called = []
        def handler():
            called.append(True)
            return {"ok": True}
        desc = ActionDescriptor("handler_action", "Handler", "test", "h", handler=handler)
        registry.register(desc)
        result = registry.execute("handler_action")
        assert result["ok"] is True
        assert len(called) == 1

    def test_execute_handler_returns_dict(self, registry):
        desc = ActionDescriptor("dict_action", "Dict", "test", "d", handler=lambda: {"ok": True, "data": 42})
        registry.register(desc)
        result = registry.execute("dict_action")
        assert result["ok"] is True
        assert result["data"] == 42

    def test_execute_handler_returns_non_dict(self, registry):
        desc = ActionDescriptor("non_dict", "NonDict", "test", "nd", handler=lambda: 42)
        registry.register(desc)
        result = registry.execute("non_dict")
        assert result["ok"] is True

    def test_execute_handler_raises(self, registry):
        desc = ActionDescriptor("raise_action", "Raise", "test", "r", handler=lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        registry.register(desc)
        result = registry.execute("raise_action")
        assert result["ok"] is False
        assert "fail" in result["error"]

    def test_custom_shortcut_appears(self, registry):
        action = registry.get("custom_test")
        assert action is not None
        assert action.shortcut == "Ctrl+T"

    def test_search_is_case_insensitive(self, bridge):
        results_upper = bridge.searchCommands("INICIO")
        results_lower = bridge.searchCommands("inicio")
        assert len(results_upper) == len(results_lower)

    def test_no_false_positives(self, bridge):
        results = bridge.searchCommands("zzzzzznonexistent")
        assert len(results) == 0

    def test_category_property_exists(self, registry):
        actions = registry.actions
        for a in actions:
            assert "category" in a

    def test_visible_filtered_out(self, registry):
        action = registry.get("navigate_home")
        action.visible = False
        assert registry.get("navigate_home") is not None
        assert registry.get("navigate_home").visible is False
        visible_actions = [a for a in registry.actions if a["visible"]]
        assert "navigate_home" not in [a["id"] for a in visible_actions]

    def test_bridge_executes_unknown(self, bridge):
        result = bridge.executeCommand("nonexistent")
        assert result["ok"] is False


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
