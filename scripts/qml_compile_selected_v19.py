#!/usr/bin/env python3
"""Compile-check selected V19 files."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    files = sys.argv[1:]
    if not files:
        print("Usage: qml_compile_selected_v19.py <file1> [file2...]")
        sys.exit(1)
    errors = []
    for f in files:
        fp = Path(f) if Path(f).is_absolute() else Path(__file__).parent.parent / f
        if not fp.exists():
            errors.append(f"NOT FOUND: {f}")
            continue
        r = subprocess.run([sys.executable, "-m", "compileall", "-q", str(fp)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            errors.append(f"FAIL: {f}")
            for line in r.stderr.split("\n"):
                if line.strip():
                    errors.append(f"  {line.strip()}")
    if errors:
        print("COMPILE SELECTED FAILED:")
        for e in errors:
            print(e)
        sys.exit(1)
    print("All selected files compile OK")


if __name__ == "__main__":
    main()
