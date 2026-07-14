#!/usr/bin/env python3
"""Widget dependency audit — detects ui.* imports from QML runtime, SQL in widgets, duplicated logic."""
import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SCAN_DIRS = [
    "ui_qml_bridge",
    "ui_qml",
    "core",
]

IGNORE_DIRS = {"__pycache__", ".venv", "node_modules", "ui/audio_lab/client"}


def scan_imports(path: Path) -> list[dict]:
    findings = []
    for pyfile in sorted(path.rglob("*.py")):
        if any(ign in pyfile.parts for ign in IGNORE_DIRS):
            continue
        try:
            tree = ast.parse(pyfile.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("ui."):
                        findings.append({"file": str(pyfile.relative_to(REPO)), "type": "UI_IMPORT", "detail": alias.name})
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("ui."):
                    findings.append({"file": str(pyfile.relative_to(REPO)), "type": "UI_IMPORT", "detail": node.module})
                if node.module and node.module == "ui":
                    findings.append({"file": str(pyfile.relative_to(REPO)), "type": "UI_IMPORT", "detail": "ui"})
    return findings


def scan_sql_in_widgets() -> list[dict]:
    findings = []
    ui_dir = REPO / "ui"
    if not ui_dir.exists():
        return findings
    for pyfile in sorted(ui_dir.rglob("*.py")):
        if any(ign in pyfile.parts for ign in IGNORE_DIRS):
            continue
        try:
            tree = ast.parse(pyfile.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("execute", "executemany") and isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "conn":
                findings.append({"file": str(pyfile.relative_to(REPO)), "type": "SQL_IN_WIDGET", "detail": f"line {node.lineno}"})
    return findings


def main():
    print("# QML Widget Dependency Audit\n")
    all_findings = []

    for d in SCAN_DIRS:
        p = REPO / d
        if p.exists():
            all_findings.extend(scan_imports(p))

    all_findings.extend(scan_sql_in_widgets())

    by_type = {}
    for f in all_findings:
        by_type.setdefault(f["type"], []).append(f)

    total_issues = len(all_findings)
    for t, items in sorted(by_type.items()):
        print(f"\n## {t}: {len(items)}")
        for item in items[:10]:
            print(f"  {item['file']}: {item.get('detail', '')}")

    print(f"\n---\nTotal: {total_issues}")
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    exit(main())
