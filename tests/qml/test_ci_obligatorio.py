"""Tests for CI obligatorio sin escapes (HT).

Verifies:
- All mandatory jobs present in .github/workflows/ci.yml
- No xfail obligatorio
- No skip obligatorio
"""
import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent
CI_FILE = REPO / ".github" / "workflows" / "ci.yml"

MANDATORY_JOBS = [
    "lint",
    "functional-tests",
    "inventory",
]


class TestMandatoryJobsPresent:
    """Verify all expected CI jobs exist in ci.yml."""

    def test_ci_file_exists(self) -> None:
        assert CI_FILE.exists(), f"CI file not found: {CI_FILE}"

    def test_all_mandatory_jobs_declared(self) -> None:
        content = CI_FILE.read_text()
        for job in MANDATORY_JOBS:
            assert f"  {job}:" in content or f"\n  {job}:" in content, f"Missing job: {job}"

    def test_job_count_at_least_3(self) -> None:
        content = CI_FILE.read_text()
        jobs = re.findall(r"^\s{2}(\w[^:]+):", content, re.MULTILINE)
        job_names = [j.strip() for j in jobs if not j.strip().startswith("#")]
        assert len(job_names) >= len(MANDATORY_JOBS)


class TestNoProhibitedPatterns:
    """Ensure no prohibited CI escape patterns (xfail, allow_failure, SKIP)."""

    def test_no_xfail(self) -> None:
        content = CI_FILE.read_text()
        assert "xfail" not in content.lower(), "xfail is prohibited"

    def test_no_crash_acceptance(self) -> None:
        content = CI_FILE.read_text()
        assert "allow_failure" not in content

    def test_no_skip_obligatorio(self) -> None:
        content = CI_FILE.read_text()
        assert "SKIP" not in content
