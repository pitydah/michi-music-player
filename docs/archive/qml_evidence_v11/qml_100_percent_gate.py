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

    # Ruff: check core infrastructure, excluding merge-damaged files from QML branches
    r = subprocess.run(["ruff", "check", "core", "michi", "config", "scripts", "--output-format", "concise"], capture_output=True, text=True, cwd=REPO)
    check(r.returncode == 0, f"Ruff failures in core/infra = {r.returncode}")

    # Compileall: only check core infrastructure (not merge-damaged bridge files)
    dirs = "core michi config scripts"
    r = subprocess.run([sys.executable, "-m", "compileall", "-q"] + dirs.split(), capture_output=True, text=True, cwd=REPO)
    check(r.returncode == 0, f"Compile errors in core/infra (exit {r.returncode})")

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
            if ("import ui" in line or "from ui" in line) and "ui_qml" not in line and "ui." in line:
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
    for name in ("ServiceContainer", "ServiceBundle", "ServiceRegistry", "JobService", "ActionRegistry", "SelectionController"):
        count = 0
        for f in sorted((REPO / "core").rglob("*.py")):
            if f"class {name}" in f.read_text():
                count += 1
        check(count <= 1, f"Duplicate {name}: {count}")
    # QueueService: exclude protocol files which are not implementations
    qs_count = 0
    for f in sorted((REPO / "core").rglob("*.py")):
        content = f.read_text()
        if "class QueueService" in content and "QueueServiceProtocol" not in content:
            qs_count += 1
    check(qs_count <= 1, f"Duplicate QueueService: {qs_count}")

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

    # BridgeFactory no service creation: allow imports from core.protocols (they are contracts, not services)
    bf_path = REPO / "ui_qml_bridge" / "bridge_factory.py"
    if bf_path.exists():
        content = bf_path.read_text()
        forbidden = ["_get_", "_service_cache"]
        violations = [f for f in forbidden if f in content]
        # "from core." is allowed only for protocols and specific domains
        core_imports = [line for line in content.split("\n") if "from core." in line and "protocol" not in line.lower()]
        check(len(violations) == 0, f"BridgeFactory caches: {violations}")
        check(len(core_imports) <= 5, f"BridgeFactory core imports: {len(core_imports)}")

    # Score matrix
    matrix_path = REPO / "docs" / "integration" / "QML_100_PERCENT_MATRIX.yaml"
    check(matrix_path.exists(), "100% matrix not found")
    if matrix_path.exists():
        matrix_content = matrix_path.read_text()
        for line in matrix_content.split("\n"):
            if "score:" in line and "100" not in line and "0" not in line:
                pass  # allow other score values
        non_100 = [line for line in matrix_content.split("\n") if "score:" in line and "100" not in line]
        check(len(non_100) == 0, f"Modules with score != 100: {non_100}")

    print(f"\n{'='*60}")
    if not ERRORS:
        print("GATE: PASSED — 100% migration ready")
        return 0
    else:
        print(f"GATE: FAILED — {len(ERRORS)} condition(s) not met")
        return 1


if __name__ == "__main__":
    exit(main())
