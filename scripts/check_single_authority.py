"""Gate script: forbid imports that bypass the single-authority (QML) pattern.

Exits with code 1 if any forbidden import is found, 0 otherwise.
"""
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PATTERNS: list[str] = [
    "core.app_context",
    "core.app_services",
    "ui_qml_bridge.service_bundle",
    "legacy_widgets",
    "michi.widgets_app",
    "PySide6.QtWidgets",
    "QMainWindow",
    "QApplication",
]

IGNORE_DIRS = {"build", ".venv", ".git"}

# Files with legitimate usage of forbidden patterns
IGNORE_FILES: set[str] = {
    "tests/test_crash_reporter.py",  # needs QApplication for crash reporter testing
}


def _skip(path: Path) -> bool:
    if any(part in IGNORE_DIRS for part in path.parts):
        return True
    return any(str(path).endswith(ignore_file) for ignore_file in IGNORE_FILES)


def check_file(path: Path) -> list[tuple[str, int, str]]:
    """Return list of (filename, lineno, import_text) for violations."""
    violations: list[tuple[str, int, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        # import X
        if isinstance(node, ast.Import):
            for alias in node.names:
                for pattern in FORBIDDEN_PATTERNS:
                    if alias.name == pattern or alias.name.startswith(pattern + "."):
                        violations.append(
                            (str(path), node.lineno, f"import {alias.name}")
                        )
                        break

        # from X import Y
        if isinstance(node, ast.ImportFrom) and node.module:
            for pattern in FORBIDDEN_PATTERNS:
                if node.module == pattern or node.module.startswith(pattern + "."):
                    names = ", ".join(a.name for a in node.names)
                    violations.append(
                        (str(path), node.lineno, f"from {node.module} import {names}")
                    )
                    break

    return violations


def main() -> int:
    all_violations: list[tuple[str, int, str]] = []

    for py_file in sorted(REPO_ROOT.rglob("*.py")):
        if _skip(py_file):
            continue
        all_violations.extend(check_file(py_file))

    if all_violations:
        print("FORBIDDEN IMPORTS FOUND:")
        for fname, lineno, text in all_violations:
            print(f"  {fname}:{lineno}: {text}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
