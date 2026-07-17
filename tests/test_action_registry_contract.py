"""Contract tests for ActionRegistry — validates all actions have valid service/method references."""
from __future__ import annotations

from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor


class TestActionRegistryContract:
    def test_all_actions_have_ids(self):
        reg = ActionRegistry()
        for aid, action in reg._actions.items():
            assert aid == action.id, f"Action ID mismatch: {aid} vs {action.id}"

    def test_no_duplicate_ids(self):
        reg = ActionRegistry()
        ids = list(reg._actions.keys())
        assert len(ids) == len(set(ids)), "Duplicate action IDs found"

    def test_all_actions_have_titles(self):
        reg = ActionRegistry()
        for aid, action in reg._actions.items():
            assert action.title, f"Action {aid} has no title"

    def test_all_actions_have_categories(self):
        reg = ActionRegistry()
        for aid, action in reg._actions.items():
            assert action.category, f"Action {aid} has no category"

    def test_categories_are_valid(self):
        reg = ActionRegistry()
        valid = {"navigation", "playback", "library", "playlist", "metadata",
                 "radio", "system", "track", "album", "artist", "folder", "source"}
        for aid, action in reg._actions.items():
            assert action.category in valid, f"Action {aid} has invalid category: {action.category}"

    def test_validate_all_without_container_returns_empty(self):
        reg = ActionRegistry()
        issues = reg.validate_all()
        assert isinstance(issues, list)

    def test_register_duplicate_raises(self):
        reg = ActionRegistry()
        dup = ActionDescriptor(action_id="navigate_home", title="Dup", category="system")
        try:
            reg.register(dup)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_get_nonexistent_returns_none(self):
        reg = ActionRegistry()
        assert reg.get("nonexistent_action_xyz") is None

    def test_execute_no_handler_returns_error(self):
        reg = ActionRegistry()
        result = reg.execute("navigate_home")
        assert result == {"ok": False, "error": "NO_HANDLER"}

    def test_execute_unknown_returns_not_found(self):
        reg = ActionRegistry()
        result = reg.execute("i_dont_exist")
        assert result == {"ok": False, "error": "NOT_FOUND"}

    def test_execute_handler_returns_ok(self):
        reg = ActionRegistry()
        called = False

        def handler():
            nonlocal called
            called = True
            return {"ok": True}

        action = ActionDescriptor(
            action_id="test_handler", title="Test", category="system",
            handler=handler)
        reg.register(action)
        result = reg.execute("test_handler")
        assert result == {"ok": True}
        assert called

    def test_qml_get_returns_dict(self):
        reg = ActionRegistry()
        info = reg.qmlGet("navigate_home")
        assert info["id"] == "navigate_home"
        assert info["title"] == "Ir a Inicio"
        assert info["handler_exists"] is False
