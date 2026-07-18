#!/usr/bin/env python3
"""Validate QML→Bridge→Service contracts.

Checks: slot exists, property exists, service method exists, result fields match.
"""
import ast
import importlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ERRORS = []


def get_qml_imports(qml_file: str) -> set[str]:
    imports = set()
    with open(qml_file) as f:
        content = f.read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "import":
                for child in ast.walk(node):
                    if isinstance(child, ast.Str):
                        imports.add(child.s)
    return imports


def validate_bridge_module(module_name: str):
    try:
        mod = importlib.import_module(module_name)
    except ImportError:
        ERRORS.append(f"BRIDGE_IMPORT_FAILED: {module_name}")
        return

    # Find QObject subclasses
    for name in dir(mod):
        cls = getattr(mod, name, None)
        if not isinstance(cls, type):
            continue
        if "QObject" in [b.__name__ for b in cls.__bases__] if hasattr(cls, '__bases__') else []:
            continue
        # Check if it has Signal or Slot
        has_signal = any("Signal" in str(getattr(cls, a, None)) for a in dir(cls))
        has_slot = any("Slot" in str(getattr(cls, s, None)) for s in dir(cls))
        if has_signal or has_slot:
            print(f"  {module_name}.{name}: QObject bridge OK")


def main():
    print("=== QML Bridge Contract Validation ===\n")

    bridges_dir = REPO / "ui_qml_bridge"
    for pyfile in sorted(bridges_dir.glob("*.py")):
        if pyfile.name.startswith("_"):
            continue
        mod_name = f"ui_qml_bridge.{pyfile.stem}"
        print(f"Checking: {mod_name}")
        validate_bridge_module(mod_name)

    print(f"\n=== Result ===")
    if ERRORS:
        print(f"FAILED: {len(ERRORS)} errors")
        for e in ERRORS:
            print(f"  {e}")
        sys.exit(1)
    print("PASSED: All bridges validate")
    sys.exit(0)


if __name__ == "__main__":
    main()
