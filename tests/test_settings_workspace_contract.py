from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import (
    QCoreApplication,
    QObject,
    QUrl,
    Slot,
    qInstallMessageHandler,
)
from PySide6.QtQml import QQmlComponent, QQmlEngine

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


QML = Path(__file__).resolve().parents[1] / "ui_qml" / "pages"
SETTINGS_PAGES = sorted((QML / "settings").glob("Settings*Page.qml"))
QML_RUNTIME_ERRORS = (
    "Binding loop",
    "Cannot assign to non-existent property",
    "Cannot connect to",
    "Cannot create",
    "ReferenceError",
    "TypeError",
    "is not a function",
)


class SettingsBridgeProbe(QObject):
    """Provide the settings API required by QML contract tests."""

    @Slot(str, result=object)
    def getValue(self, _key: str) -> None:
        return None

    @Slot(str, object, result=object)
    def setValue(self, _key: str, _value: object) -> dict[str, bool]:
        return {"ok": True}


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


@pytest.mark.parametrize("page_path", SETTINGS_PAGES, ids=lambda path: path.stem)
def test_settings_page_instantiates_without_runtime_errors(
    qtbot: "QtBot", page_path: Path
) -> None:
    messages = []
    previous_handler = qInstallMessageHandler(
        lambda _msg_type, _context, message: messages.append(message)
    )
    engine = QQmlEngine()
    bridge = SettingsBridgeProbe()
    engine.rootContext().setContextProperty("settingsBridge", bridge)
    try:
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(page_path)))
        assert component.isReady(), [error.toString() for error in component.errors()]
        instance = component.create()
        assert instance is not None
        QCoreApplication.processEvents()
        runtime_errors = [
            message
            for message in messages
            if any(marker in message for marker in QML_RUNTIME_ERRORS)
        ]
        assert not runtime_errors
        instance.deleteLater()
    finally:
        qInstallMessageHandler(previous_handler)
        engine.deleteLater()
