#!/usr/bin/env python3
"""Audit V18: count ActionRegistry handlers and workflow test files."""
from __future__ import annotations
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    bp = repo / "core" / "application_bootstrap.py"
    if bp.exists():
        c = bp.read_text()
        count = c.count("ActionDescriptor(")
        if count < 50:
            errors.append(f"Only {count} ActionDescriptors (< 50)")
        else:
            print(f"  ActionDescriptors: {count} OK")
    wf = repo / "tests" / "qml" / "productive_workflows_v18"
    if wf.exists():
        files = list(wf.glob("test_*.py"))
        if len(files) < 12:
            errors.append(f"Only {len(files)} workflow tests (< 12)")
        else:
            print(f"  Workflow tests: {len(files)} OK")
    if errors:
        print("V18 FUNCTION AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("V18 FUNCTION AUDIT PASSED")


if __name__ == "__main__":
    main()
