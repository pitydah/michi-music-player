#!/usr/bin/env python3
"""Compile-check all V18 modules."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
repo = Path(__file__).parent.parent
dirs = ["core", "audio", "library", "ui_qml_bridge", "streaming",
        "integrations", "recommendation", "lyrics", "metadata", "ui_qml"]
errors = []
for d in dirs:
    target = repo / d
    if not target.exists():
        continue
    r = subprocess.run([sys.executable, "-m", "compileall", "-q", str(target)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        errors.append(d)
        for line in r.stderr.split("\n"):
            if line.strip():
                errors.append(f"  {line.strip()}")
if errors:
    print("COMPILE FAILED:", file=sys.stderr)
    for e in errors:
        print(e, file=sys.stderr)
    sys.exit(1)
print("All V18 modules compile OK")
