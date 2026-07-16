#!/usr/bin/env python3
"""Audit V19: verify productive workflows use real QQmlApplicationEngine."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    for wf in ["productive_workflows_v19", "productive_workflows_v18"]:
        wd = repo / "tests" / "qml" / wf
        if not wd.exists():
            continue
        r = subprocess.run(
            ["git", "grep", "-n", "MagicMock", "--", str(wd)],
            capture_output=True, text=True, cwd=repo)
        for line in r.stdout.strip().split("\n"):
            if line.strip():
                errors.append(f"MagicMock in {wf}: {line.strip()[:100]}")
    if errors:
        print("REAL ENGINE WORKFLOW AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("REAL ENGINE WORKFLOW AUDIT PASSED")


if __name__ == "__main__":
    main()
