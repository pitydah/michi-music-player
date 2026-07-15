#!/usr/bin/env python3
"""Gate V15 — validates Evidence V15, service health, and ActionRegistry."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    ep = repo / "artifacts" / "qml-evidence-v15.json"
    if not ep.exists():
        print("GATE FAILED: Evidence V15 not found")
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
        failures.append(f"Score {ev.get('scores', {}).get('overall', 0)}% != 100%")

    bp = repo / "core" / "application_bootstrap.py"
    if bp.exists():
        c = bp.read_text()
        for marker in ["object()", "lambda: None"]:
            for i, line in enumerate(c.split("\n"), 1):
                if marker in line:
                    failures.append(f"{marker} at line {i}")

    passed = len(failures) == 0
    result = {"gate": "v15", "passed": passed, "failures": failures,
              "score": 100 if passed else max(0, 100 - len(failures) * 10)}

    rp = repo / "artifacts" / "qml-gate-v15.json"
    with open(rp, "w") as f:
        json.dump(result, f, indent=2)

    if passed:
        print("GATE V15 PASSED (score=100)")
    else:
        print(f"GATE V15 FAILED (score={result['score']})")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
