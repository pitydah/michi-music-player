#!/usr/bin/env python3
"""Audit V18: detect QtWidgets imports outside legacy_widgets in production code."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    scan_dirs = ["core/", "audio/", "library/", "streaming/", "integrations/",
                 "michi/", "metadata/", "lyrics/", "recommendation/", "ui_qml_bridge/"]
    for d in scan_dirs:
        r = subprocess.run(
            ["git", "grep", "-n", "PySide6.QtWidgets", "--", d],
            capture_output=True, text=True, cwd=repo)
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            errors.append(line.strip()[:120])
    if errors:
        print("V18 WIDGET DEPENDENCY AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("V18 WIDGET DEPENDENCY AUDIT PASSED: 0 QtWidgets in production")


if __name__ == "__main__":
    main()
