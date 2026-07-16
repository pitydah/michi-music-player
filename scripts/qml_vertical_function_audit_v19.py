#!/usr/bin/env python3
"""Audit V19: count ActionRegistry handlers and workflow tests."""
from __future__ import annotations
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    bp = repo / "core" / "application_bootstrap.py"
    if bp.exists():
        count = bp.read_text().count("ActionDescriptor(")
        if count < 55:
            errors.append(f"Only {count} ActionDescriptors (< 55)")
        else:
            print(f"  ActionDescriptors: {count} OK")
    wf = repo / "tests" / "qml" / "productive_workflows_v19"
    if wf.exists():
        files = list(wf.glob("test_*.py"))
        if len(files) < 15:
            errors.append(f"Only {len(files)} workflow tests (< 15)")
        else:
            print(f"  Workflow tests: {len(files)} OK")
    if errors:
        print("FUNCTION AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("FUNCTION AUDIT PASSED")


if __name__ == "__main__":
    main()
