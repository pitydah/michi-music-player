"""Tests for normalized V9 score (HR).

Verifies:
- Score por módulo = peso_aprobado / peso_aplicable * 100
- Global = sum(score × weight) / sum(weight)
- Siempre 0-100
- NO premia: test count, archivo presente, class presente, helper marcado
"""
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "scripts"


def _load_score_mod():
    spec = importlib.util.spec_from_file_location("qml_migration_score_v9", SCRIPTS / "qml_migration_score_v9.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


score_mod = _load_score_mod()
SCORE_MAP = score_mod.SCORE_MAP


class TestNormalizedScoreFormula:
    def test_module_all_passed(self):
        mod = {"markers": {"a": {"weight": 10, "status": "PASSED"}, "b": {"weight": 5, "status": "PASSED"}}}
        s, aw, ap = score_mod.module_normalized_score(mod)
        assert s == 100.0
        assert aw == 15
        assert ap == 15

    def test_module_half_failed(self):
        mod = {"markers": {"a": {"weight": 10, "status": "PASSED"}, "b": {"weight": 10, "status": "FAILED"}}}
        s, aw, ap = score_mod.module_normalized_score(mod)
        assert s == 50.0
        assert aw == 10
        assert ap == 20

    def test_module_not_applicable_excluded(self):
        mod = {"markers": {
            "a": {"weight": 10, "status": "PASSED"},
            "b": {"weight": 10, "status": "NOT_APPLICABLE_DECLARED"},
        }}
        s, aw, ap = score_mod.module_normalized_score(mod)
        assert s == 100.0
        assert aw == 10.0
        assert ap == 10.0

    def test_module_all_not_applicable(self):
        mod = {"markers": {"a": {"weight": 10, "status": "NOT_APPLICABLE_DECLARED"}}}
        s, aw, ap = score_mod.module_normalized_score(mod)
        assert s == 100.0

    def test_module_all_failed(self):
        mod = {"markers": {"a": {"weight": 10, "status": "FAILED"}, "b": {"weight": 5, "status": "MISSING"}}}
        s, aw, ap = score_mod.module_normalized_score(mod)
        assert s == 0.0
        assert aw == 0
        assert ap == 15

    def test_module_no_markers(self):
        mod = {"markers": {}}
        s, aw, ap = score_mod.module_normalized_score(mod)
        assert s == 100.0
        assert aw == 0.0
        assert ap == 0.0


class TestGlobalScore:
    def test_global_perfect(self):
        modules = [
            {"module": "A", "weight": 10, "markers": {"x": {"weight": 10, "status": "PASSED"}}},
            {"module": "B", "weight": 20, "markers": {"y": {"weight": 10, "status": "PASSED"}}},
        ]
        scores = [score_mod.module_normalized_score(m)[0] for m in modules]
        weights = [m["weight"] for m in modules]
        global_s = sum(s * w / 100.0 for s, w in zip(scores, weights, strict=True))
        total_w = sum(weights)
        result = (global_s / total_w * 100) if total_w > 0 else 0.0
        assert result == 100.0

    def test_global_mixed(self):
        modules = [
            {"module": "A", "weight": 10, "markers": {"x": {"weight": 10, "status": "PASSED"}}},
            {"module": "B", "weight": 10, "markers": {"y": {"weight": 10, "status": "FAILED"}}},
        ]
        scores = [score_mod.module_normalized_score(m)[0] for m in modules]
        weights = [m["weight"] for m in modules]
        global_s = sum(s * w / 100.0 for s, w in zip(scores, weights, strict=True))
        total_w = sum(weights)
        result = round(global_s / total_w * 100, 1) if total_w > 0 else 0.0
        assert result == 50.0

    def test_global_always_0_to_100(self):
        modules = [
            {"module": "A", "weight": 25, "markers": {"x": {"weight": 10, "status": "PASSED"}, "y": {"weight": 5, "status": "FAILED"}}},
            {"module": "B", "weight": 15, "markers": {"z": {"weight": 8, "status": "NOT_APPLICABLE_DECLARED"}}},
        ]
        scores = [score_mod.module_normalized_score(m)[0] for m in modules]
        weights = [m["weight"] for m in modules]
        global_s = sum(s * w / 100.0 for s, w in zip(scores, weights, strict=True))
        total_w = sum(weights)
        result = round(global_s / total_w * 100, 1) if total_w > 0 else 0.0
        assert 0 <= result <= 100


class TestNoWrongPremiums:
    def test_no_premium_for_test_count(self):
        mod1 = {"markers": {"a": {"weight": 10, "status": "PASSED"}}}
        mod2 = {"markers": {"a": {"weight": 10, "status": "PASSED"}, "b": {"weight": 5, "status": "PASSED"}}}
        s1, _, _ = score_mod.module_normalized_score(mod1)
        s2, _, _ = score_mod.module_normalized_score(mod2)
        assert s1 == s2 == 100.0

    def test_no_premium_for_archivo_presente(self):
        mod = {"markers": {"a": {"weight": 10, "status": "FAILED"}}}
        s, _, _ = score_mod.module_normalized_score(mod)
        assert s == 0.0

    def test_no_premium_for_class_presente(self):
        mod = {"markers": {"a": {"weight": 10, "status": "PASSED"}, "b": {"weight": 10, "status": "MISSING"}}}
        s, _, _ = score_mod.module_normalized_score(mod)
        assert s == 50.0

    def test_no_premium_for_helper_marcado(self):
        mod = {"markers": {"a": {"weight": 10, "status": "PASSED", "helper": True}}}
        s, _, _ = score_mod.module_normalized_score(mod)
        assert s == 100.0


class TestScoreMapValues:
    def test_passed(self):
        assert SCORE_MAP["PASSED"] == 1.0

    def test_failed(self):
        assert SCORE_MAP["FAILED"] == 0.0

    def test_missing(self):
        assert SCORE_MAP["MISSING"] == 0.0

    def test_not_applicable(self):
        assert SCORE_MAP["NOT_APPLICABLE_DECLARED"] == 1.0

    def test_deferred_physical(self):
        assert SCORE_MAP["DEFERRED_PHYSICAL"] == 1.0


class TestRealManifest:
    def test_manifest_exists(self):
        mf = REPO / "docs" / "qml_migration_manifest_v9.json"
        assert mf.exists()

    def test_manifest_scores_0_100(self):
        mf = REPO / "docs" / "qml_migration_manifest_v9.json"
        if not mf.exists():
            pytest.skip("manifest not generated")
        data = json.loads(mf.read_text())
        for mod in data.get("modules", []):
            s, _, _ = score_mod.module_normalized_score(mod)
            assert 0 <= s <= 100, f"{mod['module']} score {s}"

    def test_manifest_global_0_100(self):
        mf = REPO / "docs" / "qml_migration_manifest_v9.json"
        if not mf.exists():
            pytest.skip("manifest not generated")
        data = json.loads(mf.read_text())
        gs = data.get("global_score", -1)
        assert 0 <= gs <= 100
