from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent.parent
CI_PATH = REPO / ".github" / "workflows" / "ci.yml"


def _load_ci() -> dict:
    with open(CI_PATH) as f:
        return yaml.safe_load(f)


class TestCIConfig:
    def test_ci_file_exists(self):
        assert CI_PATH.exists()

    def test_ci_has_on_push(self):
        ci = _load_ci()
        assert "push" in ci.get("on", {})

    def test_has_core_lint_job(self):
        ci = _load_ci()
        assert "core-lint" in ci.get("jobs", {})

    def test_has_core_compile_job(self):
        ci = _load_ci()
        assert "core-compile" in ci.get("jobs", {})

    def test_has_composition_tests_job(self):
        ci = _load_ci()
        assert "composition-tests" in ci.get("jobs", {})

    def test_has_shutdown_tests_job(self):
        ci = _load_ci()
        assert "shutdown-tests" in ci.get("jobs", {})

    def test_has_widget_boundary_audit_job(self):
        ci = _load_ci()
        assert "widget-boundary-audit" in ci.get("jobs", {})

    def test_no_continue_on_error(self):
        raw = CI_PATH.read_text()
        assert "continue-on-error" not in raw

    def test_no_or_true(self):
        raw = CI_PATH.read_text()
        assert "|| true" not in raw
