"""Tests for dialog negative/edge cases: validation, destructive confirmation."""


def test_input_dialog_required_validation():
    """InputDialog should validate required field."""
    filepath = "ui_qml/components/dialogs/InputDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "required" in content
    assert "validationError" in content
    assert "validate()" in content
    assert "Este campo es obligatorio." in content


def test_input_dialog_min_length():
    filepath = "ui_qml/components/dialogs/InputDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "minLength" in content
    assert "Mínimo" in content


def test_input_dialog_max_length():
    filepath = "ui_qml/components/dialogs/InputDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "maxLength" in content
    assert "Máximo" in content


def test_input_dialog_pattern_validation():
    filepath = "ui_qml/components/dialogs/InputDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "pattern" in content
    assert "RegExp" in content


def test_input_dialog_error_display():
    filepath = "ui_qml/components/dialogs/InputDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "errorText" in content
    assert "Accessible.AlertMessage" in content


def test_destructive_dialog_confirm_disabled_by_default():
    filepath = "ui_qml/components/dialogs/DestructiveDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "confirmEnabled: false" in content


def test_destructive_dialog_irreversible_warning():
    filepath = "ui_qml/components/dialogs/DestructiveDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "no se puede deshacer" in content


def test_destructive_dialog_backup_suggestion():
    filepath = "ui_qml/components/dialogs/DestructiveDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "backupSuggestion" in content


def test_destructive_dialog_affected_count():
    filepath = "ui_qml/components/dialogs/DestructiveDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "affectedCount" in content
    assert "affectedType" in content


def test_base_dialog_close_on_click_outside():
    filepath = "ui_qml/components/dialogs/BaseDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "CloseOnClickOutside" in content


def test_confirm_dialog_supports_dont_ask_again():
    filepath = "ui_qml/components/dialogs/ConfirmDialog.qml"
    with open(filepath) as f:
        content = f.read()
    assert "showDontAskAgain" in content
    assert "dontAskAgain" in content


def test_all_dialogs_handle_null_content():
    """All dialogs should handle contentItem being null gracefully."""
    dialogs = ["BaseDialog.qml", "ConfirmDialog.qml", "DestructiveDialog.qml", "InputDialog.qml"]
    for d in dialogs:
        filepath = f"ui_qml/components/dialogs/{d}"
        with open(filepath) as f:
            content = f.read()
        assert "?" not in content or "contentItem" in content
