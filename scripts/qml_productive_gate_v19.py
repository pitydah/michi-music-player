#!/usr/bin/env python3
"""Gate V19 — full validation."""
from __future__ import annotations
import json
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    ep = repo / "artifacts" / "qml-evidence-v19.json"
    if not ep.exists():
        print("GATE FAILED: Evidence V19 not found")
        sys.exit(1)
    with open(ep) as f:
        ev = json.load(f)
    failures = []
    if ev.get("junit", {}).get("errors", 0) > 0:
        failures.append("JUnit errors")
    if ev.get("junit", {}).get("failures", 0) > 0:
        failures.append("JUnit failures")
    if not ev.get("sha_match", True):
        failures.append("SHA mismatch")
    if ev.get("scores", {}).get("overall", 0) < 100:
        failures.append(f"Score {ev['scores']['overall']}% != 100%")
    if ev.get("issues"):
        failures.append(f"Placeholders: {ev['issues']}")
    bp = repo / "core" / "application_bootstrap.py"
    if bp.exists():
        c = bp.read_text()
        for pat in ["object()", "lambda: None"]:
            if pat in c:
                failures.append(f"{pat} in bootstrap")
        if "PlayerService(engine=None)" in c:
            failures.append("PlayerService(engine=None) in bootstrap")
        ac = c.count("ActionDescriptor(")
        if ac < 55:
            failures.append(f"Only {ac} ActionDescriptors (< 55)")
    for audit in ["qml_widget_dependency_audit_v19.py", "qml_placeholder_audit_v19.py",
                  "qml_fake_bridge_audit_v19.py", "qml_action_handler_audit_v19.py",
                  "qml_real_engine_workflow_audit_v19.py", "qml_legacy_business_logic_audit_v19.py",
                  "qml_vertical_function_audit_v19.py",
                  "qml_null_bridge_audit.py", "qml_real_test_integrity_audit.py"]:
        if not (repo / "scripts" / audit).exists():
            failures.append(f"Missing audit: {audit}")
    # NullBridge check
    null_count = 0
    for f in (repo / "tests").rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        if "NullBridge" in f.read_text():
            null_count += 1
    if null_count > 0:
        failures.append(f"NullBridge found in {null_count} test files")
    # Real test integrity
    bad_real = []
    for pattern in ("*real*.py", "*interactive*.py"):
        for f in (repo / "tests").rglob(pattern):
            if "__pycache__" in str(f):
                continue
            if "MagicMock" in f.read_text():
                bad_real.append(f.name)
    if bad_real:
        failures.append(f"Tests named 'real' use MagicMock: {bad_real}")
    # Shim count
    shim_count = sum(1 for _ in (repo / "ui").rglob("*.py") if _.name != "__init__.py")
    if shim_count > 3:
        failures.append(f"Too many shims in ui/ ({shim_count})")
    wf = repo / "tests" / "qml" / "productive_workflows_v19"
    if not wf.exists():
        failures.append("productive_workflows_v19/ missing")
    else:
        wff = list(wf.glob("test_*.py"))
        if len(wff) < 15:
            failures.append(f"Only {len(wff)} workflow tests (< 15)")
    passed = len(failures) == 0
    result = {"gate": "v19", "passed": passed, "failures": failures,
              "score": 100 if passed else max(0, 100 - len(failures) * 7)}
    rp = repo / "artifacts" / "qml-gate-v19.json"
    with open(rp, "w") as f:
        json.dump(result, f, indent=2)
    if passed:
        print("GATE V19 PASSED (score=100)")
    else:
        print(f"GATE V19 FAILED (score={result['score']})")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
