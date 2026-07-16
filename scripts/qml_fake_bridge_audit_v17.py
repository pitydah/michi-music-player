#!/usr/bin/env python3
"""Audit: no FakeBridge or MagicMock engine in productive workflows."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    wf_paths = ["tests/qml/productive_workflows_v17", "tests/qml/productive_workflows_v16",
                "tests/qml/productive_workflows_v15"]
    for wf in wf_paths:
        wd = repo / wf
        if not wd.exists():
            continue
        r = subprocess.run(
            ["git", "grep", "-n", "Fake.*Bridge\\|MagicMock", "--", wf + "/"],
            capture_output=True, text=True, cwd=repo)
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            if "FakeAudioBackend" in line or "FakeNetworkTransport" in line:
                continue
            if "MagicMock" in line and "QQmlApplicationEngine" not in line:
                continue
            errors.append(line.strip()[:120])
    if errors:
        print("FAKE BRIDGE AUDIT FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("FAKE BRIDGE AUDIT PASSED")


if __name__ == "__main__":
    main()
