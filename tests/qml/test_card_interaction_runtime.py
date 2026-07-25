from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QUrl, Qt
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest


QML_ROOT = Path(__file__).resolve().parents[2] / "ui_qml"


def _card_harness(engine: QQmlEngine) -> QQmlComponent:
    source = b'''import QtQuick
import QtQuick.Controls
import "../components"

Item {
    width: 360
    height: 220
    property int cardClicks: 0
    property int childClicks: 0

    MichiCard {
        id: card
        objectName: "testedCard"
        x: 20
        y: 20
        width: 320
        height: 180
        interactive: true
        title: "Interactive card"
        onClicked: parent.cardClicks += 1

        Button {
            objectName: "childButton"
            width: 140
            height: 44
            text: "Child action"
            onClicked: card.parent.childClicks += 1
        }
    }
}
'''
    component = QQmlComponent(engine)
    component.setData(source, QUrl.fromLocalFile(str(QML_ROOT / "tests/CardHarness.qml")))
    return component


def test_child_control_is_not_blocked_by_interactive_card(qapp) -> None:
    engine = QQmlEngine()
    component = _card_harness(engine)
    assert component.isReady(), component.errorString()
    root = component.create()
    assert root is not None, component.errorString()
    window = QQuickWindow()
    window.resize(360, 220)
    root.setParentItem(window.contentItem())
    window.show()
    qapp.processEvents()

    child = root.findChild(QQuickItem, "childButton")
    card = root.findChild(QQuickItem, "testedCard")
    assert child is not None
    assert card is not None

    child_point = child.mapToScene(QPoint(int(child.width() / 2), int(child.height() / 2))).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, child_point)
    qapp.processEvents()
    assert root.property("childClicks") == 1
    assert root.property("cardClicks") == 0

    card_point = card.mapToScene(QPoint(int(card.width() / 2), int(card.height() - 20))).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, card_point)
    qapp.processEvents()
    assert root.property("cardClicks") == 1

    window.close()
    root.deleteLater()
    engine.deleteLater()


def test_glass_card_preserves_interactive_visual_contract(qapp) -> None:
    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / "components/GlassCard.qml")))
    assert component.isReady(), component.errorString()
    card = component.create()
    assert card is not None, component.errorString()
    assert card.property("interactive") is True
    assert card.property("variant") == "glass"
    assert card.property("controlObjectName") == "glassCard"
    card.deleteLater()
    engine.deleteLater()
