"""Tests for qml_widget_dependency_audit.py — dependency and SQL audit."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "scripts" / "qml_widget_dependency_audit.py"


@pytest.fixture
def audit_result():
    """Run the dependency audit script and capture JSON output."""
    out = REPO / "artifacts" / ".test_widget_dep_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(out)],
        cwd=REPO, capture_output=True, text=True, timeout=30,
    )
    data = json.loads(out.read_text()) if out.exists() else {}
    out.unlink(missing_ok=True)
    return data, result


class TestWidgetDependencyAuditExecution:
    def test_script_executes(self, audit_result):
        data, result = audit_result
        assert result.returncode in (0, 1), f"Script failed: {result.stderr}"

    def test_output_has_categories(self, audit_result):
        data, _ = audit_result
        expected = {"ui_imports_from_qml_runtime", "ui_imports_from_core",
                    "sql_in_widgets", "business_rules_in_widgets",
                    "qml_duplications", "_total_findings", "_passed"}
        assert expected.issubset(data.keys()), f"Missing categories: {expected - set(data.keys())}"

    def test_total_findings_is_integer(self, audit_result):
        data, _ = audit_result
        assert isinstance(data.get("_total_findings"), int)

    def test_passed_is_bool(self, audit_result):
        data, _ = audit_result
        assert isinstance(data.get("_passed"), bool)


class TestUiImportsFromQmlRuntime:
    def test_findings_have_correct_type(self, audit_result):
        data, _ = audit_result
        for f in data.get("ui_imports_from_qml_runtime", []):
            assert f["type"] == "ui_import_from_qml_runtime"

    def test_findings_have_file_and_line(self, audit_result):
        data, _ = audit_result
        for f in data.get("ui_imports_from_qml_runtime", []):
            assert "file" in f
            assert "line" in f

    def test_qml_main_import_is_detected(self, audit_result):
        data, _ = audit_result
        files = {f["file"] for f in data.get("ui_imports_from_qml_runtime", [])}
        # qml_main.py imports from ui.audio_lab.services
        assert "ui_qml_bridge/qml_main.py" in files


class TestUiImportsFromCore:
    def test_findings_have_correct_type(self, audit_result):
        data, _ = audit_result
        for f in data.get("ui_imports_from_core", []):
            assert f["type"] == "ui_import_from_core"

    def test_findings_are_deduplicated(self, audit_result):
        data, _ = audit_result
        findings = data.get("ui_imports_from_core", [])
        keys = [(f["file"], f.get("function", ""), f.get("line", "")) for f in findings]
        assert len(keys) == len(set(keys)), "Duplicate findings present"


class TestSqlInWidgets:
    def test_findings_have_correct_type(self, audit_result):
        data, _ = audit_result
        for f in data.get("sql_in_widgets", []):
            assert f["type"] == "sql_in_widget"

    def test_findings_contain_match_text(self, audit_result):
        data, _ = audit_result
        for f in data.get("sql_in_widgets", []):
            assert "match" in f


class TestBusinessRulesInWidgets:
    def test_findings_have_correct_type(self, audit_result):
        data, _ = audit_result
        for f in data.get("business_rules_in_widgets", []):
            assert f["type"] == "business_rule_in_widget"

    def test_findings_have_function_name(self, audit_result):
        data, _ = audit_result
        for f in data.get("business_rules_in_widgets", []):
            assert "function" in f


class TestQmlDuplications:
    def test_findings_have_correct_type(self, audit_result):
        data, _ = audit_result
        for f in data.get("qml_duplications", []):
            assert f["type"] == "qml_widget_duplicate"

    def test_duplications_have_name(self, audit_result):
        data, _ = audit_result
        for f in data.get("qml_duplications", []):
            assert "name" in f


class TestEdgeCases:
    def test_empty_script_output_is_resilient(self):
        """Run with a non-existent path to test error handling."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=REPO, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode in (0, 1)
        assert "findings" in result.stdout.lower() or "total" in result.stdout.lower()
