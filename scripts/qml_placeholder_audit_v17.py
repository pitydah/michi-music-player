#!/usr/bin/env python3
"""Audit: object(), lambda: None, PlayerService(engine=None)."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    for pattern in ["object()", "lambda: None"]:
        r = subprocess.run(
            ["git", "grep", "-n", pattern, "--",
             "core/", "michi/", "audio/", "library/", "ui_qml_bridge/"],
            capture_output=True, text=True, cwd=repo)
        for line in r.stdout.strip().split("\n"):
            if pattern in line and line.strip():
                errors.append(f"{pattern}: {line.strip()[:120]}")
    r = subprocess.run(
        ["git", "grep", "-n", "PlayerService(engine=None)", "--", "core/"],
        capture_output=True, text=True, cwd=repo)
    for line in r.stdout.strip().split("\n"):
        if "PlayerService" in line and line.strip():
            errors.append(f"PlayerService(engine=None): {line.strip()[:120]}")
    if errors:
        print("PLACEHOLDER AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("PLACEHOLDER AUDIT PASSED")


if __name__ == "__main__":
    main()
