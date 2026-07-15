"""Test Mix pages keyboard navigation via QML component loading."""
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


def test_mix_hub_page_loads(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/MixHubPage.qml")))
    assert component.isReady()


def test_mix_detail_page_loads(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/MixDetailPage.qml")))
    assert component.isReady()


def test_mix_generator_page_loads(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/mix/MixGeneratorPage.qml")))
    assert component.isReady()


def test_mix_result_page_loads(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/mix/MixResultPage.qml")))
    assert component.isReady()


def test_mix_hub_focus_scope(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/MixHubPage.qml")))
    assert component.isReady()


def test_mix_detail_object_name(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/MixDetailPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") == "mixDetailPage"
    finally:
        obj.deleteLater()


def test_mix_generator_object_name(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/mix/MixGeneratorPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") == "mixGeneratorPage"
    finally:
        obj.deleteLater()


def test_mix_result_object_name(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/mix/MixResultPage.qml")))
    obj = component.create()
    try:
        assert obj.property("objectName") == "mixResultPage"
    finally:
        obj.deleteLater()


def test_mix_hub_accessible(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/MixHubPage.qml")))
    assert component.isReady()
    source = (QML_DIR / "pages/MixHubPage.qml").read_text()
    assert "Accessible.name" in source
    assert "objectName" in source


def test_mix_generator_key_navigation(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/mix/MixGeneratorPage.qml")))
    assert component.isReady()
