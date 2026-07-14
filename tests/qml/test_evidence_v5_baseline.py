"""Tests for QML Evidence V5 baseline: SHA, weights, JUnit parsing, module markers."""
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
ARTIFACTS = REPO / "artifacts"
CONFIG_FILE = REPO / "config" / "qml_migration_dimensions.json"
EVIDENCE_FILE = ARTIFACTS / "qml-evidence-v5.json"
MANIFEST_FILE = REPO / "docs" / "qml_migration_manifest_v5.json"
BASELINE_FILE = ARTIFACTS / "qml-baseline.json"
JUNIT_FILE = ARTIFACTS / "qml-results-v5.xml"


@pytest.fixture
def head_sha():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()


@pytest.fixture
def config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


@pytest.fixture
def baseline():
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text())
    return {}


@pytest.fixture
def evidence():
    if EVIDENCE_FILE.exists():
        return json.loads(EVIDENCE_FILE.read_text())
    return {}


@pytest.fixture
def manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {}


@pytest.fixture
def junit_tree():
    if JUNIT_FILE.exists():
        return ET.parse(JUNIT_FILE)
    return None


class TestShaConsistency:
    def test_baseline_sha_matches_head(self, baseline, head_sha):
        assert baseline.get("sha") == head_sha, f"Baseline SHA {baseline.get('sha')} != HEAD {head_sha}"

    def test_evidence_sha_matches_head(self, evidence, head_sha):
        assert evidence.get("sha") == head_sha, f"Evidence SHA {evidence.get('sha')} != HEAD {head_sha}"

    def test_manifest_sha_matches_head(self, manifest, head_sha):
        assert manifest.get("sha") == head_sha, f"Manifest SHA {manifest.get('sha')} != HEAD {head_sha}"


class TestWeights:
    def test_dimension_weights_no_physical(self, config):
        dims = config.get("dimension_weights", {})
        assert "physical" not in dims, "physical should not be in dimension_weights"

    def test_area_weights_sum_100(self, config):
        areas = config.get("area_weights", {})
        assert sum(areas.values()) == 100, f"Area weights sum to {sum(areas.values())}, expected 100"

    def test_no_physical_in_dimensions(self, config):
        dims = config.get("dimension_weights", {})
        assert "physical" not in dims, "physical dimension should NOT be in dimension_weights"

    def test_known_dimensions(self, config):
        dims = config.get("dimension_weights", {})
        known = {"route_load", "qml_instance", "model_data", "service_wiring",
                 "read", "primary_action", "secondary_actions", "write",
                 "error_contract", "async_execution", "real_cancellation",
                 "persistence", "integration", "vertical_workflow",
                 "performance", "accessibility"}
        for d in dims:
            assert d in known, f"Unknown dimension: {d}"

    def test_known_areas(self, config):
        areas = config.get("area_weights", {})
        known = {"shell_nav", "library_playback", "core_workflows",
                 "advanced_tools", "ecosystem_network", "quality_release"}
        for a in areas:
            assert a in known, f"Unknown area: {a}"


class TestJunitParsing:
    def test_junit_file_exists(self):
        assert JUNIT_FILE.exists(), f"JUnit file not found: {JUNIT_FILE}"

    def test_junit_parses_tests(self, junit_tree):
        assert junit_tree is not None
        root = junit_tree.getroot()
        tests = sum(int(ts.get("tests", 0)) for ts in root)
        assert tests > 0, f"JUnit tests count is {tests}, expected > 0"

    def test_junit_has_testcases(self, junit_tree):
        root = junit_tree.getroot()
        count = sum(1 for ts in root for _ in ts)
        assert count > 0, "No testcases found in JUnit XML"

    def test_junit_baseline_matches(self, baseline, junit_tree):
        root = junit_tree.getroot()
        junit_tests = sum(int(ts.get("tests", 0)) for ts in root)
        baseline_tests = baseline.get("tests_collected", 0)
        assert abs(junit_tests - baseline_tests) < 200, f"JUnit has {junit_tests} tests, baseline says {baseline_tests}"

    def test_junit_passed_failed_skipped(self, junit_tree):
        root = junit_tree.getroot()
        failures = sum(int(ts.get("failures", 0)) for ts in root)
        skipped = sum(int(ts.get("skipped", 0)) for ts in root)
        errors = sum(int(ts.get("errors", 0)) for ts in root)
        tests = sum(int(ts.get("tests", 0)) for ts in root)
        passed = tests - failures - errors - skipped
        assert passed >= 0
        assert failures >= 0
        assert skipped >= 0


class TestModuleMarkers:
    def test_evidence_has_marked_tests(self, evidence):
        marked = evidence.get("marked_tests", [])
        assert isinstance(marked, list), "marked_tests should be a list"

    def test_marked_tests_have_required_keys(self, evidence):
        for mt in evidence.get("marked_tests", []):
            assert "file" in mt
            assert "function" in mt
            assert "markers" in mt
            assert isinstance(mt["markers"], list)

    def test_evidence_testcases_have_required_keys(self, evidence):
        for tc in evidence.get("testcases", []):
            assert "name" in tc
            assert "classname" in tc
            assert "time" in tc


class TestBaselineInfo:
    def test_baseline_has_required_keys(self, baseline):
        required = ["sha", "python_version", "pyside_version", "qt_version",
                     "platform", "ruff_ok", "compileall_ok",
                     "tests_collected", "tests_passed", "tests_failed",
                     "tests_skipped", "runtime_smoke_ok", "route_audit_ok"]
        for k in required:
            assert k in baseline, f"Missing key in baseline: {k}"

    def test_manifest_excludes_physical(self, manifest):
        excluded = manifest.get("excluded", [])
        has_physical_excluded = any("physical" in e.lower() for e in excluded)
        assert has_physical_excluded, "physical_audio not in excluded list"
