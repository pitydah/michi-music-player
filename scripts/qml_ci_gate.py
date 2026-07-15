#!/usr/bin/env python3
"""QML CI Gate V9 — runs all mandatory jobs without escapes.

Jobs: lint, compile, core-tests, qml-load, qml-instance, qml-interaction,
service-graph, context-bindings, widget-dependency, decommission,
vertical-workflows, isolation-workflows, runtime-quality, performance,
Evidence-V9, release-gate.

Prohibited: continue-on-error, crashes aceptados, xfail funcional,
skip obligatorio, artifacts stale, score >100, score <0,
gate PASS con failed >0.

Output: /tmp/michi_qml_ci_gate.json (results dict).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = {**dict(sorted(os.environ.items())), "QT_QPA_PLATFORM": "offscreen", "MICHI_SAFE_MODE": "1"}

MANDATORY_JOBS = [
    "ruff",
    "compileall",
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
]

STEPS = [
    ("ruff", ["ruff", "check", ".", "--output-format", "concise"]),
    ("compileall", [sys.executable, "-m", "compileall", "-q", "-x", r"\.venv/|\.tmpl\."]),
    ("core-tests", [sys.executable, "-m", "pytest", "tests/test_schema.py", "tests/test_format_probe.py", "tests/test_packaging.py", "-q"]),
    ("qml-load", [sys.executable, "scripts/qml_compile_all.py"]),
    ("qml-instance", [sys.executable, "scripts/qml_instance_all.py"]),
    ("qml-interaction", [sys.executable, "-m", "pytest", "tests/qml/workflows/test_qml_interaction_real.py", "-q", "--timeout=600"]),
    ("service-graph", [sys.executable, "scripts/qml_productive_service_audit.py"]),
    ("context-bindings", [sys.executable, "scripts/qml_bridge_contract_audit.py"]),
    ("widget-dependency", [sys.executable, "scripts/qml_hybrid_dependency_audit.py"]),
    ("decommission", [sys.executable, "scripts/qml_decommission_audit.py"]),
    ("vertical-workflows", [sys.executable, "-m", "pytest", "tests/qml/workflows", "-q", "--timeout=600"]),
    ("isolation-workflows", [sys.executable, "-m", "pytest", "tests/qml", "-m", "isolation", "-q", "--timeout=300"]),
    ("runtime-quality", [sys.executable, "scripts/qml_runtime_quality_audit.py"]),
    ("performance", [sys.executable, "scripts/qml_library_benchmark.py"]),
    ("Evidence-V9", [sys.executable, "-m", "pytest", "tests/qml/test_evidence_v9_plugin.py", "-q"]),
]

XFAIL_OK: set[str] = set()


def run() -> dict:
    results = {}
    failed = False
    for name, cmd in STEPS:
        env = {**ENV}
        print(f"\n{'='*60}")
        print(f"[{name}] Running: {' '.join(cmd)}")
        print(f"{'='*60}")

        try:
            proc = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            results[name] = {"ok": False, "error": "TIMEOUT", "returncode": -1}
            print(f"[{name}] TIMEOUT")
            failed = True
            break
        ok = proc.returncode == 0

        if name in XFAIL_OK and not ok:
            ok = True
            print(f"[{name}] XFAIL (tolerated)")

        results[name] = {
            "ok": ok,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-500:] if proc.stdout else "",
            "stderr": proc.stderr[-500:] if proc.stderr else "",
        }
        if ok:
            print(f"[{name}] PASSED")
        else:
            print(f"[{name}] FAILED (rc={proc.returncode})")
            print(proc.stdout[-300:])
            print(proc.stderr[-300:])
            failed = True
            break

    return {
        "results": results,
        "passed": not failed,
        "total": len(STEPS),
        "failed_count": sum(1 for v in results.values() if not v.get("ok")),
        "mandatory_jobs": MANDATORY_JOBS,
    }


def main():
    result = run()
    outpath = Path("/tmp/michi_qml_ci_gate.json")
    outpath.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nResults written to {outpath}")
    passed = result["passed"]
    fc = result["failed_count"]
    print(f"Gate status: {'PASSED' if passed else 'FAILED'}")
    if passed and fc > 0:
        print("ERROR: gate PASS con failed > 0 — forbidden")
        return 1
    if not passed and fc == 0:
        print("ERROR: inconsistent state")
        return 1
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
