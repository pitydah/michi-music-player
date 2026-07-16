#!/usr/bin/env python3
"""Audit V18: no FakeBridge or MagicMock engine in productive workflows."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    for wf in ["productive_workflows_v18", "productive_workflows_v17",
               "productive_workflows_v16", "productive_workflows_v15"]:
        wd = repo / "tests" / "qml" / wf
        if not wd.exists():
            continue
        r = subprocess.run(
            ["git", "grep", "-n", "Fake.*Bridge\\|MagicMock", "--", str(wd)],
            capture_output=True, text=True, cwd=repo)
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            if "FakeAudioBackend" in line or "FakeNetworkTransport" in line:
                continue
            errors.append(line.strip()[:120])
    if errors:
        print("V18 FAKE BRIDGE AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("V18 FAKE BRIDGE AUDIT PASSED")


if __name__ == "__main__":
    main()
