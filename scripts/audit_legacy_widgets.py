#!/usr/bin/env python3
"""Audit which functions only exist in QtWidgets legacy and need migration."""
import ast
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONTROLLERS_DIR = PROJECT_ROOT / "legacy_widgets" / "ui" / "controllers"
BRIDGES_DIR = PROJECT_ROOT / "ui_qml_bridge"


def extract_methods(path):
    """Extract public method names from a Python file."""
    methods = set()
    try:
        with open(path) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                methods.add(node.name)
    except (SyntaxError, OSError) as e:
        print(f"Warning: could not parse {path}: {e}", file=sys.stderr)
    return methods


def extract_bridge_slots(bridge_path):
    """Extract @Slot decorated methods from a bridge file."""
    slots = set()
    try:
        with open(bridge_path) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                for dec in node.decorator_list:
                    if (isinstance(dec, ast.Call) and hasattr(dec.func, 'attr') and dec.func.attr == 'Slot') or (isinstance(dec, ast.Name) and dec.id == 'Slot'):
                        slots.add(node.name)
    except (SyntaxError, OSError) as e:
        print(f"Warning: could not parse {bridge_path}: {e}", file=sys.stderr)
    return slots


def main():
    report = {
        "legacy_controllers": [],
        "bridges": [],
        "only_in_legacy": {},
        "only_in_qml": {},
    }

    controller_methods = {}
    if CONTROLLERS_DIR.exists():
        for f in sorted(CONTROLLERS_DIR.rglob("*.py")):
            if f.name.startswith('__'):
                continue
            methods = extract_methods(f)
            if methods:
                rel = f.relative_to(CONTROLLERS_DIR.parent.parent)
                controller_methods[str(rel)] = methods
                report["legacy_controllers"].append(str(rel))
    else:
        print(f"WARNING: Controllers dir not found at {CONTROLLERS_DIR}", file=sys.stderr)

    bridge_slots = {}
    if BRIDGES_DIR.exists():
        for f in sorted(BRIDGES_DIR.glob("*_bridge.py")):
            if f.name.startswith('__'):
                continue
            slots = extract_bridge_slots(f)
            bridge_slots[f.name] = slots
            report["bridges"].append(f.name)
    else:
        print(f"WARNING: Bridges dir not found at {BRIDGES_DIR}", file=sys.stderr)

    for ctrl_path, methods in controller_methods.items():
        ctrl_name = Path(ctrl_path).name
        domain = ctrl_name.replace('_controller.py', '')
        matching_bridge = f"{domain}_bridge.py"
        qml_methods = bridge_slots.get(matching_bridge, set())

        only_in_ctrl = methods - qml_methods
        if only_in_ctrl:
            report["only_in_legacy"][ctrl_path] = sorted(only_in_ctrl)

    for bridge_name, slots in bridge_slots.items():
        domain = bridge_name.replace('_bridge.py', '').replace('_bridge_v2', '')
        matching_ctrl = f"{domain}_controller.py"
        ctrl_methods = set()
        for ctrl_path, methods in controller_methods.items():
            if Path(ctrl_path).name == matching_ctrl:
                ctrl_methods = methods
                break

        only_in_bridge = slots - ctrl_methods
        if only_in_bridge:
            report["only_in_qml"][bridge_name] = sorted(only_in_bridge)

    print(json.dumps(report, indent=2))

    total_only_legacy = sum(len(v) for v in report["only_in_legacy"].values())
    print(f"\nMethods only in legacy (not in QML bridges): {total_only_legacy}")

    if total_only_legacy > 50:
        print("WARNING: Over 50 methods only in legacy - high migration debt")

    return 0


if __name__ == "__main__":
    sys.exit(main())
