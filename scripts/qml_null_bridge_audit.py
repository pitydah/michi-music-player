#!/usr/bin/env python3
"""Audit: verify NullBridge is NOT used anywhere in tests."""
from __future__ import annotations
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    for f in (repo / "tests").rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        content = f.read_text()
        if "NullBridge" in content:
            errors.append(f"{f.relative_to(repo)}")
    if errors:
        print("NULL BRIDGE AUDIT FAILED — NullBridge found in:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("NULL BRIDGE AUDIT PASSED: 0 occurrences")


if __name__ == "__main__":
    main()
