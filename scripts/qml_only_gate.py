#!/usr/bin/env python3
"""Gate: fail if production code imports QtWidgets or references legacy."""
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {".venv", "build", "tests", "docs", "scripts", "tools",
                "legacy_widgets", "__pycache__", "michi_ai_ui", ".git"}
EXCLUDE_PATTERNS = {"__pycache__", ".egg-info"}

ERRORS = []


def check_file(path):
    rel = path.relative_to(REPO)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return

    # Check text patterns
    for pat, label in [
        ("PySide6.QtWidgets", "QtWidgets import"),
        ("legacy_widgets", "legacy_widgets reference"),
        ("michi.widgets_app", "widgets_app reference"),
        ("QMainWindow", "QMainWindow reference"),
        ("MICHI_UI=widgets", "widgets mode"),

    ]:
        if pat in text:
            for i, line in enumerate(text.splitlines(), 1):
                if pat in line and not line.strip().startswith("#"):
                    ERRORS.append(f"{rel}:{i}: {label}: {line.strip()}")
                    break

    # AST check for imports
    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "QtWidgets" in alias.name:
                        ERRORS.append(f"{rel}: QtWidgets import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and "QtWidgets" in node.module:
                    ERRORS.append(f"{rel}: QtWidgets from-import: {node.module}")
    except SyntaxError:
        pass


def main():
    for path in REPO.rglob("*.py"):
        if any(ex in path.parts for ex in EXCLUDE_DIRS):
            continue
        if any(pat in str(path) for pat in EXCLUDE_PATTERNS):
            continue
        check_file(path)

    if ERRORS:
        print(f"QML-ONLY GATE FAILED: {len(ERRORS)} violations")
        for err in ERRORS:
            print(f"  {err}")
        sys.exit(1)
    print("QML-ONLY GATE PASSED: 0 violations")
    sys.exit(0)


if __name__ == "__main__":
    main()
