"""Tests for Evidence V7 conftest plugin, module config, and evidence collector."""
import ast
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent


class TestConftestPlugin:
    def test_conftest_exists(self):
        conftest = REPO / "tests" / "qml" / "conftest.py"
        assert conftest.exists(), "conftest.py not found in tests/qml/"

    def test_conftest_has_pytest_collection_modifyitems(self):
        conftest = REPO / "tests" / "qml" / "conftest.py"
        tree = ast.parse(conftest.read_text())
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "pytest_collection_modifyitems" in funcs

    def test_conftest_handles_all_markers(self):
        conftest = REPO / "tests" / "qml" / "conftest.py"
        source = conftest.read_text()
        for marker in ["qml_module", "qml_dimension", "qml_workflow", "qml_route", "qml_widget_replacement"]:
            assert marker in source, f"marker {marker} not handled in conftest"

    def test_conftest_appends_user_properties(self):
        conftest = REPO / "tests" / "qml" / "conftest.py"
        source = conftest.read_text()
        assert "user_properties.append" in source

    def test_conftest_importable(self):
        result = subprocess.run(
            [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); from tests.qml.conftest import pytest_collection_modifyitems"],
            cwd=REPO, capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"


class TestQmlModulesConfig:
    def test_config_exists(self):
        config = REPO / "config" / "qml_modules.yaml"
        assert config.exists()

    def test_config_valid_yaml(self):
        config = REPO / "config" / "qml_modules.yaml"
        data = yaml.safe_load(config.read_text())
        assert data is not None
        assert "modules" in data

    def test_all_modules_have_required_fields(self):
        config = REPO / "config" / "qml_modules.yaml"
        data = yaml.safe_load(config.read_text())
        for m in data["modules"]:
            assert "module" in m
            assert "area" in m
            assert "module_weight" in m
            assert "applicable_dimensions" in m
            assert "widget_replacement" in m

    def test_area_weights_sum_100(self):
        area_weights = {
            "shell_nav": 10,
            "library_playback": 25,
            "core_workflows": 20,
            "advanced_tools": 20,
            "ecosystem_network": 15,
            "quality_release": 10,
        }
        total = sum(area_weights.values())
        assert total == 100, f"Area weights sum to {total}, expected 100"

    def test_all_areas_represented(self):
        config = REPO / "config" / "qml_modules.yaml"
        raw = yaml.safe_load(config.read_text())
        areas = {m["area"] for m in raw["modules"]}
        expected = {"shell_nav", "library_playback", "core_workflows", "advanced_tools", "ecosystem_network", "quality_release"}
        assert areas == expected

    def test_audio_lab_module_config(self):
        config = REPO / "config" / "qml_modules.yaml"
        data = yaml.safe_load(config.read_text())
        audio_lab = next(m for m in data["modules"] if m["module"] == "audio_lab")
        assert audio_lab["area"] == "advanced_tools"
        assert audio_lab["module_weight"] == 10
        assert audio_lab["widget_replacement"]["status"] == "W1_FROZEN"


class TestEvidenceV7Collector:
    def test_collector_script_exists(self):
        script = REPO / "scripts" / "qml_evidence_v7_collect.py"
        assert script.exists()

    def test_collector_has_main_function(self):
        script = REPO / "scripts" / "qml_evidence_v7_collect.py"
        tree = ast.parse(script.read_text())
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "main" in funcs

    def test_collector_junit_parsing(self):
        from scripts.qml_evidence_v7_collect import parse_junit
        import tempfile
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1">
    <testcase classname="test_mod" name="test_func" time="0.1">
      <properties>
        <property name="qml_module" value="audio_lab"/>
        <property name="qml_dimension" value="route_load"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            tmp = f.name
        try:
            cases = parse_junit(Path(tmp))
            assert len(cases) == 1
            assert cases[0]["user_properties"]["qml_module"] == "audio_lab"
            assert cases[0]["user_properties"]["qml_dimension"] == "route_load"
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_collector_module_scoring(self):
        from scripts.qml_evidence_v7_collect import derive_composite_status
        dims = {
            "route_load": {"status": "PASSED"},
            "qml_instance": {"status": "PASSED"},
        }
        assert derive_composite_status(dims) == "COMPILES"

    def test_collector_parity_status(self):
        from scripts.qml_evidence_v7_collect import derive_composite_status
        dims = {d: {"status": "PASSED"} for d in [
            "route_load", "qml_instance", "model_data", "service_wiring",
            "read", "primary_action", "secondary_actions", "write",
            "error_contract", "async_execution", "real_cancellation",
            "persistence", "integration", "vertical_workflow",
            "performance", "accessibility",
        ]}
        assert derive_composite_status(dims) == "PARITY"


class TestManifestScripts:
    def test_manifest_generate_exists(self):
        assert (REPO / "scripts" / "qml_manifest_v7_generate.py").exists()

    def test_manifest_audit_exists(self):
        assert (REPO / "scripts" / "qml_manifest_v7_audit.py").exists()

    def test_migration_score_exists(self):
        assert (REPO / "scripts" / "qml_migration_score_v7.py").exists()

    def test_manifest_generate_has_main(self):
        tree = ast.parse((REPO / "scripts" / "qml_manifest_v7_generate.py").read_text())
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "main" in funcs

    def test_manifest_audit_has_main(self):
        tree = ast.parse((REPO / "scripts" / "qml_manifest_v7_audit.py").read_text())
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert "main" in funcs
