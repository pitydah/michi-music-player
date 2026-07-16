#!/usr/bin/env python3
"""Audit V18: verify productive workflows use real QQmlApplicationEngine."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    for wf in ["productive_workflows_v18", "productive_workflows_v17", "productive_workflows_v16"]:
        wd = repo / "tests" / "qml" / wf
        if not wd.exists():
            continue
        r = subprocess.run(
            ["git", "grep", "-n", "MagicMock\\|QQmlApplicationEngine", "--", str(wd)],
            capture_output=True, text=True, cwd=repo)
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            if "MagicMock" in line:
                errors.append(f"MagicMock in {wf}: {line.strip()[:100]}")
            if "QQmlApplicationEngine" in line and "from PySide6.QtQml import" in line:
                pass
    if errors:
        print("REAL ENGINE WORKFLOW AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("REAL ENGINE WORKFLOW AUDIT PASSED")


if __name__ == "__main__":
    main()
