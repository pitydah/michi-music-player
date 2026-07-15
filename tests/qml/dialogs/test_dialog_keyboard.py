"""Tests for dialog keyboard navigation: focus trap, escape, enter."""


import pytest


@pytest.fixture
def theme_mock(monkeypatch):
    monkeypatch.setattr(
        "PySide6.QtQml.qmlRegisterSingletonInstance",
        lambda *a, **kw: None,
    )


def test_base_dialog_escape_key(qtbot, theme_mock):
    """BaseDialog should handle Escape key via closePolicy."""
    filepath = "ui_qml/components/dialogs/BaseDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onEscapePressed" in content
    assert "CloseOnEscape" in content


def test_base_dialog_enter_key(qtbot, theme_mock):
    """BaseDialog should handle Return/Enter key for confirmation."""
    filepath = "ui_qml/components/dialogs/BaseDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onReturnPressed" in content
    assert "Keys.onEnterPressed" in content


def test_base_dialog_focus_trap(qtbot, theme_mock):
    filepath = "ui_qml/components/dialogs/BaseDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "FocusTrap" in content


def test_base_dialog_focus_restoration(qtbot, theme_mock):
    filepath = "ui_qml/components/dialogs/BaseDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "_savedFocus" in content
    assert "_restoreFocus" in content
    assert "_focusFirstInteractive" in content


def test_confirm_dialog_button_focus(qtbot, theme_mock):
    filepath = "ui_qml/components/dialogs/ConfirmDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "focus: true" in content


def test_destructive_dialog_escape_keyword(qtbot, theme_mock):
    filepath = "ui_qml/components/dialogs/DestructiveDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onEscapePressed" in content
    assert "Keys.onReturnPressed" in content
    assert "keyword" in content


def test_destructive_dialog_confirm_enabled_by_keyword(qtbot, theme_mock):
    filepath = "ui_qml/components/dialogs/DestructiveDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "_keywordMatched" in content


def test_input_dialog_return_key(qtbot, theme_mock):
    filepath = "ui_qml/components/dialogs/InputDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onReturnPressed" in content
    assert "Keys.onEscapePressed" in content


def test_all_dialogs_have_close_on_escape(qtbot, theme_mock):
    import os
    dialogs = ["BaseDialog.qml", "DestructiveDialog.qml", "InputDialog.qml"]
    for d in dialogs:
        filepath = os.path.join("ui_qml/components/dialogs", d)
        with open(filepath) as f:
            content = f.read()
        assert "Keys.onEscapePressed" in content, f"{d} missing Escape handling"
    filepath = os.path.join("ui_qml/components/dialogs", "ConfirmDialog.qml")
    with open(filepath) as f:
        content = f.read()
    assert "Keys.onEscapePressed" in content or "BaseDialog" in content, "ConfirmDialog should inherit Escape from BaseDialog"
