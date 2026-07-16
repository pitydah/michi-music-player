#!/usr/bin/env python3
"""Audit V19: verify no business logic remains in ui/."""
from __future__ import annotations
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    for f in (repo / "ui").rglob("*.py"):
        if "legacy" in str(f) or "__pycache__" in str(f):
            continue
        content = f.read_text()
        if len(content) > 100:
            errors.append(f"{f.relative_to(repo)}: {len(content)} chars")
    if errors:
        print("LEGACY BUSINESS LOGIC AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("LEGACY BUSINESS LOGIC AUDIT PASSED: ui/ is clean")


if __name__ == "__main__":
    main()
