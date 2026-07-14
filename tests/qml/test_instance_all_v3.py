"""DI — Instance audit V3: LOAD_PASS, INSTANCE_PASS, INTERACTION_PASS, CLEANUP_PASS."""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

SCRIPTS = REPO / "scripts"
QML_DIR = REPO / "ui_qml"


@pytest.fixture(scope="module")
def v3_results():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "qml_instance_all_v3", SCRIPTS / "qml_instance_all_v3.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run()


class TestInstanceAllV3Summary:
    def test_all_qml_files_accounted(self, v3_results):
        qml_files = sorted(QML_DIR.rglob("*.qml"))
        assert v3_results["summary"]["total"] == len(qml_files)

    def test_total_greater_than_zero(self, v3_results):
        assert v3_results["summary"]["total"] > 0

    def test_loaded_count_matches_total(self, v3_results):
        s = v3_results["summary"]
        assert s["loaded"] == s["total"], (
            f"LOAD_PASS: {s['loaded']}/{s['total']}"
        )

    def test_instanced_count_matches_total(self, v3_results):
        s = v3_results["summary"]
        assert s["instanced"] == s["total"], (
            f"INSTANCE_PASS: {s['instanced']}/{s['total']}"
        )

    def test_interaction_passed_mostly(self, v3_results):
        s = v3_results["summary"]
        assert s["interaction_passed"] > 0

    def test_cleanup_passed_mostly(self, v3_results):
        s = v3_results["summary"]
        assert s["cleanup_passed"] > 0

    def test_no_reference_errors(self, v3_results):
        assert not v3_results["summary"]["has_reference_errors"]

    def test_no_type_errors(self, v3_results):
        assert not v3_results["summary"]["has_type_errors"]

    def test_binding_loops_reported(self, v3_results):
        assert isinstance(v3_results["summary"]["binding_loops"], int)

    def test_error_count_zero(self, v3_results):
        assert v3_results["summary"]["error_count"] == 0

    def test_warning_count_is_int(self, v3_results):
        assert isinstance(v3_results["summary"]["warning_count"], int)

    def test_component_results_length(self, v3_results):
        assert len(v3_results["component_results"]) > 0

    def test_each_component_has_all_states(self, v3_results):
        for cr in v3_results["component_results"]:
            assert "load" in cr
            assert "instance" in cr
            assert "interaction" in cr
            assert "cleanup" in cr


class TestInstanceAllV3States:
    def test_loaded_passed_files_are_ready(self, v3_results):
        for cr in v3_results["component_results"]:
            assert cr["load"] == "PASS"

    def test_instanced_files_are_created(self, v3_results):
        for cr in v3_results["component_results"]:
            assert cr["instance"] == "PASS"

    def test_interaction_is_pass_or_na(self, v3_results):
        valid = {"PASS", "N/A"}
        for cr in v3_results["component_results"]:
            assert cr["interaction"] in valid

    def test_cleanup_is_pass_or_na(self, v3_results):
        valid = {"PASS", "N/A"}
        for cr in v3_results["component_results"]:
            assert cr["cleanup"] in valid

    def test_no_fail_status_in_results(self, v3_results):
        fails = [cr for cr in v3_results["component_results"]
                 if cr["load"] == "FAIL"]
        assert len(fails) == 0

    def test_all_have_warnings_list(self, v3_results):
        for cr in v3_results["component_results"]:
            assert isinstance(cr["warnings"], list)


class TestInstanceAllV3Report:
    def test_has_summary_dict(self, v3_results):
        assert isinstance(v3_results["summary"], dict)

    def test_has_errors_list(self, v3_results):
        assert isinstance(v3_results["errors"], list)

    def test_has_warnings_list(self, v3_results):
        assert isinstance(v3_results["warnings"], list)

    def test_has_component_results(self, v3_results):
        assert isinstance(v3_results["component_results"], list)

    def test_summary_total_is_int(self, v3_results):
        assert isinstance(v3_results["summary"]["total"], int)

    def test_summary_loaded_is_int(self, v3_results):
        assert isinstance(v3_results["summary"]["loaded"], int)
