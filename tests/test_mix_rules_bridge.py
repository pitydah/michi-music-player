"""Tests for MixBridge saveRules and previewRules integration."""
import json



class TestMixRulesBridge:
    def test_save_rules_returns_id(self):
        from core.mix_service import MixService
        svc = MixService()
        rules = json.dumps({
            "name": "Test Mix",
            "groups": [{
                "logic": "AND",
                "rules": [{"field": "genre", "operator": "is", "value": "Rock", "logic": "AND"}]
            }],
            "limit": 20, "sort_by": "random", "seed": 42,
        })
        result = svc.save_rules("test_mix", rules)
        assert result["ok"]
        assert "mix_id" in result

    def test_preview_rules_returns_tracks(self):
        from core.mix_service import MixService
        from unittest.mock import MagicMock
        svc = MixService()
        svc._library_query = MagicMock()
        svc._library_query.search.return_value = [
            {"title": "Rock Song", "genre": "Rock", "year": 2020},
            {"title": "Jazz Song", "genre": "Jazz", "year": 2019},
        ]
        svc._rule_engine._lqs = svc._library_query
        rules = json.dumps({
            "groups": [{
                "logic": "AND",
                "rules": [{"field": "genre", "operator": "is", "value": "Rock", "logic": "AND"}]
            }],
        })
        result = svc.preview_rules(rules)
        assert result["ok"]

    def test_preview_rules_invalid_json(self):
        from core.mix_service import MixService
        svc = MixService()
        result = svc.preview_rules("not json")
        assert not result["ok"]

    def test_save_rules_empty(self):
        from core.mix_service import MixService
        svc = MixService()
        result = svc.save_rules("test", json.dumps({"name": "Empty"}))
        assert result["ok"]

    def test_bridge_has_save_rules(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        assert hasattr(MixBridge, 'saveRules')

    def test_bridge_has_preview_rules(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        assert hasattr(MixBridge, 'previewRules')
