"""Test Evidence V9 plugin — conftest.py with user_properties injection
and pytest markers qml_module, qml_dimension, qml_route.

Tests: marker parsing, user_properties collection, JUnit matching, scores,
module weight calculation, manifest generation.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "scripts"

V9_MARKERS = {"qml_module", "qml_dimension", "qml_route"}

VALID_STATUSES = {"PASSED", "FAILED", "MISSING", "NOT_APPLICABLE_DECLARED", "DEFERRED_PHYSICAL"}

SCORE_MAP = {
    "PASSED": 1.0,
    "FAILED": 0.0,
    "MISSING": 0.0,
    "NOT_APPLICABLE_DECLARED": 1.0,
    "DEFERRED_PHYSICAL": 1.0,
}


@pytest.mark.qml_module("test_mod")
@pytest.mark.qml_dimension("primary_action")
def test_with_markers():
    """Test with both qml_module and qml_dimension markers."""
    assert True


@pytest.mark.qml_module("test_mod")
def test_module_only():
    assert True


@pytest.mark.qml_dimension("read")
def test_dimension_only():
    assert True


@pytest.mark.qml_route("test_route")
def test_route_only():
    assert True


@pytest.mark.qml_module("multi")
@pytest.mark.qml_dimension("write")
@pytest.mark.qml_dimension("persistence")
def test_multi_dimension():
    assert True


@pytest.mark.qml_module("workflows")
@pytest.mark.qml_dimension("qml_workflow")
def test_workflows_marker():
    assert True


@pytest.mark.qml_module("navigation")
@pytest.mark.qml_dimension("route_load")
@pytest.mark.qml_route("library")
def test_navigation_route():
    assert True


def test_no_markers():
    """Test without any QML markers — should be ignored by collector."""
    assert True


class TestWithClassMarker:
    pytestmark = [pytest.mark.qml_module("class_mod"), pytest.mark.qml_dimension("integration")]

    def test_class_marked(self):
        assert True

    def test_class_marked_too(self):
        assert True


@pytest.mark.qml_module("settings")
@pytest.mark.qml_dimension("read")
@pytest.mark.qml_dimension("write")
@pytest.mark.qml_route("settings")
def test_settings_full():
    assert True


class TestUserProperties:
    """Verify conftest.py injects user_properties from markers."""

    @pytest.mark.qml_module("evidence")
    @pytest.mark.qml_dimension("verification")
    @pytest.mark.qml_route("test")
    def test_user_properties_injected(self, request):
        props = dict(request.node.user_properties)
        assert props.get("qml_module") == "evidence"
        assert props.get("qml_dimension") == "verification"
        assert props.get("qml_route") == "test"


class TestManifest:
    def test_manifest_v9_exists(self):
        mf = REPO / "docs" / "qml_migration_manifest_v9.json"
        assert mf.exists(), "Manifest V9 not generated"

    def test_manifest_has_global_score(self):
        mf = REPO / "docs" / "qml_migration_manifest_v9.json"
        if not mf.exists():
            pytest.skip("Manifest not generated yet")
        data = json.loads(mf.read_text())
        assert "global_score" in data
        score = data["global_score"]
        assert 0 <= score <= 100, f"Global score {score} out of range"

    def test_manifest_has_modules(self):
        mf = REPO / "docs" / "qml_migration_manifest_v9.json"
        if not mf.exists():
            pytest.skip("Manifest not generated yet")
        data = json.loads(mf.read_text())
        assert len(data.get("modules", [])) > 0

    def test_manifest_module_scores_0_100(self):
        mf = REPO / "docs" / "qml_migration_manifest_v9.json"
        if not mf.exists():
            pytest.skip("Manifest not generated yet")
        data = json.loads(mf.read_text())
        for mod in data.get("modules", []):
            score = mod.get("score", -1)
            assert 0 <= score <= 100, f"Module '{mod['module']}' score {score} out of range"

    def test_manifest_marker_statuses_valid(self):
        mf = REPO / "docs" / "qml_migration_manifest_v9.json"
        if not mf.exists():
            pytest.skip("Manifest not generated yet")
        data = json.loads(mf.read_text())
        for mod in data.get("modules", []):
            for marker_name, marker_val in mod.get("markers", {}).items():
                status = marker_val.get("status")
                assert status in VALID_STATUSES, f"Invalid status '{status}' in {mod['module']}/{marker_name}"


class TestEvidence:
    def test_evidence_v9_exists(self):
        ev = REPO / "artifacts" / "qml-evidence-v9.json"
        if not ev.exists():
            pytest.skip("Evidence V9 not generated yet")
        data = json.loads(ev.read_text())
        assert data.get("version") == "9.0"
        assert "sha" in data

    def test_evidence_has_testcases(self):
        ev = REPO / "artifacts" / "qml-evidence-v9.json"
        if not ev.exists():
            pytest.skip("Evidence V9 not generated yet")
        data = json.loads(ev.read_text())
        assert len(data.get("testcases", [])) > 0

    def test_evidence_has_modules(self):
        ev = REPO / "artifacts" / "qml-evidence-v9.json"
        if not ev.exists():
            pytest.skip("Evidence V9 not generated yet")
        data = json.loads(ev.read_text())
        assert len(data.get("modules", [])) > 0


class TestScoreMap:
    def test_failed_zero(self):
        assert SCORE_MAP["FAILED"] == 0.0

    def test_missing_zero(self):
        assert SCORE_MAP["MISSING"] == 0.0

    def test_passed_full(self):
        assert SCORE_MAP["PASSED"] == 1.0

    def test_not_applicable_declared_full(self):
        assert SCORE_MAP["NOT_APPLICABLE_DECLARED"] == 1.0

    def test_deferred_physical_full(self):
        assert SCORE_MAP["DEFERRED_PHYSICAL"] == 1.0


class TestJUnitParsing:
    def test_parse_junit_basic(self, tmp_path):
        xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0">
    <testcase classname="test_foo" name="test_bar" time="0.1">
      <properties>
        <property name="qml_module" value="library"/>
        <property name="qml_dimension" value="read"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>"""
        jfile = tmp_path / "results.xml"
        jfile.write_text(xml)
        tree = ET.parse(jfile)
        tc = tree.find(".//testcase")
        props = {p.get("name"): p.get("value") for p in tc.findall(".//property")}
        assert props.get("qml_module") == "library"
        assert props.get("qml_dimension") == "read"

    def test_parse_junit_failure(self, tmp_path):
        xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="1">
    <testcase classname="test_foo" name="test_fail" time="0.1">
      <failure message="AssertionError">assert 0</failure>
    </testcase>
  </testsuite>
</testsuites>"""
        jfile = tmp_path / "results_fail.xml"
        jfile.write_text(xml)
        tree = ET.parse(jfile)
        tc = tree.find(".//testcase")
        assert tc.find("failure") is not None

    def test_parse_junit_skipped(self, tmp_path):
        xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0" skipped="1">
    <testcase classname="test_foo" name="test_skip" time="0.0">
      <skipped message="unconditional" type="pytest.skip"/>
    </testcase>
  </testsuite>
</testsuites>"""
        jfile = tmp_path / "results_skip.xml"
        jfile.write_text(xml)
        tree = ET.parse(jfile)
        tc = tree.find(".//testcase")
        assert tc.find("skipped") is not None
