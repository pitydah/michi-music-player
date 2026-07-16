#!/usr/bin/env python3
"""Audit: find object() placeholders and lambda: None handlers in production code."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []

    # 1. object() en archivos productivos
    r = subprocess.run(
        ["git", "grep", "-n", "object()", "--",
         "core/", "michi/", "audio/", "library/", "metadata/",
         "integrations/", "ui_qml_bridge/"],
        capture_output=True, text=True, cwd=repo,
    )
    for line in r.stdout.strip().split("\n"):
        if line and "object()" in line:
            errors.append(f"object(): {line}")

    # 2. lambda: None en archivos productivos
    r = subprocess.run(
        ["git", "grep", "-n", "lambda: None", "--",
         "core/", "michi/", "audio/", "library/", "metadata/",
         "integrations/", "ui_qml_bridge/", "ui_qml/"],
        capture_output=True, text=True, cwd=repo,
    )
    for line in r.stdout.strip().split("\n"):
        if line and "lambda: None" in line:
            errors.append(f"lambda: None: {line}")

    # 3. PlayerService(engine=None)
    r = subprocess.run(
        ["git", "grep", "-n", "PlayerService(engine=None)", "--", "core/"],
        capture_output=True, text=True, cwd=repo,
    )
    for line in r.stdout.strip().split("\n"):
        if line and "PlayerService" in line:
            errors.append(f"PlayerService(engine=None): {line}")

    if errors:
        print("PLACEHOLDER AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    print("PLACEHOLDER AUDIT PASSED: 0 placeholders found")


if __name__ == "__main__":
    main()
