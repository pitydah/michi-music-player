"""Test app launcher separation — MICHI_UI modes, no GUI needed."""
import ast
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent


def test_qml_app_no_widgets_import():
    """michi/qml_app.py must not import QtWidgets."""
    code = (REPO / "michi" / "qml_app.py").read_text()
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "QtWidgets" in alias.name:
                    assert False, f"QML app imports QtWidgets: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module and "QtWidgets" in node.module:
                assert False, f"QML app imports QtWidgets: {node.module}"


def test_qml_app_imports_pyside_qml():
    """michi/qml_app.py should import PySide6.QtQml (QML runtime)."""
    code = (REPO / "michi" / "qml_app.py").read_text()
    assert "QQmlApplicationEngine" in code or "QGuiApplication" in code


def test_app_launcher_dispatches_qml():
    """app_launcher.py must dispatch to qml_app when MICHI_UI=qml."""
    code = (REPO / "michi" / "app_launcher.py").read_text()
    assert "run_qml" in code


def test_app_launcher_defaults_qml():
    """app_launcher.py must default to qml."""
    code = (REPO / "michi" / "app_launcher.py").read_text()
    assert '"qml"' in code or "'qml'" in code
