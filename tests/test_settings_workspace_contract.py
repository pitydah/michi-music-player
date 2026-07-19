from pathlib import Path


def test_settings_workspace_wraps_content_and_transaction_bar():
    path = Path("ui_qml/pages/SettingsPage.qml")
    qml = path.read_text(encoding="utf-8")
    assert "SettingsContentPage" in qml
    assert "SettingsTransactionBar" in qml
    assert "commitAll" in qml
    assert "rollbackAll" in qml
