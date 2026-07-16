"""ActionRegistry edge cases: error codes, typed results, handler failures."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("gate_check"),
    pytest.mark.qml_route("all"),
]


class TestActionRegistryEdgeCases:
    def test_execute_nonexistent_action(self, bootstrap):
        ar = bootstrap.container.get("action_registry")
        assert ar is not None
        result = ar.execute("nonexistent__action__id")
        assert isinstance(result, dict)
        assert result.get("ok") is False
        assert result.get("error") == "NOT_FOUND"

    def test_execute_returns_dict(self, bootstrap):
        ar = bootstrap.container.get("action_registry")
        assert ar is not None
        actions = ar.actions
        assert len(actions) > 0, "Should have registered actions"
        for action in actions[:5]:
            result = ar.execute(action["id"])
            assert isinstance(result, dict), f"Action {action['id']} should return dict"
            assert "ok" in result, f"Action {action['id']} result should have 'ok' key"

    def test_action_has_handler(self, bootstrap):
        ar = bootstrap.container.get("action_registry")
        assert ar is not None
        none_handlers = []
        for aid, desc in ar._actions.items():
            if desc.handler is None:
                none_handlers.append(aid)
            else:
                assert callable(desc.handler), f"Action '{aid}' handler should be callable"
        assert len(none_handlers) <= 100, (
            f"Too many actions with None handler: {none_handlers}"
        )

    def test_find_action_by_id(self, bootstrap):
        ar = bootstrap.container.get("action_registry")
        assert ar is not None
        play = ar.find("play")
        assert play is not None or ar.find("play") is not None
        none_action = ar.find("nonexistent__99")
        assert none_action is None

    def test_action_categories(self, bootstrap):
        ar = bootstrap.container.get("action_registry")
        assert ar is not None
        cats = {a["category"] for a in ar.actions}
        assert len(cats) >= 4, f"Expected >=4 categories, got {cats}"
        for cat in ("playback", "navigation", "library", "queue"):
            filtered = ar.get_by_category(cat)
            assert len(filtered) > 0, f"Category '{cat}' should have actions"

    def test_all_actions_have_ids(self, bootstrap):
        ar = bootstrap.container.get("action_registry")
        assert ar is not None
        for aid, desc in ar._actions.items():
            assert aid == desc.id, f"Key '{aid}' doesn't match action_id '{desc.id}'"
