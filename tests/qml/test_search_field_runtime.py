from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMetaObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest


QML_ROOT = Path(__file__).resolve().parents[2] / "ui_qml"


def test_clear_cancels_debounce_and_emits_once(qapp) -> None:
    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.setData(
        b'''import QtQuick
import "../components"

Item {
    width: 320
    height: 80
    property int textChanges: 0
    property int clears: 0

    MichiSearchField {
        id: search
        objectName: "testedSearch"
        x: 20
        y: 16
        width: 280
        debounceMs: 80
        onSearchTextChanged: parent.textChanges += 1
        onClearRequested: parent.clears += 1
    }
}
''',
        QUrl.fromLocalFile(str(QML_ROOT / "tests/SearchFieldHarness.qml")),
    )
    assert component.isReady(), component.errorString()
    root = component.create()
    assert root is not None, component.errorString()
    window = QQuickWindow()
    window.resize(320, 80)
    root.setParentItem(window.contentItem())
    window.show()
    qapp.processEvents()

    search = root.findChild(QQuickItem, "testedSearch")
    clear_button = root.findChild(QQuickItem, "searchClearButton")
    assert search is not None
    assert clear_button is not None
    search.setProperty("text", "michi")
    qapp.processEvents()
    assert QMetaObject.invokeMethod(clear_button, "click")
    QTest.qWait(120)
    qapp.processEvents()

    assert search.property("text") == ""
    assert root.property("clears") == 1
    assert root.property("textChanges") == 0

    window.close()
    root.deleteLater()
    engine.deleteLater()
