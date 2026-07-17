"""Invalid selection handling — core tests, no QML."""
from __future__ import annotations

from ui_qml_bridge.action_registry import ActionRegistry


class TestInvalidSelection:
    def test_action_registry_find_nonexistent(self):
        ar = ActionRegistry()
        result = ar.find("nonexistent_action_id_xyz")
        assert result is None

    def test_action_registry_execute_nonexistent(self):
        ar = ActionRegistry()
        result = ar.execute("nonexistent_action_id_xyz")
        assert result.get("ok") is False
        assert result.get("error") == "NOT_FOUND"

    def test_action_registry_has_actions(self):
        ar = ActionRegistry()
        assert len(list(ar._actions.keys())) > 0
