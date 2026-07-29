from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from core.library.library_query_service import _sort_col
from ui_qml.models.AlbumListModel import AlbumListModel

pytestmark = [pytest.mark.qml_module("album_views")]

QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"
LIBRARY_ROOT = QML_ROOT / "pages/library"


@pytest.fixture
def engine(qapp):
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_ROOT))
    yield qml_engine
    qml_engine.deleteLater()


def _create(engine: QQmlEngine, relative_path: str):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    assert component.isReady(), component.errorString()
    item = component.createWithInitialProperties({"width": 1200, "height": 760})
    assert item is not None, component.errorString()
    return item, component


def test_album_grid_density_maps_all_three_sizes(engine):
    grid, component = _create(engine, "pages/library/album/AlbumGridView.qml")
    try:
        assert grid.property("density") == "regular"
        assert grid.property("minimumCardWidth") == 192

        grid.setProperty("density", "compact")
        assert grid.property("minimumCardWidth") == 152

        grid.setProperty("density", "comfortable")
        assert grid.property("minimumCardWidth") == 216
    finally:
        grid.deleteLater()
        component.deleteLater()


def test_artist_grid_density_maps_all_three_sizes(engine):
    grid, component = _create(engine, "pages/library/ArtistGridPage.qml")
    try:
        assert grid.property("density") == "regular"
        assert grid.property("minimumCardWidth") == 184

        grid.setProperty("density", "compact")
        assert grid.property("minimumCardWidth") == 152

        grid.setProperty("density", "comfortable")
        assert grid.property("minimumCardWidth") == 216
        selector = grid.findChild(object, "artistDensitySelector")
        assert selector is not None
    finally:
        grid.deleteLater()
        component.deleteLater()


def test_album_host_exposes_five_visible_sort_orders(engine):
    host, component = _create(engine, "pages/library/album/AlbumViewHost.qml")
    try:
        options_value = host.property("sortOptions")
        options = options_value.toVariant() if hasattr(options_value, "toVariant") else options_value
        assert [option["key"] for option in options] == [
            "year",
            "title",
            "artist",
            "added",
            "play_count",
        ]
        selector = host.findChild(object, "albumSortSelector")
        assert selector is not None
        assert selector.property("visible") is True
    finally:
        host.deleteLater()
        component.deleteLater()


@pytest.mark.parametrize(
    ("sort_key", "ascending"),
    (("title", True), ("artist", True), ("year", False), ("added", False), ("play_count", False)),
)
def test_album_model_refreshes_for_every_visible_sort_order(sort_key, ascending):
    query = MagicMock()
    query.count_albums.return_value = 0
    query.fetch_albums.return_value = []
    model = AlbumListModel(query_service=query)

    result = model.refreshForSort(sort_key, ascending)

    assert result == {"ok": True, "search": "", "sort": sort_key, "asc": ascending}
    query.fetch_albums.assert_called_once_with(
        offset=0,
        limit=100,
        search="",
        artist="",
        album="",
        fmt="",
        genre="",
        composer="",
        year="",
        folder="",
        favorites=False,
        unplayed=False,
        missing=False,
        sort=sort_key,
        asc=ascending,
    )


@pytest.mark.parametrize("sort_key", ("added", "play_count"))
def test_album_query_sort_keys_use_album_aggregates(sort_key):
    expression = _sort_col(sort_key, "albums")
    assert sort_key.split("_")[0] in expression.lower() or "created_at" in expression.lower()
    assert expression != "MIN(year)"


def test_library_animations_are_guarded_by_reduced_motion():
    animation_files = {
        "ArtistCard.qml",
        "SongRow.qml",
        "album/AlbumViewHost.qml",
        "album/AlbumMagazineView.qml",
        "album/AlbumVinylWallView.qml",
        "album/AlbumGridView.qml",
        "album/AlbumCoverFlowView.qml",
        "album/delegates/AlbumVinylDelegate.qml",
        "album/delegates/AlbumCoverDelegate.qml",
    }

    for relative_path in animation_files:
        source = (LIBRARY_ROOT / relative_path).read_text()
        behavior_count = source.count("Behavior on")
        assert source.count("enabled: !MichiTheme.reducedMotion") >= behavior_count, relative_path

    vinyl_wall = (LIBRARY_ROOT / "album/AlbumVinylWallView.qml").read_text()
    vinyl_delegate = (LIBRARY_ROOT / "album/delegates/AlbumVinylDelegate.qml").read_text()
    assert "running: !MichiTheme.reducedMotion &&" in vinyl_wall
    assert "running: !MichiTheme.reducedMotion &&" in vinyl_delegate
