#!/usr/bin/env python3
"""QML Widget Retirement Audit — verifies each W3 domain's retirement conditions:

1. QML does not import the Widget
2. Shell QML does not open the Widget
3. core does not depend on ui
4. packaging QML does not include the Widget
5. business logic in core
6. workflow QML approved

Reads canonical config/qwidget_decommission_matrix.yaml.
"""
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATRIX = REPO / "config" / "qwidget_decommission_matrix.yaml"

IGNORE_DIRS = {"__pycache__", ".venv", "node_modules"}

WIDGET_IMPORT_PATTERNS = [
    "from PySide6.QtWidgets",
    "import PySide6.QtWidgets",
    "from PySide6 import QtWidgets",
]


def load_matrix():
    try:
        import yaml
        return yaml.safe_load(MATRIX.read_text())
    except Exception as e:
        print(f"ERROR: cannot parse matrix: {e}")
        sys.exit(1)


def _check_qml_no_import_widget(domain: str) -> bool:
    """Condition 1: QML does not import the Widget."""
    for d in ("ui_qml", "ui_qml_bridge"):
        p = REPO / d
        if not p.exists():
            continue
        for pyfile in p.rglob("*.py"):
            if any(ign in pyfile.parts for ign in IGNORE_DIRS):
                continue
            try:
                tree = ast.parse(pyfile.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and (".widgets." + domain) in node.module:
                        return False
                    if node.module and node.module.startswith("ui.") and domain in node.module:
                        return False
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if domain in alias.name and ("ui" in alias.name or "widget" in alias.name):
                            return False
    return True


def _check_shell_qml_does_not_open(domain: str) -> bool:
    """Condition 2: Shell QML does not open the Widget."""
    shell_files = [
        REPO / "ui_qml" / "shell" / "AppShell.qml",
        REPO / "ui_qml" / "Main.qml",
        REPO / "ui_qml" / "MichiApp.qml",
    ]
    for sf in shell_files:
        if sf.exists():
            text = sf.read_text()
            if domain in text.lower():
                return False
    return True


def _check_core_no_ui_dep() -> bool:
    """Condition 3: core does not depend on ui."""
    core_dir = REPO / "core"
    if not core_dir.exists():
        return True
    for pyfile in core_dir.rglob("*.py"):
        if any(ign in pyfile.parts for ign in IGNORE_DIRS):
            continue
        try:
            text = pyfile.read_text()
        except Exception:
            continue
        for pattern in WIDGET_IMPORT_PATTERNS:
            if pattern in text:
                return False
        if "import ui" in text or "from ui" in text:
            return False
    return True


def _check_packaging_qml_no_widget(domain: str) -> bool:
    """Condition 4: packaging QML does not include the Widget."""
    pyproject = REPO / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text()
        if domain in text and ("widget" in text.lower() or "ui" in text.lower()):
            return False
    return True


def _check_logic_in_core(domain: str) -> bool:
    """Condition 5: business logic is in core, not ui."""
    core_hit = False
    ui_hit = False
    core_dir = REPO / "core"
    if core_dir.exists():
        for pyfile in core_dir.rglob("*.py"):
            if any(ign in pyfile.parts for ign in IGNORE_DIRS):
                continue
            text = pyfile.read_text()
            if domain in text and any(kw in text for kw in ("class ", "def ", "import ")):
                core_hit = True
                break
    ui_dir = REPO / "ui"
    if ui_dir.exists():
        for pyfile in ui_dir.rglob("*.py"):
            if any(ign in pyfile.parts for ign in IGNORE_DIRS):
                continue
            text = pyfile.read_text()
            if domain in text and any(kw in text for kw in ("class ", "def ", "import ")):
                ui_hit = True
                break
    return core_hit or not ui_hit


def _check_workflow_qml_approved(domain: str) -> bool:
    """Condition 6: workflow QML approved — check matrix field."""
    matrix = load_matrix()
    for d in matrix.get("domains", []):
        if d.get("domain") == domain:
            return d.get("workflow_passed", False)
    return False


def main():
    matrix = load_matrix()
    domains = matrix.get("domains", [])

    w3_domains = [d for d in domains if d.get("widget_status", "").startswith("W3")]
    if not w3_domains:
        print("No W3 domains found in matrix")
        return 0

    checks = [
        ("qml_no_import_widget", _check_qml_no_import_widget, "QML imports Widget"),
        ("shell_qml_no_open", _check_shell_qml_does_not_open, "Shell QML opens Widget"),
        ("core_no_ui_dep", lambda _: _check_core_no_ui_dep(), "core depends on ui"),
        ("packaging_qml_no_widget", _check_packaging_qml_no_widget, "Packaging includes Widget"),
        ("logic_in_core", _check_logic_in_core, "Logic not in core"),
        ("workflow_qml_approved", _check_workflow_qml_approved, "Workflow not approved"),
    ]

    all_pass = True

    print("# QML Widget Retirement Audit\n")

    header = f"{'Domain':25s} {'Status':10s} " + " ".join(f"{c[0]:20s}" for c in checks)
    print(header)
    print("-" * len(header))

    for d in sorted(w3_domains, key=lambda x: x.get("domain", "")):
        domain = d.get("domain", "")
        results = []
        domain_ok = True
        for _name, checker, _ in checks:
            ok = checker(domain)
            results.append(ok)
            if not ok:
                domain_ok = False

        status = "PASS" if domain_ok else "FAIL"
        if not domain_ok:
            all_pass = False

        results_str = " ".join("PASS" if r else "FAIL" for r in results)
        print(f"{domain:25s} {status:10s} {results_str}")

    w3_total = len(w3_domains)
    print(f"\nW3+ domains checked: {w3_total}")
    print(f"\nResult: {'ALL PASS' if all_pass else 'SOME FAILURES'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
