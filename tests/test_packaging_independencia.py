"""Tests for package independence rules:

- michi-qml (ui_qml, ui_qml_bridge) does NOT import PySide6.QtWidgets
- michi-core (core, audio, library, ...) does NOT import ui
- michi-widgets (ui/) depends on core (allowed)
"""
import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

IGNORE_DIRS = {"__pycache__", ".venv", "node_modules"}

QML_DIRS = ["ui_qml", "ui_qml_bridge"]
CORE_DIRS = ["core", "audio", "library", "metadata", "lyrics",
             "integrations", "sources", "streaming", "sync",
             "recognition", "recommendation"]
WIDGET_DIRS = ["ui"]

KNOWN_QML_QTWIDGETS_EXCEPTIONS = {"ui_qml_bridge/desktop_bridge.py"}

QML_PATTERNS = ["from PySide6.QtWidgets", "import PySide6.QtWidgets",
                "from PySide6 import QtWidgets"]

CORE_UI_PATTERNS = ["import ui", "from ui", "import ui.", "from ui."]


def _walk_py_files(base_dir: Path, subdirs: list[str]) -> list[Path]:
    result = []
    for sub in subdirs:
        p = base_dir / sub
        if not p.exists():
            continue
        for pyfile in p.rglob("*.py"):
            if any(ign in pyfile.parts for ign in IGNORE_DIRS):
                continue
            result.append(pyfile)
    return result


def _file_has_import(text: str, patterns: list[str]) -> list[str]:
    found = []
    for line in text.splitlines():
        for pat in patterns:
            if pat in line:
                found.append(line.strip())
    return found


def _get_rel(pyfile: Path) -> str:
    return str(pyfile.relative_to(REPO))


@pytest.fixture(scope="session")
def qml_py_files():
    return _walk_py_files(REPO, QML_DIRS)


@pytest.fixture(scope="session")
def core_py_files():
    return _walk_py_files(REPO, CORE_DIRS)


@pytest.fixture(scope="session")
def widget_py_files():
    return _walk_py_files(REPO, WIDGET_DIRS)


@pytest.fixture(scope="session")
def all_py_files():
    result = []
    for sub in QML_DIRS + CORE_DIRS + WIDGET_DIRS:
        p = REPO / sub
        if not p.exists():
            continue
        for pyfile in p.rglob("*.py"):
            if any(ign in pyfile.parts for ign in IGNORE_DIRS):
                continue
            result.append(pyfile)
    return result


