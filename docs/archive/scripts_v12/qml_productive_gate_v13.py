#!/usr/bin/env python3
"""QML Productive Gate V13 — validates Evidence V13 and stops build on failure."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main():
    repo_root = Path(__file__).parent.parent
    evidence_path = repo_root / "artifacts" / "qml-evidence-v13.json"

    if not evidence_path.exists():
        print("GATE FAILED: Evidence V13 not found")
        sys.exit(1)

    with open(evidence_path) as f:
        evidence = json.load(f)

    failures = []

    if evidence.get("junit", {}).get("errors", 0) > 0:
        failures.append("JUnit has errors")

    if evidence.get("junit", {}).get("failures", 0) > 0:
        failures.append("JUnit has failures")

    if not evidence.get("sha_match", True):
        failures.append("SHA mismatch")

    if not evidence.get("issues", {}).get("object_placeholders", False):
        count = len(evidence.get("object_placeholders", []))
        failures.append(f"{count} object() placeholders in bootstrap")

    if not evidence.get("issues", {}).get("lambda_handlers", False):
        count = len(evidence.get("lambda_handlers", []))
        failures.append(f"{count} lambda: None handlers in ActionRegistry")

    score = 100 if not failures else max(0, 100 - len(failures) * 15)

    result = {
        "gate": "v13",
        "passed": len(failures) == 0,
        "score": score,
        "failures": failures,
        "sha": evidence.get("sha", ""),
    }

    result_path = repo_root / "artifacts" / "qml-gate-v13.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

    if result["passed"]:
        print(f"GATE PASSED (score={score})")
    else:
        print(f"GATE FAILED (score={score})")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
