from __future__ import annotations

from pathlib import Path

from scripts.qml_integration_preflight import run_preflight, load_manifest

REPO = Path(__file__).resolve().parent.parent.parent.parent
TEST_MANIFESTS = {
    "empty": str(REPO / "docs" / "qml_migration_manifest_v9.json"),
    "main": str(REPO / "docs" / "qml_migration_manifest_v8.json"),
}


class TestPreflight:
    def test_empty_manifest_load(self):
        m = load_manifest("/nonexistent/file.json")
        assert m == {}

    def test_load_real_manifest(self):
        m = load_manifest(str(REPO / "docs" / "qml_migration_manifest_v9.json"))
        assert isinstance(m, dict)

    def test_run_preflight_returns_dict(self):
        result = run_preflight(TEST_MANIFESTS)
        assert isinstance(result, dict)

    def test_run_preflight_has_passed_key(self):
        result = run_preflight(TEST_MANIFESTS)
        assert "passed" in result

    def test_run_preflight_has_issue_count(self):
        result = run_preflight(TEST_MANIFESTS)
        assert "issue_count" in result
        assert isinstance(result["issue_count"], int)

    def test_run_preflight_has_summary(self):
        result = run_preflight(TEST_MANIFESTS)
        assert "summary" in result

    def test_run_preflight_summary_has_route_overlaps(self):
        result = run_preflight(TEST_MANIFESTS)
        assert "route_overlaps" in result["summary"]

    def test_run_preflight_summary_has_name_conflicts(self):
        result = run_preflight(TEST_MANIFESTS)
        assert "name_conflicts" in result["summary"]

    def test_run_preflight_no_manifests(self):
        result = run_preflight({})
        assert result["passed"] is True
