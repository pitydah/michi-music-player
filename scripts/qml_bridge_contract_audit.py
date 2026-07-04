#!/usr/bin/env python3
"""Audit QML bridges for contract issues."""
import ast
import sys
from pathlib import Path

BRIDGE_DIR = Path(__file__).resolve().parent.parent / "ui_qml_bridge"
WARNINGS = []
EXCLUDED_FILES = {"__init__.py", "qml_main.py", "route_registry.py"}
REFRESH_EXEMPT = {
    "app_bridge.py",
    "command_bus.py",
    "command_palette_bridge.py",
    "cover_bridge.py",
    "navigation_bridge.py",
    "notification_bridge.py",
    "playback_bridge.py",
    "route_registry_bridge.py",
    "selection_context_bridge.py",
    "theme_bridge.py",
}


def check_file(path: Path):
    name = path.name
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError as e:
        WARNINGS.append((name, "SYNTAX_ERROR", str(e)))
        return

    slots = []
    has_signal = False
    has_refresh = False
    has_demo = False
    has_heavy_top_import = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    for dec in item.decorator_list:
                        if isinstance(dec, ast.Name) and dec.id == "Slot":
                            slots.append(item.name)
                            # Check return type
                            for d2 in item.decorator_list:
                                if isinstance(d2, ast.Call) and any(
                                    kw.arg == "result" for kw in d2.keywords
                                ):
                                    pass  # has result type
                if isinstance(item, ast.FunctionDef) and item.name == "refresh":
                    has_refresh = True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Signal"
        ):
            has_signal = True
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            and "MICHI_QML_DEMO" in node.value.value
        ):
            has_demo = True

    # Check for Signal declarations via regex (AST doesn't detect from-import easily)
    source = path.read_text()
    if "Signal()" in source or "Signal(" in source:
        has_signal = True

    # Check top-level imports from heavy modules
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in (node.names if isinstance(node, ast.Import) else []):
                if alias.name and any(h in alias.name for h in ["audio.", "gstreamer", "player_service"]):
                    has_heavy_top_import = True
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and any(h in node.module for h in ["audio.", "gstreamer", "player_service"])
            ):
                has_heavy_top_import = True

    # Report
    issues = []
    if not has_signal:
        issues.append("NO_SIGNAL")
    if not has_refresh and name not in REFRESH_EXEMPT:
        issues.append("NO_REFRESH")
    if has_demo:
        issues.append("HAS_DEMO_DATA")
    if has_heavy_top_import:
        issues.append("HEAVY_TOP_IMPORT")
    for slot in slots:
        if slot.startswith(("create", "delete", "remove", "rename", "update", "play", "scan")):
            issues.append(f"ACTION_SLOT_NO_DICT_RETURN: {slot}")

    if issues:
        WARNINGS.append((name, "; ".join(issues), ""))


def main():
    for f in sorted(BRIDGE_DIR.glob("*.py")):
        if f.name in EXCLUDED_FILES:
            continue
        check_file(f)

    print("# QML Bridge Contract Audit")
    print()
    if WARNINGS:
        print("| Bridge | Issues |")
        print("|---|---|")
        for name, issues, _ in sorted(WARNINGS):
            print(f"| {name} | {issues} |")
    else:
        print("No issues found.")

    print()
    print(f"**Total bridges checked:** {sum(1 for f in BRIDGE_DIR.glob('*.py') if f.name not in EXCLUDED_FILES)}")
    print(f"**Warnings:** {len(WARNINGS)}")
    return 0 if not any("NO_SIGNAL" in w[1] or "ACTION_SLOT_NO_DICT_RETURN" in w[1] for w in WARNINGS) else 1


if __name__ == "__main__":
    sys.exit(main())
