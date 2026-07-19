from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("library")]

QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"

COMPONENTS = (
    ("components/MichiLibraryToolbar.qml", "michiLibraryToolbar"),
    ("pages/library/LibraryPage.qml", "libraryPage_control"),
    ("pages/library/LibraryFilterBar.qml", "libraryFilterBar"),
    ("pages/library/LibraryTrackTable.qml", "libraryTrackTable"),
    ("pages/library/LibrarySelectionBar.qml", "librarySelectionBar"),
    ("pages/library/LibraryContextMenu.qml", "LibraryContextMenu"),
    ("pages/library/AlbumDetailPage.qml", "albumDetailPage"),
    ("pages/library/ArtistDetailPage.qml", "artistDetailPage"),
    ("shell/PageStack.qml", "pageStack"),
)


@pytest.fixture
def engine(qapp):
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_ROOT))
    yield qml_engine
    qml_engine.deleteLater()


@pytest.mark.parametrize(("relative_path", "object_name"), COMPONENTS)
def test_premium_library_component_compiles_and_instantiates(
    engine,
    relative_path,
    object_name,
):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    assert component.isReady(), component.errorString()

    instance = component.createWithInitialProperties({"width": 1200, "height": 760})
    assert instance is not None, component.errorString()
    assert instance.objectName() == object_name
    instance.deleteLater()
