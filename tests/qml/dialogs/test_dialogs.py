"""Tests for standardized dialog components (BaseDialog, ConfirmDialog, DestructiveDialog, InputDialog)."""


import pytest

try:
    from pytest_qt.qtbot import QtBot
except ImportError:
    QtBot = None


@pytest.fixture
def theme_mock(monkeypatch):
    if QtBot is None:
        pytest.skip("pytest-qt not available")
    monkeypatch.setattr(
        "PySide6.QtQml.qmlRegisterSingletonInstance",
        lambda *a, **kw: None,
    )


@pytest.fixture
def dialog_qml_path():
    return "ui_qml/components/dialogs"


def test_base_dialog_loads(qtbot: QtBot, theme_mock):
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.loadUrl("ui_qml/components/dialogs/BaseDialog.qml")
    assert component.status() == QQmlComponent.Status.Ready, component.errorString()


def test_confirm_dialog_loads(qtbot: QtBot, theme_mock):
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.loadUrl("ui_qml/components/dialogs/ConfirmDialog.qml")
    assert component.status() == QQmlComponent.Status.Ready, component.errorString()


def test_destructive_dialog_loads(qtbot: QtBot, theme_mock):
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.loadUrl("ui_qml/components/dialogs/DestructiveDialog.qml")
    assert component.status() == QQmlComponent.Status.Ready, component.errorString()


def test_input_dialog_loads(qtbot: QtBot, theme_mock):
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.loadUrl("ui_qml/components/dialogs/InputDialog.qml")
    assert component.status() == QQmlComponent.Status.Ready, component.errorString()


@pytest.mark.parametrize("dialog_file", [
    "BaseDialog.qml",
    "ConfirmDialog.qml",
    "DestructiveDialog.qml",
    "InputDialog.qml",
])
def test_all_dialogs_have_object_name(qtbot: QtBot, theme_mock, dialog_file):
    import os
    filepath = os.path.join("ui_qml/components/dialogs", dialog_file)
    with open(filepath) as f:
        content = f.read()
    assert "objectName:" in content, f"{dialog_file} missing objectName"


@pytest.mark.parametrize("dialog_file", [
    "BaseDialog.qml",
    "ConfirmDialog.qml",
    "DestructiveDialog.qml",
    "InputDialog.qml",
])
def test_all_dialogs_have_accessible(qtbot: QtBot, theme_mock, dialog_file):
    import os
    filepath = os.path.join("ui_qml/components/dialogs", dialog_file)
    with open(filepath) as f:
        content = f.read()
    assert "Accessible.role" in content, f"{dialog_file} missing Accessible.role"
    assert "Accessible.name" in content, f"{dialog_file} missing Accessible.name"
    assert "Accessible.description" in content, f"{dialog_file} missing Accessible.description"


@pytest.mark.parametrize("dialog_file", [
    "BaseDialog.qml",
    "ConfirmDialog.qml",
    "DestructiveDialog.qml",
    "InputDialog.qml",
])
def test_all_dialogs_have_focus_trap(qtbot: QtBot, theme_mock, dialog_file):
    import os
    filepath = os.path.join("ui_qml/components/dialogs", dialog_file)
    with open(filepath) as f:
        content = f.read()
    assert "FocusTrap" in content, f"{dialog_file} missing FocusTrap"


def test_confirm_dialog_has_icon_types(qtbot: QtBot, theme_mock):
    filepath = "ui_qml/components/dialogs/ConfirmDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "iconType" in content
    assert "warning" in content or '"info"' in content


def test_destructive_dialog_has_keyword_check(qtbot: QtBot, theme_mock):
    filepath = "ui_qml/components/dialogs/DestructiveDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "keyword" in content
    assert "_keywordMatched" in content


def test_input_dialog_has_validation(qtbot: QtBot, theme_mock):
    filepath = "ui_qml/components/dialogs/InputDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "required" in content
    assert "pattern" in content
    assert "validationError" in content
    assert "minLength" in content
    assert "maxLength" in content
