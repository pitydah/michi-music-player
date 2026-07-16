#!/usr/bin/env python3
"""Audit V19: no FakeBridge in productive workflows."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def main():
    repo = Path(__file__).parent.parent
    errors = []
    for wf in ["productive_workflows_v19", "productive_workflows_v18"]:
        wd = repo / "tests" / "qml" / wf
        if not wd.exists():
            continue
        r = subprocess.run(
            ["git", "grep", "-n", "Fake.*Bridge\\|FakeLibrary\\|FakePlayback\\|FakeQueue\\|FakeAI\\|FakeDevice\\|FakeConnection\\|FakeHomeAudio",
             "--", str(wd)], capture_output=True, text=True, cwd=repo)
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            if "FakeAudioBackend" in line or "FakeNetworkTransport" in line:
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
