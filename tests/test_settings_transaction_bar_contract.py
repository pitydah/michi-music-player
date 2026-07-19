from pathlib import Path


def test_settings_transaction_bar_has_global_actions():
    qml = Path("ui_qml/pages/SettingsTransactionBar.qml").read_text(encoding="utf-8")
    assert "bridge.hasPendingChanges" in qml
    assert "bridge.pendingCount" in qml
    assert "applyRequested" in qml
    assert "discardRequested" in qml
