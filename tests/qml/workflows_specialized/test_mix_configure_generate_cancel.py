from __future__ import annotations
"""MW: Mix — configure mix category, generate mix, cancel generation."""

from unittest.mock import MagicMock

from .specialized_workflow_harness import SpecializedWorkflowBase


class TestMixConfigureGenerateCancel(SpecializedWorkflowBase):
    def test_list_categories(self, mix_fixtures):
        b = mix_fixtures
        assert len(b.categories) >= 1

    def test_select_category(self, mix_fixtures):
        b = mix_fixtures
        cat = b.categories[0]
        assert cat.get("id") == "favorites"

    def test_generate_mix(self, mix_fixtures):
        b = mix_fixtures
        result = b.loadMix("favorites")
        self.assert_ok(result)

    def test_cancel_generation(self, mix_fixtures):
        b = mix_fixtures
        result = b.cancelGeneration()
        self.assert_ok(result)

    def test_full_workflow(self, mix_fixtures):
        b = mix_fixtures
        b.loadMix("favorites")
        b.loadMix("recent")
        b.cancelGeneration()
        assert b.loadMix.call_count >= 2
        assert b.cancelGeneration.called

    def test_empty_categories(self):
        b = MagicMock()
        b.categories = []
        assert len(b.categories) == 0

    def test_generation_error(self, mix_fixtures):
        b = mix_fixtures
        b.loadMix = MagicMock(return_value={"ok": False, "error": "EMPTY_MIX"})
        result = b.loadMix("nonexistent")
        self.assert_error(result, "EMPTY_MIX")
