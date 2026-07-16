#!/usr/bin/env python3
"""Audit: tests named 'real' or 'interactive' must NOT use MagicMock."""
from __future__ import annotations
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    patterns = ("*real*.py", "*interactive*.py")
    tests_dir = repo / "tests"
    for pattern in patterns:
        for f in tests_dir.rglob(pattern):
            if "__pycache__" in str(f):
                continue
            content = f.read_text()
            if "MagicMock" in content or "from unittest.mock" in content:
                errors.append(f"{f.relative_to(repo)}")
    if errors:
        print("REAL TEST INTEGRITY AUDIT FAILED — tests named 'real' use MagicMock:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("REAL TEST INTEGRITY AUDIT PASSED: 0 violations")


if __name__ == "__main__":
    main()