class TestMichiQmlNoQtWidgets:
    """michi-qml must not import PySide6.QtWidgets (known exceptions allowed)."""

    def test_no_qtwidgets_in_ui_qml(self):
        files = _walk_py_files(REPO, ["ui_qml"])
        violations = []
        for pyfile in files:
            rel = _get_rel(pyfile)
            text = pyfile.read_text()
            hits = _file_has_import(text, QML_PATTERNS)
            if hits:
                violations.append(f"{rel}: {hits}")
        assert len(violations) == 0, "QtWidgets imports in ui_qml:\n" + "\n".join(violations)

    def test_no_qtwidgets_in_ui_qml_bridge_except_known(self):
        files = _walk_py_files(REPO, ["ui_qml_bridge"])
        violations = []
        for pyfile in files:
            rel = _get_rel(pyfile)
            if rel in KNOWN_QML_QTWIDGETS_EXCEPTIONS:
                continue
            text = pyfile.read_text()
            hits = _file_has_import(text, QML_PATTERNS)
            if hits:
                violations.append(f"{rel}: {hits}")
        assert len(violations) == 0, "QtWidgets imports in ui_qml_bridge:\n" + "\n".join(violations)

    def test_all_qml_files_no_qtwidgets_ast(self, qml_py_files):
        """AST-based check — catches dynamic/aliased imports."""
        violations = []
        for pyfile in qml_py_files:
            rel = _get_rel(pyfile)
            if rel in KNOWN_QML_QTWIDGETS_EXCEPTIONS:
                continue
            try:
                tree = ast.parse(pyfile.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "QtWidgets" in (node.module or ""):
                        names = [a.name for a in node.names]
                        violations.append(f"{rel}: from {node.module} import {names}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "QtWidgets" in alias.name:
                            violations.append(f"{rel}: import {alias.name}")
        assert len(violations) == 0, "QtWidgets imports (AST):\n" + "\n".join(violations)

    def test_qml_no_qtwidgets_in_qml_files(self):
        """QML .qml files must not reference QtWidgets."""
        qml_dirs = [REPO / d for d in QML_DIRS if (REPO / d).exists()]
        violations = []
        for qd in qml_dirs:
            for qmlfile in qd.rglob("*.qml"):
                if any(ign in qmlfile.parts for ign in IGNORE_DIRS):
                    continue
                text = qmlfile.read_text()
                if "QtWidgets" in text:
                    violations.append(str(qmlfile.relative_to(REPO)))
        assert len(violations) == 0, "QtWidgets references in QML files:\n" + "\n".join(violations)

    def test_qml_py_has_no_qt_widgets_module_level(self):
        """No file in ui_qml/ui_qml_bridge has module-level QtWidgets import."""
        files = _walk_py_files(REPO, QML_DIRS)
        violations = []
        for pyfile in files:
            rel = _get_rel(pyfile)
            if rel in KNOWN_QML_QTWIDGETS_EXCEPTIONS:
                continue
            text = pyfile.read_text()
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.endswith('"""'):
                    continue
                if "QtWidgets" in stripped and ("import" in stripped or "from" in stripped):
                    violations.append(f"{rel}: {stripped}")
        assert len(violations) == 0


class TestMichiCoreNoUi:
    """michi-core must not import ui."""

    def test_core_no_ui_import(self):
        files = _walk_py_files(REPO, CORE_DIRS)
        violations = []
        for pyfile in files:
            text = pyfile.read_text()
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""'):
                    continue
                for pat in CORE_UI_PATTERNS:
                    if pat in stripped:
                        violations.append(f"{_get_rel(pyfile)}: {stripped}")
        assert len(violations) == 0, "ui imports in core dirs:\n" + "\n".join(violations)

    def test_core_no_ui_import_ast(self):
        files = _walk_py_files(REPO, CORE_DIRS)
        violations = []
        for pyfile in files:
            try:
                tree = ast.parse(pyfile.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "ui" or node.module.startswith("ui.")):
                        violations.append(f"{_get_rel(pyfile)}: from {node.module} import ...")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "ui" or alias.name.startswith("ui."):
                            violations.append(f"{_get_rel(pyfile)}: import {alias.name}")
        assert len(violations) == 0, "ui imports in core dirs (AST):\n" + "\n".join(violations)

    def test_core_no_qtwidgets_direct_import(self):
        files = _walk_py_files(REPO, CORE_DIRS)
        violations = []
        for pyfile in files:
            text = pyfile.read_text()
            for pat in QML_PATTERNS:
                if pat in text:
                    violations.append(f"{_get_rel(pyfile)}: import QtWidgets")
        assert len(violations) == 0, "QtWidgets imports in core dirs:\n" + "\n".join(violations)


class TestMichiWidgetsDependsOnCore:
    """michi-widgets (ui/) depends on core — this is allowed but must be verified."""

    def test_widgets_imports_core(self):
        files = _walk_py_files(REPO, WIDGET_DIRS)
        found_core = 0
        for pyfile in files:
            text = pyfile.read_text()
            if "from core" in text or "import core" in text:
                found_core += 1
        assert found_core > 0, "No ui/ files import core"

    def test_widgets_has_core_imports_ast(self):
        files = _walk_py_files(REPO, WIDGET_DIRS)
        imports = []
        for pyfile in files:
            try:
                tree = ast.parse(pyfile.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "core" or node.module.startswith("core.")):
                        imports.append(f"{_get_rel(pyfile)}: {node.module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "core" or alias.name.startswith("core."):
                            imports.append(f"{_get_rel(pyfile)}: {alias.name}")
        assert len(imports) > 0, "No ui/ files import core (AST check)"

    def test_widgets_depends_on_core_not_other_way(self):
        """Core should NOT import widgets, but widgets SHOULD import core."""
        core_imports_widget = []
        for pyfile in _walk_py_files(REPO, CORE_DIRS):
            text = pyfile.read_text()
            if ("from ui" in text or "import ui" in text) and "import" in text and "QtWidgets" not in text:
                core_imports_widget.append(_get_rel(pyfile))
        assert len(core_imports_widget) == 0, "Core imports widget:\n" + "\n".join(core_imports_widget)


class TestPyProjectMarkers:
    def test_pyproject_mentions_three_packages(self):
        text = (REPO / "pyproject.toml").read_text()
        assert "michi-core" in text
        assert "michi-qml" in text
        assert "michi-widgets-legacy" in text

    def test_pyproject_no_qtwidgets_in_qml_package(self):
        text = (REPO / "pyproject.toml").read_text()
        text_lower = text.lower()
        qml_section = text_lower[text_lower.find("michi-qml"):]
        if "qtwidgets" in qml_section:
            pytest.fail("pyproject.toml references QtWidgets in michi-qml section")
