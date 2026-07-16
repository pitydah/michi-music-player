#!/usr/bin/env python3
"""Gate V16 — validates Evidence V16, placeholders, actions, and widgets."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    ep = repo / "artifacts" / "qml-evidence-v16.json"
    if not ep.exists():
        print("GATE FAILED: Evidence V16 not found")
        sys.exit(1)

    with open(ep) as f:
        ev = json.load(f)

    failures = []
    if ev.get("junit", {}).get("errors", 0) > 0:
        failures.append("JUnit errors present")
    if ev.get("junit", {}).get("failures", 0) > 0:
        failures.append("JUnit failures present")
    if not ev.get("sha_match", True):
        failures.append("SHA mismatch")
    if ev.get("scores", {}).get("overall", 0) < 100:
        failures.append(f"Score {ev.get('scores', {}).get('overall', 0)}% != 100%")
    if ev.get("issues"):
        failures.append(f"Placeholders: {ev['issues']}")

    # Check bootstrap for object/lambda
    bp = repo / "core" / "application_bootstrap.py"
    if bp.exists():
        c = bp.read_text()
        if "object()" in c:
            failures.append("object() found in bootstrap")
        if "lambda: None" in c:
            failures.append("lambda: None found in bootstrap")

    # Check ActionRegistry action count
    action_count = c.count("ActionDescriptor(") if bp.exists() else 0
    if action_count < 40:
        failures.append(f"Only {action_count} ActionDescriptors (< 40)")

    # Check productive_workflows_v16
    wf = repo / "tests" / "qml" / "productive_workflows_v16"
    if not wf.exists():
        failures.append("productive_workflows_v16/ missing")
    else:
        wf_files = list(wf.glob("test_*.py"))
        if len(wf_files) < 5:
            failures.append(f"Only {len(wf_files)} workflow tests (< 5)")

    passed = len(failures) == 0
    result = {"gate": "v16", "passed": passed, "failures": failures,
              "score": 100 if passed else max(0, 100 - len(failures) * 10),
              "action_count": action_count}

    rp = repo / "artifacts" / "qml-gate-v16.json"
    with open(rp, "w") as f:
        json.dump(result, f, indent=2)

    if passed:
        print(f"GATE V16 PASSED (score=100, actions={action_count})")
    else:
        print(f"GATE V16 FAILED (score={result['score']})")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
