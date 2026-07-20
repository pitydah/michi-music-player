from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("library")]

QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"


@pytest.fixture
def engine(qapp):
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_ROOT))
    yield qml_engine
    qml_engine.deleteLater()


def _create(engine, relative_path: str, **properties):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    assert component.isReady(), component.errorString()
    item = component.createWithInitialProperties(properties)
    assert item is not None, component.errorString()
    return component, item


def test_cover_image_compiles_without_runtime_context_bridge(engine):
    component, item = _create(
        engine,
        "components/CoverImage.qml",
        width=240,
        height=240,
        coverKey="album-key",
    )
    try:
        assert component.isReady()
        assert item.objectName() == "coverImage"
        assert item.property("ready") is False
    finally:
        item.deleteLater()


def test_library_albums_route_uses_premium_host(engine):
    component, item = _create(
        engine,
        "pages/library/AlbumGridPage.qml",
        width=1200,
        height=760,
    )
    try:
        assert component.isReady()
        assert item.objectName() == "albumGridPage"
        host = item.findChild(QObject, "albumViewHost")
        assert host is not None
        modes_value = host.property("viewModes")
        modes = (
            modes_value.toVariant()
            if hasattr(modes_value, "toVariant")
            else modes_value
        )
        assert len(modes) == 5
    finally:
        item.deleteLater()


def test_compatibility_album_route_no_longer_uses_legacy_selector():
    source = (QML_ROOT / "pages/library/AlbumGridPage.qml").read_text(
        encoding="utf-8"
    )
    assert "AlbumViewHost" in source
    assert "LibraryViewSelector" not in source
    assert "AlbumListView" not in source


@pytest.mark.parametrize(("width", "expected_count"), ((900, 5), (1400, 7)))
def test_coverflow_caps_visible_delegates(engine, qapp, width, expected_count):
    component, item = _create(
        engine,
        "pages/library/album/AlbumCoverFlowView.qml",
        width=width,
        height=760,
    )
    try:
        assert component.isReady()
        qapp.processEvents()
        path_view = item.findChild(QObject, "albumCoverFlowPathView")
        assert path_view is not None
        assert path_view.property("pathItemCount") == expected_count
    finally:
        item.deleteLater()


def test_coverflow_has_no_fake_rectangular_reflection():
    source = (
        QML_ROOT / "pages/library/album/AlbumCoverFlowView.qml"
    ).read_text(encoding="utf-8")
    assert "scale: -1" not in source
    assert "height: root.coverSize * 0.28" not in source
    assert 'objectName: "albumCoverFlowPathView"' in source
