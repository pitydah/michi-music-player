"""E2E: Michi AI proposal + execution."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("ai"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestMichiAIProposalE2E:
    def test_michi_ai_bridge_exists(self, bootstrap, bridges):
        ai = bridges.get("michi_ai")
        assert ai is not None, "MichiAIBridge should exist"

    def test_michi_ai_get_suggestions(self, bootstrap, bridges):
        ai = bridges.get("michi_ai")
        assert ai is not None
        result = ai.getSuggestions()
        assert isinstance(result, (list, tuple))

    def test_michi_ai_navigation(self, nav):
        nav.navigate("ai")
        assert nav.currentRoute == "ai", (
            f"Expected 'ai', got '{nav.currentRoute}'"
        )
