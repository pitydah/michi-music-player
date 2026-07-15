#!/usr/bin/env python3
"""QML 100% Migration Gate — fails if any condition is not met."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ERRORS = []


def check(condition: bool, msg: str):
    if not condition:
        ERRORS.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  PASS: {msg}")


def main():
    print("# QML 100% Migration Gate\n")

    # Ruff
    r = subprocess.run(["ruff", "check", ".", "--output-format", "concise"], capture_output=True, text=True, cwd=REPO)
    check(r.returncode == 0, f"Ruff failures = {r.returncode}")

    # Compileall
    r = subprocess.run([sys.executable, "-m", "compileall", "-q", "-x", r"\.venv/|\.tmpl\.", "."], capture_output=True, text=True, cwd=REPO)
    check(r.returncode == 0, f"Compile errors (exit {r.returncode})")

    # QML imports Widgets
    imports = []
    for f in sorted((REPO / "ui_qml_bridge").rglob("*.py")):
        content = f.read_text()
        if "PySide6.QtWidgets" in content or "from PySide6 import QtWidgets" in content:
            imports.append(str(f.relative_to(REPO)))
    for f in sorted((REPO / "ui_qml").rglob("*.qml")):
        content = f.read_text()
        if "import" in content and "QtWidgets" in content:
            imports.append(str(f.relative_to(REPO)))
    check(len(imports) == 0, f"QML imports QtWidgets: {imports}")

    # Core imports ui
    ui_imports = []
    for f in sorted((REPO / "core").rglob("*.py")):
        content = f.read_text()
        for line in content.split("\n"):
            if "import ui" in line or "from ui" in line:
                if "ui_qml" not in line and "ui." in line:
                    ui_imports.append(f"{f.relative_to(REPO)}: {line.strip()}")
    check(len(ui_imports) == 0, f"Core imports ui: {len(ui_imports)}")

    # Bridge imports QWidget
    bridge_imports = []
    for f in sorted((REPO / "ui_qml_bridge").rglob("*.py")):
        content = f.read_text()
        if "QWidget" in content or "QDialog" in content:
            bridge_imports.append(str(f.relative_to(REPO)))
    check(len(bridge_imports) == 0, f"Bridge imports QWidget: {bridge_imports}")

    # Duplicate canonical services
    for name in ("ServiceContainer", "ServiceBundle", "ServiceRegistry", "JobService", "ActionRegistry", "SelectionController", "QueueService"):
        count = 0
        for f in sorted((REPO / "core").rglob("*.py")):
            if f"class {name}" in f.read_text():
                count += 1
        check(count <= 1, f"Duplicate {name}: {count}")

    # QML routes opening Widgets
    routes_path = REPO / "ui_qml_bridge" / "route_registry.py"
    if routes_path.exists():
        content = routes_path.read_text()
        check("widget" not in content.lower() and "legacy" not in content.lower(), "Routes reference Widget/legacy pages")

    # ServiceContainer unique
    sc_count = 0
    for f in sorted((REPO / "core").rglob("*.py")):
        if "class ServiceContainer" in f.read_text() or "ServiceRegistry as ServiceContainer" in f.read_text():
            sc_count += 1
    check(sc_count <= 1, f"ServiceContainer instances: {sc_count}")

    # BridgeFactory no service creation
    bf_path = REPO / "ui_qml_bridge" / "bridge_factory.py"
    if bf_path.exists():
        content = bf_path.read_text()
        forbidden = ["_get_", "_service_cache", "from core."]
        violations = [f for f in forbidden if f in content]
        check(len(violations) == 0, f"BridgeFactory caches: {violations}")

    # Score matrix
    matrix_path = REPO / "docs" / "integration" / "QML_100_PERCENT_MATRIX.yaml"
    check(matrix_path.exists(), "100% matrix not found")

    print(f"\n{'='*60}")
    if not ERRORS:
        print("GATE: PASSED — 100% migration ready")
        return 0
    else:
        print(f"GATE: FAILED — {len(ERRORS)} condition(s) not met")
        return 1


if __name__ == "__main__":
    exit(main())
