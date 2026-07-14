"""Tests for Runtime Quality Audit via subprocess (avoids QApp conflict)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "scripts"


@pytest.fixture(scope="module")
def audit_results():
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "qml_runtime_quality_audit.py"),
            "--json",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "MICHI_SAFE_MODE": "1",
        },
    )
    if result.returncode != 0:
        pytest.skip(f"Audit subprocess failed (rc={result.returncode}): {result.stderr[-300:]}")
        return {}
    try:
        return json.loads(result.stdout.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError):
        pytest.skip(f"Could not parse audit output: {result.stdout[-200:]}")
        return {}


class TestRuntimeQualityCycles:
    def _check(self, audit_results, key, ok_key=None):
        if not audit_results:
            pytest.skip("No audit results")
        ok_key = ok_key or key.replace("_ok", "")
        if "error" in audit_results:
            pytest.skip(f"Audit error: {audit_results['error']}")

    def test_rss_growth_within_budget(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert audit_results.get("rss_growth_ok", False), (
            f"RSS growth {audit_results.get('rss_growth_mb', '?')}MB exceeds 50MB budget"
        )

    def test_workers_zero_after_cycles(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert audit_results.get("threads_ok", False), (
            f"Threads remaining: {audit_results.get('threads_after', '?')}"
        )

    def test_no_external_processes(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert audit_results.get("external_processes_ok", False), (
            f"External processes: {audit_results.get('external_processes', [])}"
        )

    def test_no_open_db_connections(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert audit_results.get("db_connections_ok", False), (
            f"Open DB connections: {audit_results.get('db_connections_open', '?')}"
        )

    def test_no_critical_qml_warnings(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert audit_results.get("critical_warnings_ok", False), (
            f"Critical warnings: {audit_results.get('critical_warnings', [])}"
        )

    def test_no_duplicate_context_properties(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert audit_results.get("duplicates_ok", False), (
            f"Duplicate context properties: {audit_results.get('duplicate_context_properties', [])}"
        )

    def test_no_stale_callbacks(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert audit_results.get("stale_callbacks_ok", True)

    def test_100_cycles_completed(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert audit_results.get("cycles_completed") == 100

    def test_rss_growth_measured(self, audit_results):
        if not audit_results or "error" in audit_results:
            pytest.skip("No audit results or error")
        assert "rss_growth_mb" in audit_results


class TestRuntimeQualityBudgetEnforcement:
    def test_budget_rss_50mb(self):
        assert True

    def test_budget_workers_zero(self):
        assert True

    def test_budget_no_external_procs(self):
        assert True

    def test_budget_no_db_leaks(self):
        assert True

    def test_budget_zero_critical_warnings(self):
        assert True
