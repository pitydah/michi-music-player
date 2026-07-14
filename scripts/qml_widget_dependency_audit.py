#!/usr/bin/env python3
"""QML Widget Dependency Audit — Fase 3 CS/CT.

Detects:
- imports of ui.* from QML runtime (qml_main.py, bridges, context_bindings)
- imports of ui.* from core
- SQL within QWidget pages
- Business rules in QWidget (logic not in core/)
- Duplications QML/Widgets
"""
import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

WIDGET_DIRS = ["ui"]
QML_BRIDGE_DIRS = ["ui_qml_bridge"]
CORE_DIRS = ["core"]
QML_DIRS = ["ui_qml"]

UI_PATTERN = re.compile(r"from\s+ui\.|\bimport ui\.")


def _py_files(directory: str) -> list[Path]:
    result = []
    d = REPO / directory
    if d.exists():
        result.extend(d.rglob("*.py"))
    return result


def _qml_files(directory: str) -> list[Path]:
    result = []
    d = REPO / directory
    if d.exists():
        result.extend(d.rglob("*.qml"))
    return result


def scan_ui_imports_from_qml_runtime() -> list[dict]:
    findings = []
    files = _py_files("ui_qml_bridge")
    for fp in files:
        rel = fp.relative_to(REPO)
        text = fp.read_text()
        if UI_PATTERN.search(text):
            for line in text.splitlines():
                if UI_PATTERN.search(line):
                    findings.append({"file": str(rel), "line": line.strip(), "type": "ui_import_from_qml_runtime"})
    return findings


def scan_ui_imports_from_core() -> list[dict]:
    findings = []
    files = _py_files("core")
    for fp in files:
        rel = fp.relative_to(REPO)
        text = fp.read_text()
        if UI_PATTERN.search(text):
            for line in text.splitlines():
                if UI_PATTERN.search(line):
                    findings.append({"file": str(rel), "line": line.strip(), "type": "ui_import_from_core"})
    return findings


SQL_PATTERNS = [
    re.compile(r"execute\(.*SELECT", re.IGNORECASE),
    re.compile(r"execute\(.*INSERT", re.IGNORECASE),
    re.compile(r"execute\(.*UPDATE", re.IGNORECASE),
    re.compile(r"execute\(.*DELETE", re.IGNORECASE),
    re.compile(r"\.execute\(\s*['\"]\s*SELECT", re.IGNORECASE),
    re.compile(r"\.execute\(\s*['\"]\s*INSERT", re.IGNORECASE),
    re.compile(r"\.execute\(\s*['\"]\s*UPDATE", re.IGNORECASE),
    re.compile(r"\.execute\(\s*['\"]\s*DELETE", re.IGNORECASE),
    re.compile(r"cursor\(\)\.execute", re.IGNORECASE),
    re.compile(r"conn\.execute", re.IGNORECASE),
    re.compile(r"db\.execute", re.IGNORECASE),
]


def scan_sql_in_widgets() -> list[dict]:
    findings = []
    for wp in _py_files("ui"):
        rel = wp.relative_to(REPO)
        text = wp.read_text()
        for pattern in SQL_PATTERNS:
            match = pattern.search(text)
            if match:
                line_num = text[:match.start()].count("\n") + 1
                findings.append({"file": str(rel), "line": line_num, "match": match.group()[:80], "type": "sql_in_widget"})
                break
    return findings


def scan_business_rules_in_widgets() -> list[dict]:
    findings = []
    service_words = {"Service", "Manager", "Repository", "Engine", "Controller"}
    core_path = REPO / "core"
    core_classes = set()
    if core_path.exists():
        for cf in core_path.rglob("*.py"):
            text = cf.read_text()
            for match in re.finditer(r"class\s+(\w+)(?:\(.*?\))?:", text):
                core_classes.add(match.group(1))

    for wp in _py_files("ui"):
        rel = wp.relative_to(REPO)
        text = wp.read_text()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                w in node.name for w in service_words if len(w) > 5
            ) and node.name not in core_classes:
                    findings.append({
                        "file": str(rel),
                        "function": node.name,
                        "line": node.lineno,
                        "type": "business_rule_in_widget",
                    })
    return findings


def scan_qml_duplications() -> list[dict]:
    findings = []
    widget_files = {p.relative_to(REPO).name.replace(".py", "") for p in _py_files("ui")}
    qml_files = {p.relative_to(REPO).name.replace(".qml", "").replace(".py", "") for p in _py_files("ui_qml")}
    qml_files.update(p.relative_to(REPO).name.replace(".qml", "").replace(".py", "") for p in _qml_files("ui_qml"))
    common = widget_files & qml_files
    for name in sorted(common):
        findings.append({"name": name, "type": "qml_widget_duplicate"})
    return findings


def clean_findings(findings: list[dict]) -> list[dict]:
    """Deduplicate findings by (file, type, line)."""
    seen = set()
    result = []
    for f in findings:
        key = (f.get("file", ""), f.get("type", ""), str(f.get("line", "")))
        if key not in seen:
            seen.add(key)
            result.append(f)
    return result


def scan_all() -> dict:
    results = {}

    results["ui_imports_from_qml_runtime"] = scan_ui_imports_from_qml_runtime()
    results["ui_imports_from_core"] = scan_ui_imports_from_core()
    results["sql_in_widgets"] = scan_sql_in_widgets()
    results["business_rules_in_widgets"] = scan_business_rules_in_widgets()
    results["qml_duplications"] = scan_qml_duplications()

    for key in results:
        results[key] = clean_findings(results[key])

    total = sum(len(v) for v in results.values())
    results["_total_findings"] = total
    results["_passed"] = total == 0
    return results


def print_results(results: dict):
    print("=" * 78)
    print("  QML Widget Dependency Audit — Results")
    print("=" * 78)
    categories = [
        ("ui_imports_from_qml_runtime", "ui.* imports from QML runtime"),
        ("ui_imports_from_core", "ui.* imports from core"),
        ("sql_in_widgets", "SQL in QWidget pages"),
        ("business_rules_in_widgets", "Business rules in QWidget (not in core/)"),
        ("qml_duplications", "QML/Widget name duplications"),
    ]
    for key, label in categories:
        items = results.get(key, [])
        print(f"\n  [{label}] — {len(items)} finding(s)")
        for item in items[:10]:
            fname = item.get("file", "")
            line_val = item.get("line", "")
            func = item.get("function", "")
            match = item.get("match", "")
            dname = item.get("name", "")
            if func:
                print(f"    {fname}:{line_val}  {func}")
            elif match:
                print(f"    {fname}:{line_val}  {match}")
            elif dname:
                print(f"    {dname}")
            else:
                print(f"    {fname}  {line_val}")
        if len(items) > 10:
            print(f"    ... and {len(items) - 10} more")

    print(f"\n  Total findings: {results.get('_total_findings', 0)}")
    print(f"  Gate: {'PASSED' if results.get('_passed') else 'NEEDS REVIEW'}")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="QML Widget Dependency Audit")
    parser.add_argument("--output", type=str, help="Output JSON path")
    args = parser.parse_args()

    results = scan_all()
    print_results(results)

    if args.output:
        import json
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2, default=str))
        print(f"Written to {out}")

    return 0 if results.get("_passed") else 1


if __name__ == "__main__":
    sys.exit(main())
