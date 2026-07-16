#!/usr/bin/env python3
"""Audit V18: verify all ActionRegistry handlers are real (no lambda, no None)."""
from __future__ import annotations
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    bp = repo / "core" / "application_bootstrap.py"
    if not bp.exists():
        print("FAIL: bootstrap not found")
        sys.exit(1)
    content = bp.read_text()
    errors = []
    if "lambda: None" in content:
        errors.append("lambda: None handlers found")
    if "handler=None" in content:
        errors.append("handler=None found")
    count = content.count("ActionDescriptor(")
    if count < 50:
        errors.append(f"Only {count} ActionDescriptors (< 50)")
    if errors:
        print("ACTION HANDLER AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print(f"ACTION HANDLER AUDIT PASSED: {count} handlers OK")


if __name__ == "__main__":
    main()
