"""Runtime warning gate — fails when QML runtime warnings are detected.

Catches: Binding loop, ReferenceError, TypeError, Unable to assign undefined,
Accessible attached property errors, anchors on layout-managed items,
deprecated parameter injection, Error loading QML component.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAIN_QML = REPO / "ui_qml" / "Main.qml"

WARNING_PATTERNS = [
    "Binding loop detected",
    "ReferenceError",
    "TypeError",
    "Unable to assign [undefined]",
    "Accessible attached property must be attached",
    "anchors on an item managed by a layout",
    "Injection of parameters into signal handlers is deprecated",
    "_pythonToCppCopy",
    "Error loading QML component",
    "Loader.Error",
    "Cannot specify top, bottom, verticalCenter, fill or centerIn",
    "Column will not function",
    "is not a type",
    "is not a function",
]

EXPECTED_SAFE_PATTERNS = [
    "PyGIDeprecationWarning",
]


def _run_qml_runtime() -> tuple[int, str]:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MICHI_SAFE_MODE"] = "1"
    env["PYTHONPATH"] = str(REPO)
    try:
        proc = subprocess.run(
            [sys.executable, "main.py", "--qml"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(REPO),
            env=env,
        )
        return proc.returncode, proc.stderr + proc.stdout
    except subprocess.TimeoutExpired as exc:
        output = ""
        if exc.stderr:
            output += exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr
        if exc.stdout:
            output += exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout
        return -1, output


class TestRuntimeWarningGate:
    def test_qml_loads_without_warnings(self):
        rc, output = _run_qml_runtime()
        lines = output.splitlines()
        violations: list[str] = []
        for line in lines:
            for pattern in WARNING_PATTERNS:
                if pattern.lower() in line.lower():
                    if not any(safe in line for safe in EXPECTED_SAFE_PATTERNS):
                        violations.append(line.strip())
        assert violations == [], (
            f"Runtime warnings detected ({len(violations)}):\n"
            + "\n".join(violations[:20])
        )

    def test_qml_reaches_ready_state(self):
        rc, output = _run_qml_runtime()
        assert "READY" in output, f"QML did not reach READY state. Output:\n{output}"

    def test_qml_no_traceback(self):
        rc, output = _run_qml_runtime()
        assert "Traceback" not in output, f"Python traceback detected:\n{output}"

    def test_qml_no_shutdown_error(self):
        rc, output = _run_qml_runtime()
        assert "_pythonToCppCopy" not in output, (
            "_pythonToCppCopy error during shutdown:\n" + output
        )
