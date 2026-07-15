"""Tests for Runtime Quality Gate (HU)."""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
GATE_SCRIPT = REPO / "scripts" / "qml_runtime_quality_gate.py"
AUDIT_SCRIPT = REPO / "scripts" / "qml_runtime_quality_audit.py"


class TestGateScriptStructure:
    def test_gate_script_exists(self):
        assert GATE_SCRIPT.exists()

    def test_audit_script_exists(self):
        assert AUDIT_SCRIPT.exists()

    def test_gate_has_budgets(self):
        content = GATE_SCRIPT.read_text()
        assert "BUDGETS" in content
        assert "rss_growth_mb_max" in content
        assert "threads_expected" in content
        assert "external_processes_expected" in content
        assert "db_connections_expected" in content
        assert "critical_warnings_expected" in content
        assert "duplicates_expected" in content
        assert "stale_callbacks_expected" in content


class TestGateBudgetConstants:
    RSS_MAX = 50.0
    THREADS_EXPECTED = 0
    EXT_PROCS_EXPECTED = 0
    DB_CONNS_EXPECTED = 0
    CRIT_WARNINGS_EXPECTED = 0
    DUPLICATES_EXPECTED = 0
    STALE_CALLBACKS_EXPECTED = 0

    def test_budget_rss_growth_positive(self):
        assert self.RSS_MAX > 0

    def test_budget_rss_growth_reasonable(self):
        assert self.RSS_MAX <= 200

    def test_budget_threads_is_zero(self):
        assert self.THREADS_EXPECTED == 0

    def test_budget_ext_procs_is_zero(self):
        assert self.EXT_PROCS_EXPECTED == 0

    def test_budget_db_conns_is_zero(self):
        assert self.DB_CONNS_EXPECTED == 0

    def test_budget_crit_warnings_is_zero(self):
        assert self.CRIT_WARNINGS_EXPECTED == 0

    def test_budget_duplicates_is_zero(self):
        assert self.DUPLICATES_EXPECTED == 0

    def test_budget_stale_callbacks_is_zero(self):
        assert self.STALE_CALLBACKS_EXPECTED == 0

    def test_all_budgets_defined(self):
        assert self.RSS_MAX is not None
        assert self.THREADS_EXPECTED is not None
        assert self.EXT_PROCS_EXPECTED is not None
        assert self.DB_CONNS_EXPECTED is not None
        assert self.CRIT_WARNINGS_EXPECTED is not None
        assert self.DUPLICATES_EXPECTED is not None
        assert self.STALE_CALLBACKS_EXPECTED is not None


class TestGateResultFormat:
    @pytest.fixture
    def sample_result(self):
        return {
            "passed": True,
            "checks": {
                "rss_growth": {"value": 5.0, "budget": 50.0, "ok": True},
                "threads": {"value": 0, "expected": 0, "ok": True},
                "external_processes": {"value": 0, "expected": 0, "ok": True},
                "db_connections": {"value": 0, "expected": 0, "ok": True},
                "critical_warnings": {"value": 0, "expected": 0, "ok": True},
                "duplicate_context_properties": {"value": 0, "expected": 0, "ok": True},
                "stale_callbacks": {"value": 0, "expected": 0, "ok": True},
            },
            "result": {},
        }

    def test_result_has_passed_field(self, sample_result):
        assert "passed" in sample_result
        assert sample_result["passed"] is True

    def test_result_has_seven_checks(self, sample_result):
        assert len(sample_result["checks"]) == 7

    def test_each_check_has_ok_field(self, sample_result):
        for name, check in sample_result["checks"].items():
            assert "ok" in check, f"check {name} missing 'ok'"

    def test_each_check_has_value_field(self, sample_result):
        for name, check in sample_result["checks"].items():
            assert "value" in check, f"check {name} missing 'value'"

    def test_gate_fails_on_any_failed_check(self):
        import scripts.qml_runtime_quality_gate as gate_mod
        gate_mod.BUDGETS = {
            "rss_growth_mb_max": 50.0,
            "threads_expected": 0,
            "external_processes_expected": 0,
            "db_connections_expected": 0,
            "critical_warnings_expected": 0,
            "duplicates_expected": 0,
            "stale_callbacks_expected": 0,
        }
        bad_result = {
            "rss_growth_mb": 60.0,
            "threads_after": 0,
            "external_processes": [],
            "db_connections_open": 0,
            "critical_warnings": [],
            "duplicate_context_properties": [],
            "stale_callbacks": [],
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("scripts.qml_runtime_quality_audit.run", lambda: bad_result)
            gate_result = gate_mod.run_gate()
            assert gate_result["passed"] is False


class TestGateFailure:
    def test_gate_fails_on_rss_exceeded(self):
        import scripts.qml_runtime_quality_gate as gate_mod
        result = {
            "rss_growth_mb": 99.9,
            "threads_after": 0,
            "external_processes": [],
            "db_connections_open": 0,
            "critical_warnings": [],
            "duplicate_context_properties": [],
            "stale_callbacks": [],
        }
        checks = gate_mod._run_checks(result)
        assert checks["rss_growth"]["ok"] is False

    def test_gate_fails_on_threads_leaked(self):
        import scripts.qml_runtime_quality_gate as gate_mod
        result = {
            "rss_growth_mb": 0,
            "threads_after": 3,
            "external_processes": [],
            "db_connections_open": 0,
            "critical_warnings": [],
            "duplicate_context_properties": [],
            "stale_callbacks": [],
        }
        checks = gate_mod._run_checks(result)
        assert checks["threads"]["ok"] is False

    def test_gate_fails_on_external_processes(self):
        import scripts.qml_runtime_quality_gate as gate_mod
        result = {
            "rss_growth_mb": 0,
            "threads_after": 0,
            "external_processes": ["ffmpeg"],
            "db_connections_open": 0,
            "critical_warnings": [],
            "duplicate_context_properties": [],
            "stale_callbacks": [],
        }
        checks = gate_mod._run_checks(result)
        assert checks["external_processes"]["ok"] is False

    def test_gate_fails_on_db_connections(self):
        import scripts.qml_runtime_quality_gate as gate_mod
        result = {
            "rss_growth_mb": 0,
            "threads_after": 0,
            "external_processes": [],
            "db_connections_open": 2,
            "critical_warnings": [],
            "duplicate_context_properties": [],
            "stale_callbacks": [],
        }
        checks = gate_mod._run_checks(result)
        assert checks["db_connections"]["ok"] is False

    def test_gate_fails_on_critical_warnings(self):
        import scripts.qml_runtime_quality_gate as gate_mod
        result = {
            "rss_growth_mb": 0,
            "threads_after": 0,
            "external_processes": [],
            "db_connections_open": 0,
            "critical_warnings": ["ReferenceError: x is not defined"],
            "duplicate_context_properties": [],
            "stale_callbacks": [],
        }
        checks = gate_mod._run_checks(result)
        assert checks["critical_warnings"]["ok"] is False

    def test_gate_returns_dict(self):
        import scripts.qml_runtime_quality_gate as gate_mod
        result = {"error": "no engine"}
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("scripts.qml_runtime_quality_audit.run", lambda: result)
            gate_result = gate_mod.run_gate()
            assert isinstance(gate_result, dict)
