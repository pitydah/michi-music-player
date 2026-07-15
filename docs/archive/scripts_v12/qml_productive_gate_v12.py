#!/usr/bin/env python3
"""QML Productive Gate V12 — real pytest exit code, no stdout keyword search,
no Devices/Connections/HomeAudio exclusion. Fails if any module score < 100.
"""
import json
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
    print("# QML Productive Gate V12\n")

    # Python compile — full repo
    r = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "-x", r"\.venv/|\.tmpl\.", "."],
        capture_output=True, text=True, cwd=REPO,
    )
    check(r.returncode == 0, f"Python compile errors: rc={r.returncode}")

    # Ruff — full repo
    r = subprocess.run(
        ["ruff", "check", ".", "--output-format", "concise"],
        capture_output=True, text=True, cwd=REPO,
    )
    check(r.returncode == 0, f"Ruff errors: rc={r.returncode}")

    # QML compile — all files
    r = subprocess.run(
        [sys.executable, "scripts/qml_compile_all_v12.py"],
        capture_output=True, text=True, timeout=120, cwd=REPO,
    )
    check(r.returncode == 0, "QML compile all failed")

    # QML instance — all files
    r = subprocess.run(
        [sys.executable, "scripts/qml_instance_all_v11.py"],
        capture_output=True, text=True, timeout=120, cwd=REPO,
    )
    check(r.returncode == 0, "QML instance all failed")

    # Core imports ui — no ui/ references in core/
    ui_imports = []
    for f in sorted((REPO / "core").rglob("*.py")):
        for line in f.read_text().split("\n"):
            stripped = line.strip()
            if ("import ui" in stripped or "from ui" in stripped) and "ui_qml" not in stripped:
                ui_imports.append(f"{f.relative_to(REPO)}: {stripped}")
    check(len(ui_imports) == 0, f"Core imports ui: {len(ui_imports)}")

    # QML imports QtWidgets
    widget_imports = []
    for f in sorted((REPO / "ui_qml").rglob("*.qml")):
        if "QtWidgets" in f.read_text():
            widget_imports.append(str(f.relative_to(REPO)))
    check(len(widget_imports) == 0, f"QML imports QtWidgets: {widget_imports}")

    # Bridge imports QWidget
    bridge_widgets = []
    for f in sorted((REPO / "ui_qml_bridge").rglob("*.py")):
        if "QWidget" in f.read_text():
            bridge_widgets.append(str(f.relative_to(REPO)))
    check(len(bridge_widgets) == 0, f"Bridge imports QWidget: {bridge_widgets}")

    # Baseline exists
    baseline = REPO / "docs" / "migration" / "X10_V2_PRODUCTIVE_BASELINE.yaml"
    check(baseline.exists(), "Baseline X10_V2_PRODUCTIVE_BASELINE.yaml not found")

    # Evidence V12 exists and all modules score 100
    evidence_path = REPO / "artifacts" / "qml-evidence-v12.json"
    check(evidence_path.exists(), "Evidence V12 not found (run collect first)")
    if evidence_path.exists():
        evidence = json.loads(evidence_path.read_text())
        area_scores = evidence.get("area_scores", {})
        modules = evidence.get("modules", {})
        # All module scores must be 100
        non_100 = {m: s["score"] for m, s in modules.items() if s["score"] < 100}
        check(len(non_100) == 0, f"Modules with score < 100: {non_100}")
        # No area with score < 100
        non_100_areas = {a: s for a, s in area_scores.items() if s < 100}
        check(len(non_100_areas) == 0, f"Areas with score < 100: {non_100_areas}")

    # Real pytest exit code — ALL QML tests, no exclusions
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/qml", "-q", "--timeout=300"],
        capture_output=True, text=True, timeout=600, cwd=REPO,
    )
    # Check returncode directly — no keyword search in stdout
    check(r.returncode == 0, f"Real pytest exit code {r.returncode} (must be 0)")

    print(f"\n{'='*60}")
    if not ERRORS:
        print("GATE: PASSED — Productive V12 ready")
        return 0
    else:
        print(f"GATE: FAILED — {len(ERRORS)} condition(s) not met")
        return 1


if __name__ == "__main__":
    sys.exit(main())
