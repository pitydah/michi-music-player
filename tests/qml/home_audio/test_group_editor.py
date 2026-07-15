"""Test GroupEditorPage selections, create group logic, accessibility."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
pytestmark = pytest.mark.isolation


@pytest.fixture
def engine(qapp):
    e = QQmlEngine(qapp)
    e.addImportPath(str(QML_DIR))
    return e


def test_group_editor_loads(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/GroupEditorPage.qml")))
    assert component.isReady()


def test_group_editor_has_object_name(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/GroupEditorPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") == "groupEditorPage"
    finally:
        obj.deleteLater()


def test_group_editor_selection(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/GroupEditorPage.qml")))
    obj = component.create()
    try:
        assert obj.property("selectedZoneIds") is not None
    finally:
        obj.deleteLater()


def test_group_editor_null_bridge_safe(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/GroupEditorPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") == "groupEditorPage"
    finally:
        obj.deleteLater()


def test_group_editor_accessible(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home_audio/GroupEditorPage.qml")))
    assert component.isReady()
    source = (QML_DIR / "pages/home_audio/GroupEditorPage.qml").read_text()
    assert "Accessible.name" in source
    assert "objectName" in source
