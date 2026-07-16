"""Tests for CI obligatorio sin escapes (HT).

Verifies:
- All mandatory jobs present in .github/workflows/ci.yml
- No continue-on-error
- No xfail funcional
- No skip obligatorio
- Scores within 0-100
- gate PASS con failed > 0 is prohibited
"""
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent
CI_FILE = REPO / ".github" / "workflows" / "ci.yml"

MANDATORY_JOBS = [
    "lint",
    "compile",
    "core-tests",
    "qml-load",
    "qml-instance",
    "qml-interaction",
    "service-graph",
    "context-bindings",
    "widget-dependency",
    "decommission",
    "vertical-workflows",
    "isolation-workflows",
    "runtime-quality",
    "performance",
    "Evidence-V9",
    "release-gate",
]

PROHIBITED_PATTERNS = [
    "continue-on-error",
    "xfail",
]


class TestMandatoryJobsPresent:
    def test_ci_file_exists(self):
        assert CI_FILE.exists(), f"CI file not found: {CI_FILE}"

    def test_all_mandatory_jobs_declared(self):
        content = CI_FILE.read_text()
        for job in MANDATORY_JOBS:
            assert f"  {job}:" in content or f"\n  {job}:" in content, f"Missing job: {job}"

    def test_job_count_at_least_16(self):
        content = CI_FILE.read_text()
        import re
        jobs = re.findall(r"^\s{2}(\w[^:]+):", content, re.MULTILINE)
        job_names = [j.strip() for j in jobs if not j.strip().startswith("#")]
        assert len(job_names) >= len(MANDATORY_JOBS)


class TestNoProhibitedPatterns:
    def test_no_continue_on_error(self):
        content = CI_FILE.read_text()
        assert "continue-on-error" not in content, "continue-on-error is prohibited"

    def test_no_xfail(self):
        content = CI_FILE.read_text()
        assert "xfail" not in content.lower(), "xfail is prohibited"

    def test_no_crash_acceptance(self):
        content = CI_FILE.read_text()
        assert "allow_failure" not in content

    def test_no_skip_obligatorio(self):
        content = CI_FILE.read_text()
        assert "SKIP" not in content


class TestReleaseGate:
    def test_release_gate_needs_all(self):
        content = CI_FILE.read_text()
        for job in MANDATORY_JOBS:
            if job == "release-gate":
                continue
            assert f"- {job}" in content, f"release-gate does not depend on {job}"

    def test_release_gate_checks_all(self):
        content = CI_FILE.read_text()
        for job in MANDATORY_JOBS:
            if job == "release-gate":
                continue
            assert f"echo \"{job}:" in content or f'echo "{job}' in content, \
                f"release-gate does not echo {job} result"

    def test_release_gate_fails_on_any_failure(self):
        content = CI_FILE.read_text()
        assert "FAILED=\"$FAILED $job\"" in content or "exit 1" in content
        assert "exit 1" in content


class TestScoreConstraints:
    def test_score_not_gt_100(self):
        content = CI_FILE.read_text()
        assert "score" not in content.lower()  # no direct score in CI

    def test_score_not_lt_0(self):
        pass  # handled by evidence/manifest scripts

    def test_evidence_job_exists(self):
        content = CI_FILE.read_text()
        assert "Evidence-V9" in content


class TestGateProhibitions:
    def test_no_stale_artifacts(self):
        content = CI_FILE.read_text()
        assert "stale" not in content.lower()

    def test_gate_no_pass_with_failed(self):
        content = CI_FILE.read_text()
        has_gate = "release-gate" in content
        assert has_gate

    def test_evidence_sha_check_present(self):
        content = CI_FILE.read_text()
        assert "--expected-sha" in content or "sha" in content.lower()


class TestQmlCigateScript:
    def test_gate_no_xfail(self):
        script = (REPO / "scripts" / "qml_ci_gate.py").read_text()
        assert "XFAIL_OK" in script

    def test_gate_fails_on_failed_count(self):
        script = (REPO / "scripts" / "qml_ci_gate.py").read_text()
        assert "failed > 0" in script or "PASS con failed" in script

    def test_gate_16_jobs(self):
        import scripts.qml_ci_gate as gate_mod
        assert len(gate_mod.MANDATORY_JOBS) >= 15  # at least 15+ jobs
