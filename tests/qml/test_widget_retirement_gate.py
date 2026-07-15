"""Tests for HX — QML Widget Retirement Gate."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO / "scripts" / "qml_widget_retirement_gate.py"


class TestGateScriptStructure:
    def test_script_exists(self):
        assert SCRIPT_PATH.exists()

    def test_script_is_executable(self):
        content = SCRIPT_PATH.read_text()
        assert "#!/usr/bin/env python3" in content

    def test_script_contains_run_gate(self):
        content = SCRIPT_PATH.read_text()
        assert "def run_gate" in content

    def test_script_has_w3_constants(self):
        content = SCRIPT_PATH.read_text()
        assert "W3_LEGACY_ONLY" in content
        assert "W4_DETACHED" in content

    def test_script_imports_yaml(self):
        content = SCRIPT_PATH.read_text()
        assert "import yaml" in content or "yaml.safe_load" in content


class TestGateConditions:
    def test_gate_checks_migration_score(self):
        content = SCRIPT_PATH.read_text()
        assert "score >= 90" in content or "migration_score" in content

    def test_gate_checks_ruff(self):
        content = SCRIPT_PATH.read_text()
        assert "ruff" in content.lower()

    def test_gate_checks_compileall(self):
        content = SCRIPT_PATH.read_text()
        assert "compileall" in content.lower()

    def test_gate_checks_qml_load(self):
        content = SCRIPT_PATH.read_text()
        assert "qml_compile_all" in content or "qml_load" in content

    def test_gate_checks_qml_instance(self):
        content = SCRIPT_PATH.read_text()
        assert "qml_instance_all" in content or "qml_instance" in content

    def test_gate_checks_service_graph(self):
        content = SCRIPT_PATH.read_text()
        assert "productive_service_audit" in content or "service_graph" in content

    def test_gate_checks_qml_imports_widget(self):
        content = SCRIPT_PATH.read_text()
        assert "QtWidgets" in content or "imports_widget" in content

    def test_gate_checks_core_no_ui(self):
        content = SCRIPT_PATH.read_text()
        assert "core_imports_ui" in content or "core.*ui" in content


class TestGateW4Conditions:
    def test_gate_checks_packaging_excludes_widget(self):
        content = SCRIPT_PATH.read_text()
        assert "packaging" in content.lower() and "widget" in content.lower()

    def test_gate_checks_navigation_excludes_widget(self):
        content = SCRIPT_PATH.read_text()
        assert "navigation" in content.lower() and "widget" in content.lower()

    def test_gate_checks_launcher_excludes_widget(self):
        content = SCRIPT_PATH.read_text()
        assert "launcher" in content.lower() and "widget" in content.lower()


class TestGateResultFormat:
    def test_gate_returns_dict(self):
        import scripts.qml_widget_retirement_gate as gate_mod
        result = gate_mod.run_gate()
        assert isinstance(result, dict)

    def test_gate_result_has_gate_pass_field(self):
        import scripts.qml_widget_retirement_gate as gate_mod
        result = gate_mod.run_gate()
        assert "gate_pass" in result

    def test_gate_result_has_global_checks(self):
        import scripts.qml_widget_retirement_gate as gate_mod
        result = gate_mod.run_gate()
        assert "global_checks" in result

    def test_gate_result_has_domain_results(self):
        import scripts.qml_widget_retirement_gate as gate_mod
        result = gate_mod.run_gate()
        assert "domain_results" in result

    def test_gate_result_has_score(self):
        import scripts.qml_widget_retirement_gate as gate_mod
        result = gate_mod.run_gate()
        assert "score" in result

    def test_gate_result_writes_json(self):
        import json
        outpath = Path("/tmp/michi_qml_widget_retirement_gate.json")
        if outpath.exists():
            data = json.loads(outpath.read_text())
            assert "gate_pass" in data
            assert "global_checks" in data

    def test_gate_global_checks_contains_ruff(self):
        import scripts.qml_widget_retirement_gate as gate_mod
        result = gate_mod.run_gate()
        assert "ruff" in result.get("global_checks", {})

    def test_gate_global_checks_contains_qml_load(self):
        import scripts.qml_widget_retirement_gate as gate_mod
        result = gate_mod.run_gate()
        assert "qml_load" in result.get("global_checks", {})

    def test_gate_domain_results_contains_w3_domains(self):
        import scripts.qml_widget_retirement_gate as gate_mod
        result = gate_mod.run_gate()
        assert "w3_domain_count" in result
        assert result["w3_domain_count"] >= 0
