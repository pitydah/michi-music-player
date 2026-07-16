#!/usr/bin/env python3
"""Gate V18 — validates Evidence, placeholders, actions, widgets, workflows."""
from __future__ import annotations
import json
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    ep = repo / "artifacts" / "qml-evidence-v18.json"
    if not ep.exists():
        print("GATE FAILED: Evidence V18 not found")
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
        action_count = c.count("ActionDescriptor(")
        if action_count < 50:
            failures.append(f"Only {action_count} ActionDescriptors (< 50)")

    for audit in ["qml_widget_dependency_audit_v18.py",
                  "qml_placeholder_audit_v18.py",
                  "qml_fake_bridge_audit_v18.py"]:
        audit_path = repo / "scripts" / audit
        if not audit_path.exists():
            failures.append(f"Missing audit: {audit}")

    wf = repo / "tests" / "qml" / "productive_workflows_v18"
    if not wf.exists():
        failures.append("productive_workflows_v18/ missing")
    else:
        wf_files = list(wf.glob("test_*.py"))
        if len(wf_files) < 12:
            failures.append(f"Only {len(wf_files)} workflow tests (< 12)")

    passed = len(failures) == 0
    result = {"gate": "v18", "passed": passed, "failures": failures,
              "score": 100 if passed else max(0, 100 - len(failures) * 7)}
    rp = repo / "artifacts" / "qml-gate-v18.json"
    with open(rp, "w") as f:
        json.dump(result, f, indent=2)
    if passed:
        print("GATE V18 PASSED (score=100)")
    else:
        print(f"GATE V18 FAILED (score={result['score']})")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
