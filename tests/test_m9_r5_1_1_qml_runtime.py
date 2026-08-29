"""M9-R5.1.1 real-QML geometry gates for Search and Scan."""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


QML_DIR = Path("src/michi/presentation/qml").resolve()

HARNESS = """
import QtQuick
import QtQuick.Controls.Basic
import "../controls"

Window {
    id: harness
    visible: true
    width: 520
    height: 180
    color: "#000000"
    property int primaryClicks: 0
    property int secondaryClicks: 0

    MichiSearchField {
        id: search
        objectName: "polishSearch"
        x: 20
        y: 20
        width: 320
    }

    MichiSplitButton {
        id: scan
        objectName: "polishScan"
        x: 20
        y: 76
        width: implicitWidth
        text: qsTr("Scan library")
        iconName: ""
        onPrimaryClicked: harness.primaryClicks++
        onSecondaryClicked: harness.secondaryClicks++
    }
}
"""


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _build(qapp):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.setData(
        HARNESS.encode("utf-8"),
        QUrl.fromLocalFile(str(QML_DIR / "controls/harness.qml")),
    )
    assert component.status() == QQmlComponent.Ready, component.errorString()
    window = component.create()
    assert window is not None
    window.show()
    for _ in range(10):
        qapp.processEvents()
    return engine, component, window


def _item(window, name):
    stack = [window.contentItem()]
    while stack:
        item = stack.pop()
        if str(item.objectName()) == name:
            return item
        if isinstance(item, QQuickItem):
            stack.extend(item.childItems())
    fallback = window.findChild(QObject, name)
    assert fallback is not None, name
    return fallback


def _click(qapp, window, item, local_x):
    scene = item.mapToScene(QPointF(local_x, item.height() / 2))
    QTest.mouseClick(
        window,
        Qt.LeftButton,
        Qt.NoModifier,
        QPoint(round(scene.x()), round(scene.y())),
    )
    qapp.processEvents()


def test_search_and_scan_resolve_to_the_same_36px_height(qapp) -> None:
    harness = _build(qapp)
    window = harness[2]
    search = _item(window, "polishSearch")
    scan = _item(window, "polishScan")

    assert search.property("implicitHeight") == 36
    assert scan.property("implicitHeight") == 36
    assert search.height() == scan.height() == 36
    window.close()


def test_empty_icon_removes_its_width_and_spacing_at_runtime(qapp) -> None:
    harness = _build(qapp)
    window = harness[2]
    scan = _item(window, "polishScan")
    without_icon = scan.property("implicitWidth")

    scan.setProperty("iconName", "library")
    for _ in range(5):
        qapp.processEvents()
    with_icon = scan.property("implicitWidth")

    # 16 px canonical icon + 8 px canonical Row spacing. Allow a small
    # tolerance for layout rounding while proving no ghost reservation.
    assert with_icon - without_icon >= 22
    window.close()


def test_primary_and_compact_disclosure_keep_independent_hit_areas(qapp) -> None:
    harness = _build(qapp)
    window = harness[2]
    scan = _item(window, "polishScan")

    _click(qapp, window, scan, 12)
    _click(qapp, window, scan, scan.width() - 12)

    assert window.property("primaryClicks") == 1
    assert window.property("secondaryClicks") == 1
    window.close()
