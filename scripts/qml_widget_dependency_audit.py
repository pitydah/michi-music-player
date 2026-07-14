#!/usr/bin/env python3
"""qml_widget_dependency_audit.py — checks QtWidgets imports in ui/ and core/."""
import ast
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UI_DIR = REPO / "ui"
CORE_DIR = REPO / "core"

QT_WIDGET_CLASSES = {
    "QWidget", "QDialog", "QMainWindow", "QFrame", "QStackedWidget",
    "QTableView", "QListView", "QTreeView", "QPushButton",
    "QLabel", "QLineEdit", "QTextEdit", "QComboBox", "QCheckBox",
    "QRadioButton", "QSlider", "QProgressBar", "QTabWidget",
    "QGroupBox", "QScrollArea", "QSplitter", "QToolBar",
    "QStatusBar", "QMenuBar", "QMenu", "QAction", "QToolButton",
    "QVBoxLayout", "QHBoxLayout", "QGridLayout", "QFormLayout",
    "QFileDialog", "QMessageBox", "QColorDialog", "QFontDialog",
    "QInputDialog", "QProgressDialog",
}


def check_file(path: Path) -> dict:
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return {"widget_imports": [], "widget_classes": [], "error": "syntax"}
    widget_imports = []
    widget_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "PySide6.QtWidgets" in alias.name or "PyQt6.QtWidgets" in alias.name:
                    widget_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and ("QtWidgets" in node.module):
                for alias in (node.names or []):
                    widget_imports.append(f"{node.module}.{alias.name}")
            if node.module and ("PySide6" in node.module or "PyQt6" in node.module):
                for alias in (node.names or []):
                    if alias.name in QT_WIDGET_CLASSES:
                        widget_classes.append(alias.name)
    return {"widget_imports": widget_imports, "widget_classes": widget_classes}


def main() -> int:
    ALLOWED_CORE = {"core/file_actions.py", "core/playback_controller.py"}
    results = defaultdict(list)
    for d, label in [(UI_DIR, "ui"), (CORE_DIR, "core")]:
        for f in sorted(d.rglob("*.py")):
            if f.name.startswith("__"):
                continue
            r = check_file(f)
            if r["widget_imports"] or r["widget_classes"]:
                allowed = label == "core" and str(f.relative_to(REPO)) in ALLOWED_CORE
                results[label].append({
                    "file": str(f.relative_to(REPO)),
                    "imports": r["widget_imports"],
                    "classes": r["widget_classes"],
                    "allowed": allowed,
                })

    ui_refs = len(results.get("ui", []))
    core_refs = len(results.get("core", []))
    print(f"Widget audit: {ui_refs} ui/ files, {core_refs} core/ files with QtWidgets refs")
    for label in ("core",):
        for item in results.get(label, []):
            print(f"  core/: {item['file']} imports {item['imports']} uses {item['classes']}")

    actually_violating = [r for r in results.get("core", []) if not r.get("allowed")]
    core_refs_violating = len(actually_violating)
    core_pass = core_refs_violating == 0
    print(f"\nCore widget dependency: {'PASS' if core_pass else 'FAIL'} ({core_refs_violating} violating, {core_refs} total)")
    return 0 if core_pass else 1


if __name__ == "__main__":
    sys.exit(main())
