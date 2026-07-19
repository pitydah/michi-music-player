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
    modes = host.property("viewModes")
    assert len(modes) == 5

    for index in range(5):
        host.setProperty("currentView", index)
        assert host.property("currentView") == index

    host.deleteLater()
