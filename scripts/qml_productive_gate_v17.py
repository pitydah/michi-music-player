#!/usr/bin/env python3
"""Gate V17 — validates Evidence, placeholders, actions, engine, backend."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    ep = repo / "artifacts" / "qml-evidence-v17.json"
    if not ep.exists():
        print("GATE FAILED: Evidence V17 not found")
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
    s = ev.get("scores", {}).get("overall", 0)
    if s < 100:
        failures.append(f"Score {s}% != 100%")
    if ev.get("issues"):
        failures.append(f"Placeholders: {ev['issues']}")

    bp = repo / "core" / "application_bootstrap.py"
    if bp.exists():
        c = bp.read_text()
        if "object()" in c:
            failures.append("object() in bootstrap")
        if "lambda: None" in c:
            failures.append("lambda: None in bootstrap")
        if "PlayerService(engine=None)" in c:
            failures.append("PlayerService(engine=None) in bootstrap")
        action_count = c.count("ActionDescriptor(")
        if action_count < 50:
            failures.append(f"Only {action_count} ActionDescriptors (< 50)")

    wf = repo / "tests" / "qml" / "productive_workflows_v17"
    if not wf.exists():
        failures.append("productive_workflows_v17/ missing")
    else:
        wf_files = list(wf.glob("test_*.py"))
        if len(wf_files) < 10:
            failures.append(f"Only {len(wf_files)} workflow tests (< 10)")

    passed = len(failures) == 0
    result = {"gate": "v17", "passed": passed, "failures": failures,
              "score": 100 if passed else max(0, 100 - len(failures) * 8)}

    rp = repo / "artifacts" / "qml-gate-v17.json"
    with open(rp, "w") as f:
        json.dump(result, f, indent=2)

    if passed:
        print("GATE V17 PASSED (score=100)")
    else:
        print(f"GATE V17 FAILED (score={result['score']})")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
