#!/usr/bin/env python3
"""QML Evidence Collector V4 — collect real evidence from codebase, tests, and artifacts."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
        ).stdout.strip()
    except Exception:
        return "unknown"


def test_counts() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            capture_output=True, text=True, cwd=REPO, timeout=60,
        )
        count = 0
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.endswith("selected items:"):
                count = int(line.split()[-2])
                break
        return {"count": count, "raw": result.stdout[-300:]}
    except Exception as e:
        return {"count": 0, "error": str(e)}


def ruff_check() -> dict:
    try:
        result = subprocess.run(
            ["ruff", "check", ".", "--output-format", "concise"],
            capture_output=True, text=True, cwd=REPO, timeout=60,
        )
        return {"ok": result.returncode == 0, "errors": len(result.stdout.splitlines()) if result.stdout else 0, "output": result.stdout[-500:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def compile_check() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "-x", r"\.venv/|\.tmpl\."],
            capture_output=True, text=True, cwd=REPO, timeout=60,
        )
        return {"ok": result.returncode == 0, "stderr": result.stderr[-300:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def qml_test_results() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/qml/", "-q"],
            capture_output=True, text=True, cwd=REPO,
            timeout=120, env={**dict(sorted(subprocess.os.environ.items())),
                             "QT_QPA_PLATFORM": "offscreen", "MICHI_SAFE_MODE": "1"},
        )
        passed = failed = 0
        for line in result.stdout.splitlines():
            if "passed" in line and "failed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed":
                        passed = int(parts[i - 1])
                    elif p == "failed":
                        failed = int(parts[i - 1])
                break
        return {"ok": result.returncode == 0, "passed": passed, "failed": failed, "output": result.stdout[-300:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bridge_files() -> list[dict]:
    bridges = []
    for f in sorted((REPO / "ui_qml_bridge").rglob("*.py")):
        if f.name.startswith("__"):
            continue
        content = f.read_text()
        slots = sum(1 for line in content.splitlines() if "@Slot" in line)
        signals = sum(1 for line in content.splitlines() if "Signal(" in line)
        bridges.append({
            "file": str(f.relative_to(REPO)),
            "lines": len(content.splitlines()),
            "slots": slots,
            "signals": signals,
        })
    return bridges


def qml_pages() -> list[str]:
    pages = []
    for f in sorted((REPO / "ui_qml/pages").rglob("*.qml")):
        pages.append(str(f.relative_to(REPO)))
    return pages


def perf_test_files() -> list[str]:
    files = []
    for f in sorted((REPO / "tests/perf").rglob("test_*.py")):
        files.append(str(f.relative_to(REPO)))
    return files


def main():
    evidence = {
        "sha": git_sha(),
        "branch": subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=REPO,
        ).stdout.strip(),
        "test_collection": test_counts(),
        "ruff": ruff_check(),
        "compileall": compile_check(),
        "qml_tests": qml_test_results(),
        "bridge_files": bridge_files(),
        "qml_pages": qml_pages(),
        "perf_test_files": perf_test_files(),
        "artifacts": [str(f.relative_to(REPO)) for f in sorted(ARTIFACTS.glob("*"))],
    }

    outpath = ARTIFACTS / "qml_evidence_v4.json"
    outpath.write_text(json.dumps(evidence, indent=2, default=str))
    print(f"Evidence written to {outpath}")
    print(f"SHA: {evidence['sha']}")
    print(f"Tests: {evidence['test_collection']['count']}")
    print(f"Ruff: {'OK' if evidence['ruff'].get('ok') else 'FAILED'}")
    print(f"QML tests: {evidence['qml_tests'].get('passed', 0)} passed, {evidence['qml_tests'].get('failed', 0)} failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
