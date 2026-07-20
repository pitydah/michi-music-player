from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("library")]

QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"

VIEWS = (
    ("pages/library/ArtistCard.qml", "artistCard"),
    ("pages/library/ArtistGridPage.qml", "artistGridPage"),
    ("pages/library/FolderBreadcrumb.qml", "folderBreadcrumb"),
    ("pages/library/FolderTreeView.qml", "folderTreeView"),
    ("pages/library/FolderContentView.qml", "folderContentView"),
    ("pages/library/FolderBrowserPage.qml", "folderBrowserPage"),
)


@pytest.fixture
def engine(qapp):
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_ROOT))
    yield qml_engine
    qml_engine.deleteLater()


@pytest.mark.parametrize(("relative_path", "object_name"), VIEWS)
@pytest.mark.parametrize("width", (800, 1200))
def test_navigation_view_compiles_at_supported_widths(
    engine,
    relative_path,
    object_name,
    width,
):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    assert component.isReady(), component.errorString()

    item = component.createWithInitialProperties({"width": width, "height": 720})
    assert item is not None, component.errorString()
    assert item.objectName() == object_name
    item.deleteLater()


def test_artist_grid_uses_explicit_roles_and_incremental_loading():
    source = (
        QML_ROOT / "pages/library/ArtistGridPage.qml"
    ).read_text(encoding="utf-8")

    assert "required property string name" in source
    assert "required property var trackCount" in source
    assert "function maybeFetchMore()" in source
    assert "root.artistModel.fetchMore()" in source
    assert "model.name" not in source


def test_folder_navigation_never_mutates_private_python_model_state():
    tree = (
        QML_ROOT / "pages/library/FolderTreeView.qml"
    ).read_text(encoding="utf-8")
    browser = (
        QML_ROOT / "pages/library/FolderBrowserPage.qml"
    ).read_text(encoding="utf-8")

    assert "._items" not in tree
    assert "._items" not in browser
    assert 'refresh("parent_path"' not in tree
    assert 'refresh("parent_path"' not in browser
    assert "root.folderModel.refresh(root.currentPath)" in tree
    assert "root.folderModel.refresh(root._currentPath)" in browser


def test_folder_content_has_selection_and_explicit_play_action():
    source = (
        QML_ROOT / "pages/library/FolderContentView.qml"
    ).read_text(encoding="utf-8")

    assert 'objectName: "folderTrackList"' in source
    assert "onDoubleClicked: root.playTrack" in source
    assert "function playSelected()" in source
    assert 'text: "Contenido: qsTr("' not in source
