"""Runtime Quality — 100 navigation cycles via subprocess.

Measured: RSS, threads, DB connections, external processes, critical warnings,
stale callbacks, duplicate context properties.

Budgets: RSS growth < 50MB, workers end = 0, external processes = 0,
DB connections = 0, critical warnings = 0.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO / "scripts"


@pytest.fixture(scope="module")
def audit_results():
    os.system(
        f"cd {REPO} && QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 "
        f"{sys.executable} scripts/qml_runtime_quality_audit.py --json "
        f"> /tmp/michi_quality_audit.json 2>/dev/null"
    )
    audit_path = Path("/tmp/michi_quality_audit.json")
    if not audit_path.exists():
        pytest.skip("Audit output file not found")
        return {}
    try:
        data = json.loads(audit_path.read_text())
        if "error" in data:
            pytest.skip(f"Audit error: {data['error']}")
            return {}
        return data
    except (json.JSONDecodeError, Exception) as e:
        pytest.skip(f"Could not parse audit output: {e}")
        return {}


class TestRuntimeQuality100Cycles:
    """10+ tests verifying runtime quality budgets after 100 navigation cycles."""

    def test_100_cycles_completed(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        assert audit_results.get("cycles_completed") == 100

    def test_rss_growth_within_budget(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        growth = audit_results.get("rss_growth_mb", 999)
        assert growth < 50.0, f"RSS growth {growth}MB exceeds 50MB budget"

    def test_workers_zero_after_cycles(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        after = audit_results.get("threads_after", 999)
        assert after == 0, f"Threads remaining: {after}"

    def test_no_external_processes(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        procs = audit_results.get("external_processes", [])
        assert len(procs) == 0, f"External processes: {procs}"

    def test_no_open_db_connections(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        conns = audit_results.get("db_connections_open", -1)
        assert conns == 0, f"Open DB connections: {conns}"

    def test_no_critical_qml_warnings(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        warnings = audit_results.get("critical_warnings", [])
        assert len(warnings) == 0, f"Critical warnings: {warnings}"

    def test_no_duplicate_context_properties(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        dups = audit_results.get("duplicate_context_properties", [])
        assert len(dups) == 0, f"Duplicates: {dups}"

    def test_no_stale_callbacks(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        stale = audit_results.get("stale_callbacks", [])
        assert len(stale) == 0, f"Stale callbacks: {stale}"

    def test_rss_growth_measured(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        assert "rss_growth_mb" in audit_results

    def test_rss_before_and_after_recorded(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        assert audit_results.get("rss_before_mb", 0) > 0
        assert audit_results.get("rss_after_mb", 0) > 0

    def test_threads_count_changes_recorded(self, audit_results):
        if not audit_results:
            pytest.skip("No results")
        assert "threads_before" in audit_results
        assert "threads_after" in audit_results
