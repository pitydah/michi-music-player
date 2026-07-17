"""Integration tests for ActionRegistry."""
import pytest
from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor


def test_register_valid_action():
    registry = ActionRegistry()
    action = ActionDescriptor(
        action_id="test_action",
        title="Test",
        category="test",
        handler=lambda: {"ok": True},
    )
    registry.register(action)
    assert registry.get("test_action") is not None


def test_duplicate_id_raises():
    registry = ActionRegistry()
    action1 = ActionDescriptor(action_id="dup", title="A", category="t", handler=lambda: {})
    action2 = ActionDescriptor(action_id="dup", title="B", category="t", handler=lambda: {})
    registry.register(action1)
    with pytest.raises(ValueError, match="Duplicate action ID"):
        registry.register(action2)


def test_validate_all_clean():
    registry = ActionRegistry()
    action = ActionDescriptor(action_id="ok", title="OK", category="t", handler=lambda: {"ok": True})
    registry.register(action)
    issues = registry.validate_all()
    ok_issues = [i for i in issues if i["action_id"] == "ok"]
    assert len(ok_issues) == 0
