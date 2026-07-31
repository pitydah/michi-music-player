from __future__ import annotations

"""Fase 11.2 — every mix category must explain itself.

Each block shown in the Mix hub carries: what it contains (desc),
why it exists (reason), when it updates (updated), who generated it
(origin), and its primary action (action).
"""

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.mix_bridge import MIX_CATEGORIES, MixBridge

pytestmark = pytest.mark.isolation

REQUIRED_KEYS = ("id", "title", "desc", "reason", "origin", "updated", "action")


class TestMixCategoryExplanation:
    def test_all_categories_have_explanation_fields(self):
        for cat in MIX_CATEGORIES:
            for key in REQUIRED_KEYS:
                assert cat.get(key), f"Category '{cat.get('id')}' missing '{key}'"

    def test_origin_is_known(self):
        for cat in MIX_CATEGORIES:
            assert cat["origin"] in ("Michi", "Tú"), (
                f"Category '{cat['id']}' has unknown origin '{cat['origin']}'"
            )

    def test_bridge_exposes_explanations(self):
        bridge = MixBridge(playback_service=MagicMock())
        cats = bridge.categories
        assert len(cats) == len(MIX_CATEGORIES)
        for cat in cats:
            assert cat["reason"]
            assert cat["updated"]
            assert cat["action"]

    def test_custom_mix_is_user_generated(self):
        custom = next(c for c in MIX_CATEGORIES if c["id"] == "custom")
        assert custom["origin"] == "Tú"

    def test_automatic_mixes_are_michi_generated(self):
        for auto_id in ("favorites", "recent", "most_played", "unplayed",
                        "rediscovery", "daily_mix", "high_quality"):
            cat = next(c for c in MIX_CATEGORIES if c["id"] == auto_id)
            assert cat["origin"] == "Michi", f"'{auto_id}' should be Michi-generated"
