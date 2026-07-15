#!/usr/bin/env python3
"""Runtime Quality Gate — executes checks and FAILS if budgets are exceeded.

Presupuestos (budgets):
  - RSS growth < 50MB (100 navigation cycles)
  - threads at end = 0
  - external processes = 0
  - DB connections open = 0
  - critical warnings = 0
  - duplicate context properties = 0
  - stale callbacks = 0
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

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
    """Run budget checks against an audit result dict. Returns {name: check}."""
    BUDGETS_LOCAL = dict(BUDGETS)
    checks = {}

    rss_growth = result.get("rss_growth_mb", 0)
    checks["rss_growth"] = {
        "value": rss_growth,
        "budget": BUDGETS_LOCAL["rss_growth_mb_max"],
        "ok": rss_growth < BUDGETS_LOCAL["rss_growth_mb_max"],
    }

    threads = result.get("threads_after", -1)
    checks["threads"] = {
        "value": threads,
        "expected": BUDGETS_LOCAL["threads_expected"],
        "ok": threads == BUDGETS_LOCAL["threads_expected"],
    }

    ext_procs = result.get("external_processes", [])
    ext_count = len(ext_procs)
    checks["external_processes"] = {
        "value": ext_count,
        "expected": BUDGETS_LOCAL["external_processes_expected"],
        "ok": ext_count == BUDGETS_LOCAL["external_processes_expected"],
    }

    db_conns = result.get("db_connections_open", -1)
    checks["db_connections"] = {
        "value": db_conns,
        "expected": BUDGETS_LOCAL["db_connections_expected"],
        "ok": db_conns == BUDGETS_LOCAL["db_connections_expected"],
    }

    crit_warnings = result.get("critical_warnings", [])
    crit_count = len(crit_warnings)
    checks["critical_warnings"] = {
        "value": crit_count,
        "expected": BUDGETS_LOCAL["critical_warnings_expected"],
        "ok": crit_count == BUDGETS_LOCAL["critical_warnings_expected"],
    }

    duplicates = result.get("duplicate_context_properties", [])
    dup_count = len(duplicates)
    checks["duplicate_context_properties"] = {
        "value": dup_count,
        "expected": BUDGETS_LOCAL["duplicates_expected"],
        "ok": dup_count == BUDGETS_LOCAL["duplicates_expected"],
    }

    stale = result.get("stale_callbacks", [])
    stale_count = len(stale)
    checks["stale_callbacks"] = {
        "value": stale_count,
        "expected": BUDGETS_LOCAL["stale_callbacks_expected"],
        "ok": stale_count == BUDGETS_LOCAL["stale_callbacks_expected"],
    }

    return checks


def run_gate() -> dict:
    from scripts.qml_runtime_quality_audit import run as run_audit

    result = run_audit()
    if "error" in result:
        return {"passed": False, "error": result["error"], "result": result}

    checks = _run_checks(result)
    all_ok = all(c["ok"] for c in checks.values())

    return {
        "passed": all_ok,
        "checks": checks,
        "result": result,
    }


def main():
    gate_result = run_gate()
    outpath = Path("/tmp/qml_runtime_quality_gate.json")
    outpath.write_text(json.dumps(gate_result, indent=2, default=str))
    print(f"Results written to {outpath}")

    print(f"\n{'='*60}")
    print("  QML Runtime Quality Gate")
    print(f"{'='*60}")
    for name, check in gate_result.get("checks", {}).items():
        status = "PASS" if check["ok"] else "FAIL"
        print(f"  {name:40s} {status}")
        if not check["ok"]:
            print(f"    value={check['value']}, budget/expected={check.get('budget', check.get('expected'))}")

    overall = gate_result["passed"]
    print(f"\n{'='*60}")
    print(f"  GATE: {'PASSED' if overall else 'FAILED'}")
    print(f"{'='*60}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
