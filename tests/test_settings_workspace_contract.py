from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine


QML = Path(__file__).resolve().parents[1] / "ui_qml" / "pages"


def test_settings_workspace_owns_content_reload_and_transaction_bar():
    page = (QML / "SettingsPage.qml").read_text(encoding="utf-8")
    content = (QML / "SettingsContentPage.qml").read_text(encoding="utf-8")

    assert "property int reloadGeneration" in page
    assert 'source: "SettingsContentPage.qml"' in page
    assert "SettingsTransactionBar" in page
    assert 'objectName: "settingsPage"' in content


def test_pending_navigation_dialog_is_global():
    shell = (QML / "../shell/AppShell.qml").resolve().read_text(encoding="utf-8")
    assert 'objectName: "pendingSettingsNavigationDialog"' in shell
    assert "resolvePendingNavigation" in shell


@pytest.mark.parametrize(
    "name",
    ["SettingsPage.qml", "SettingsContentPage.qml", "SettingsTransactionBar.qml"],
)
def test_settings_workspace_components_instantiate_without_context(qtbot, name):
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML / name)))
    assert component.isReady(), [error.toString() for error in component.errors()]
    instance = component.create()
    assert instance is not None
    instance.deleteLater()
    engine.deleteLater()
