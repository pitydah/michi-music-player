from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("album_views")]

QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"

VIEWS = (
    ("pages/library/album/AlbumViewHost.qml", "albumViewHost"),
    ("pages/library/album/AlbumGridView.qml", "albumGridView"),
    ("pages/library/album/AlbumCoverFlowView.qml", "albumCoverFlowView"),
    ("pages/library/album/AlbumVinylWallView.qml", "albumVinylWallView"),
    ("pages/library/album/AlbumTimelineView.qml", "albumTimelineView"),
    ("pages/library/album/AlbumMagazineView.qml", "albumMagazineView"),
)
ALBUM_VIEWS = VIEWS[1:]


@pytest.fixture
def engine(qapp):
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_ROOT))
    yield qml_engine
    qml_engine.deleteLater()


@pytest.mark.parametrize(("relative_path", "object_name"), VIEWS)
def test_premium_album_view_compiles_and_instantiates(engine, relative_path, object_name):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    assert component.isReady(), component.errorString()

    item = component.createWithInitialProperties({"width": 1200, "height": 760})
    assert item is not None, component.errorString()
    assert item.objectName() == object_name
    item.deleteLater()


def test_album_view_host_exposes_all_five_modes(engine):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / "pages/library/album/AlbumViewHost.qml")))
    assert component.isReady(), component.errorString()

    host = component.createWithInitialProperties({"width": 1200, "height": 760})
    assert host is not None, component.errorString()
    modes_value = host.property("viewModes")
    modes = modes_value.toVariant() if hasattr(modes_value, "toVariant") else modes_value
    assert len(modes) == 5

    for index in range(5):
        host.setProperty("currentView", index)
        assert host.property("currentView") == index

    host.deleteLater()


def test_album_view_selector_supports_keyboard_cycle() -> None:
    source = (QML_ROOT / "pages/library/album/AlbumViewHost.qml").read_text()

    assert "function cycleView(step)" in source
    assert "Qt.Key_Tab" in source
    assert "Keys.onReturnPressed" in source
    assert "Keys.onSpacePressed" in source


@pytest.mark.parametrize("width", (800, 1200, 1600))
@pytest.mark.parametrize(("relative_path", "object_name"), ALBUM_VIEWS)
def test_populated_album_view_instantiates_at_supported_widths(
    engine,
    width,
    relative_path,
    object_name,
):
    from ui_qml.models.AlbumListModel import AlbumListModel

    model = AlbumListModel()
    model._items = [
        {
            "album_key": f"album-{index}",
            "title": f"Album {index}",
            "artist": "Artist",
            "year": 2000 + index,
            "decade": 2000,
            "track_count": 10,
            "cover_key": "",
        }
        for index in range(12)
    ]
    model._total_count = len(model._items)
    model._initialized = True
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    assert component.isReady(), component.errorString()

    item = component.createWithInitialProperties({
        "width": width,
        "height": 720,
        "albumModel": model,
    })

    assert item is not None, component.errorString()
    assert item.objectName() == object_name
    item.deleteLater()


def test_album_view_switch_does_not_requery_database(engine, qapp):
    from unittest.mock import MagicMock

    from ui_qml.models.AlbumListModel import AlbumListModel

    query = MagicMock()
    model = AlbumListModel(query_service=query)
    model._items = [{"album_key": "album-1", "title": "Album"}]
    model._total_count = 1
    model._initialized = True
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / "pages/library/album/AlbumViewHost.qml")))
    assert component.isReady(), component.errorString()
    host = component.createWithInitialProperties({
        "width": 1200,
        "height": 720,
        "albumModel": model,
    })

    for mode in range(5):
        host.setProperty("currentView", mode)
        qapp.processEvents()

    query.assert_not_called()
    host.deleteLater()
