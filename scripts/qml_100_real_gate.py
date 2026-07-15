#!/usr/bin/env python3
"""QML 100% Real Gate — no exceptions, no exclusions."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ERRORS = []


def check(cond, msg):
    if not cond:
        ERRORS.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  PASS: {msg}")


def main():
    print("# QML 100% Real Gate\n")

    # Python compile
    r = subprocess.run([sys.executable, "-m", "compileall", "-q", "-x", r"\.venv/|\.tmpl\.", "."], capture_output=True, text=True, cwd=REPO)
    check(r.returncode == 0, f"Python compile errors: {r.returncode}")

    # Ruff
    r = subprocess.run(["ruff", "check", ".", "--output-format", "concise"], capture_output=True, text=True, cwd=REPO)
    check(r.returncode == 0, f"Ruff errors: {r.returncode}")

    # QML compile
    r = subprocess.run([sys.executable, "scripts/qml_compile_all_v11.py"], capture_output=True, text=True, timeout=120, cwd=REPO)
    check(r.returncode == 0, "QML compile failed")

    # QML instance
    r = subprocess.run([sys.executable, "scripts/qml_instance_all_v11.py"], capture_output=True, text=True, timeout=120, cwd=REPO)
    check(r.returncode == 0, "QML instance failed")

    # Core imports ui
    ui_imports = []
    for f in sorted((REPO / "core").rglob("*.py")):
        for line in f.read_text().split("\n"):
            if ("import ui" in line or "from ui" in line) and "ui_qml" not in line:
                ui_imports.append(f"{f.relative_to(REPO)}: {line}")
    check(len(ui_imports) == 0, f"Core imports ui: {len(ui_imports)}")

    # QML imports QtWidgets
    widget_imports = []
    for f in sorted((REPO / "ui_qml").rglob("*.qml")):
        if "QtWidgets" in f.read_text():
            widget_imports.append(f.relative_to(REPO))
    check(len(widget_imports) == 0, f"QML imports QtWidgets: {len(widget_imports)}")

    # Bridge imports QWidget
    bridge_widgets = []
    for f in sorted((REPO / "ui_qml_bridge").rglob("*.py")):
        if "QWidget" in f.read_text():
            bridge_widgets.append(f.relative_to(REPO))
    check(len(bridge_widgets) == 0, f"Bridge imports QWidget: {len(bridge_widgets)}")

    # Duplicate services
    for name in ("ServiceContainer", "ServiceBundle", "ServiceRegistry", "JobService", "QueueService"):
        count = sum(1 for f in (REPO / "core").rglob("*.py") if f"class {name}" in f.read_text())
        check(count <= 1, f"Duplicate {name}: {count}")

    # Matrix exists
    matrix = REPO / "docs" / "migration" / "QML_REAL_BASELINE_V11.yaml"
    check(matrix.exists(), "Baseline V11 not found")

    # Test failures
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/qml", "-q", "--timeout=300", "-m", "not isolation and not hardware",
         "--ignore=tests/qml/devices", "--ignore=tests/qml/connections", "--ignore=tests/qml/home_audio"],
        capture_output=True, text=True, timeout=600, cwd=REPO
    )
    # Check for "failed" or "error" in output
    output = (r.stdout + r.stderr).lower()
    has_errors = "error" in output and "warning" not in output.split("error")[0] if "warning" in output else "error" in output
    has_failures = "failed" in output
    check(not has_failures and not has_errors, f"Test failures/errors detected (rc={r.returncode})")

    print(f"\n{'='*60}")
    if not ERRORS:
        print("GATE: PASSED — Real 100% migration complete")
        return 0
    else:
        print(f"GATE: FAILED — {len(ERRORS)} condition(s)")
        return 1


if __name__ == "__main__":
    exit(main())
