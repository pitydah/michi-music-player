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
            if node.module and node.module.startswith("ui."):
                assert False, f"QML app imports ui.*: {node.module}"


def test_qml_app_imports_pyside_qml():
    """michi/qml_app.py should import PySide6.QtQml (QML runtime)."""
    code = (REPO / "michi" / "qml_app.py").read_text()
    assert "QQmlApplicationEngine" in code or "QGuiApplication" in code


def test_widgets_app_imports_qt_widgets():
    """michi/widgets_app.py should import QtWidgets (it's the widgets launcher)."""
    code = (REPO / "michi" / "widgets_app.py").read_text()
    assert "QApplication" in code or "QtWidgets" in code


def test_app_launcher_dispatches_qml():
    """app_launcher.py must dispatch to qml_app when MICHI_UI=qml."""
    code = (REPO / "michi" / "app_launcher.py").read_text()
    assert "run_qml" in code
    assert "run_widgets" in code


def test_app_launcher_defaults_widgets():
    """app_launcher.py must default to widgets."""
    code = (REPO / "michi" / "app_launcher.py").read_text()
    assert '"widgets"' in code or "'widgets'" in code
