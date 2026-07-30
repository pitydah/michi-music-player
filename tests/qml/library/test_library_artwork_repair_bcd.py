from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from ui_qml.models.AlbumListModel import AlbumListModel
from ui_qml.models.ArtistListModel import ArtistListModel
from ui_qml_bridge.route_registry import ROUTES


REPO_ROOT = Path(__file__).resolve().parents[3]
QML_ROOT = REPO_ROOT / "ui_qml"
LIBRARY_ROOT = QML_ROOT / "pages" / "library"


def test_album_and_artist_models_expose_namespaced_cover_roles() -> None:
    album_model = AlbumListModel(query_service=MagicMock())
    album_model._items = [{"album_key": "blue-train", "cover_key": "blue-train"}]
    artist_model = ArtistListModel(query_service=MagicMock())
    artist_model._items = [{"name": "Coltrane", "cover_key": "best-album"}]

    album_index = album_model.index(0, 0)
    artist_index = artist_model.index(0, 0)

    assert album_model.data(album_index, album_model.AlbumKeyRole) == "blue-train"
    assert album_model.data(album_index, album_model.CoverKeyRole) == "album:blue-train"
    assert artist_model.data(artist_index, artist_model.CoverKeyRole) == "album:best-album"


def test_namespaced_cover_roles_are_not_prefixed_twice() -> None:
    album_model = AlbumListModel(query_service=MagicMock())
    album_model._items = [{"cover_key": "album:already-canonical"}]

    assert album_model.data(
        album_model.index(0, 0), album_model.CoverKeyRole
    ) == "album:already-canonical"


def test_collection_detail_route_and_page_expose_paginated_query_contract() -> None:
    route = ROUTES["library.collection_detail"]
    source = (QML_ROOT / "pages/library/CollectionDetailPage.qml").read_text(encoding="utf-8")
    collections = (LIBRARY_ROOT / "CollectionsPage.qml").read_text(encoding="utf-8")

    assert route["status"] == "functional"
    assert route["params"]["collection_id"]["required"] is True
    assert "queryCollection(root.collectionId, root.pageSize, root.items.length)" in source
    assert "function fetchMore()" in source
    assert 'navigateWithParams("library.collection_detail"' in collections


def test_library_pages_do_not_use_unicode_glyphs_as_icons() -> None:
    forbidden = ("▶", "♡", "☐", "☑", "✕", "↗", "◎", "▣", "♫", "▰")
    offenders = {
        path.relative_to(LIBRARY_ROOT): glyph
        for path in LIBRARY_ROOT.rglob("*.qml")
        for glyph in forbidden
        if glyph in path.read_text(encoding="utf-8")
    }

    assert offenders == {}


def test_album_controls_share_one_toolbar() -> None:
    host = (LIBRARY_ROOT / "album/AlbumViewHost.qml").read_text(encoding="utf-8")
    grid = (LIBRARY_ROOT / "album/AlbumGridView.qml").read_text(encoding="utf-8")

    assert 'objectName: "albumLibraryToolbar"' in host
    assert 'objectName: "albumViewSelector"' in host
    assert 'objectName: "albumSortSelector"' in host
    assert 'objectName: "albumDensitySelector"' in host
    assert "densityToolbar" not in grid
