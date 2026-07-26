from __future__ import annotations

import scripts.qml_runtime_quality_audit

BUDGETS = {
    "rss_growth_mb_max": 50.0,
    "threads_expected": 0,
    "external_processes_expected": 0,
    "db_connections_expected": 0,
    "critical_warnings_expected": 0,
    "duplicates_expected": 0,
    "stale_callbacks_expected": 0,
}


def _run_checks(result: dict) -> dict:
    checks = {}
    rss = result.get("rss_growth_mb", 0)
    budget_rss = BUDGETS.get("rss_growth_mb_max", 50.0)
    checks["rss_growth"] = {"value": rss, "budget": budget_rss, "ok": rss <= budget_rss}

    threads = result.get("threads_after", 0)
    expected_threads = BUDGETS.get("threads_expected", 0)
    checks["threads"] = {"value": threads, "expected": expected_threads, "ok": threads == expected_threads}

    procs = result.get("external_processes", [])
    checks["external_processes"] = {"value": len(procs), "expected": 0, "ok": len(procs) == 0}

    db = result.get("db_connections_open", 0)
    checks["db_connections"] = {"value": db, "expected": 0, "ok": db == 0}

    warnings = result.get("critical_warnings", [])
    checks["critical_warnings"] = {"value": len(warnings), "expected": 0, "ok": len(warnings) == 0}

    dups = result.get("duplicate_context_properties", [])
    checks["duplicate_context_properties"] = {"value": len(dups), "expected": 0, "ok": len(dups) == 0}

    stale = result.get("stale_callbacks", [])
    checks["stale_callbacks"] = {"value": len(stale), "expected": 0, "ok": len(stale) == 0}

    return checks


def run_gate() -> dict:
    result = scripts.qml_runtime_quality_audit.run()
    checks = _run_checks(result)
    passed = all(c["ok"] for c in checks.values())
    return {"passed": passed, "checks": checks, "result": result}
