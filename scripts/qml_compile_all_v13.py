#!/usr/bin/env python3
"""Compile-check all QML and bridge Python files for V13."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    dirs = ["core", "audio", "library", "ui_qml_bridge", "streaming",
            "integrations", "recommendation", "lyrics", "metadata",
            "ui_qml"]
    errors = []
    for d in dirs:
        target = repo / d
        if not target.exists():
            continue
        result = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", str(target)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            errors.append(f"{d}: compile errors")
            for line in result.stderr.split("\n"):
                if line.strip():
                    errors.append(f"  {line.strip()}")

    if errors:
        print("COMPILE FAILURES:")
        for e in errors:
            print(e)
        sys.exit(1)
    print("All V13 modules compile OK")


if __name__ == "__main__":
    main()
