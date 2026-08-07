from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.library_bridge import LibraryBridge

pytestmark = [pytest.mark.qml_module("library")]

QML_LIBRARY = Path(__file__).resolve().parents[3] / "ui_qml" / "pages" / "library"


@pytest.fixture
def favorite_bridge():
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE media_items (
            id INTEGER PRIMARY KEY,
            filepath TEXT,
            album_key TEXT,
            album TEXT,
            artist TEXT,
            albumartist TEXT,
            track_uid TEXT,
            deleted_at REAL
        );
        CREATE TABLE favorites (
            track_id TEXT PRIMARY KEY,
            entity_type TEXT DEFAULT 'track',
            entity_id TEXT DEFAULT '',
            public_ref TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now')),
            source TEXT DEFAULT 'ui',
            origin TEXT NOT NULL DEFAULT 'direct',
            parent_entity TEXT
        );
        INSERT INTO media_items VALUES
            (1, '/a/one.flac', 'album-a', 'Album A', 'Artist A', 'Artist A', 'uid-1', NULL),
            (2, '/a/two.flac', 'album-a', 'Album A', 'Guest', 'Artist A', 'uid-2', NULL),
            (3, '/b/three.flac', 'album-b', 'Album B', 'Artist B', 'Artist B', 'uid-3', NULL);
        """
    )
    from core.favorite_service import FavoriteService
    query = MagicMock()
    query.search_backend = "like"
    query.count_tracks.return_value = 0
    query.count_albums.return_value = 0
    query.count_artists.return_value = 0
    bridge = LibraryBridge(
        db=SimpleNamespace(conn=connection),
        query_service=query,
        favorite_service=FavoriteService(db=SimpleNamespace(conn=connection)),
    )
    bridge._refresh_coordinator = MagicMock()
    bridge._sync_state = MagicMock()
    yield bridge, connection
    connection.close()


def test_album_favorite_uses_canonical_entity_identity(favorite_bridge):
    bridge, connection = favorite_bridge

    result = bridge.setAlbumFavorite("album-a", True)

    assert result == {"ok": True, "favorite": True, "count": 1}
    rows = connection.execute(
        "SELECT track_id, entity_type, entity_id, origin, parent_entity "
        "FROM favorites ORDER BY entity_type, entity_id"
    ).fetchall()
    assert rows == [
        ("album:album-a", "album", "album-a", "direct", None),
        ("/a/one.flac", "track", "uid-1", "inherited_album", "album-a"),
        ("/a/two.flac", "track", "uid-2", "inherited_album", "album-a"),
    ]

    # A direct track favorite outside the album is preserved on unfavorite.
    connection.execute("INSERT INTO favorites(track_id) VALUES ('/b/three.flac')")
    assert bridge.setAlbumFavorite("album-a", False)["ok"] is True
    assert connection.execute("SELECT track_id FROM favorites").fetchall() == [
        ("/b/three.flac",),
    ]


def test_artist_favorite_uses_canonical_entity_identity(favorite_bridge):
    bridge, connection = favorite_bridge

    result = bridge.setArtistFavorite("Artist A", True)

    assert result == {"ok": True, "favorite": True, "count": 1}
    rows = connection.execute(
        "SELECT track_id, entity_type, entity_id, origin "
        "FROM favorites ORDER BY entity_type, entity_id"
    ).fetchall()
    assert rows == [
        ("artist:Artist A", "artist", "Artist A", "direct"),
        ("/a/one.flac", "track", "uid-1", "inherited_artist"),
        ("/a/two.flac", "track", "uid-2", "inherited_artist"),
    ]


def test_custom_collection_is_validated_and_upserted():
    collection_service = MagicMock()
    collection_service.create.return_value = {
        "ok": True,
        "collection": {
            "id": "collection-1",
            "name": "Late-night jazz",
            "logic": "OR",
            "rules": [
                {"field": "genre", "operator": "eq", "value": "Jazz"},
                {"field": "year", "operator": "lt", "value": "1970"},
            ],
        },
    }
    bridge = LibraryBridge(query_service=MagicMock(), collection_service=collection_service)
    payload = {
        "name": "Late-night jazz",
        "matchMode": "OR",
        "rules": [
            {"field": "genre", "operator": "equals", "value": "Jazz"},
            {"field": "year", "operator": "less_than", "value": "1970"},
        ],
    }

    result = bridge.saveCollection(json.dumps(payload))

    assert result["ok"] is True
    assert result["collection"]["logic"] == "OR"
    assert len(result["collection"]["rules"]) == 2
    collection_service.create.assert_called_once()


def test_collection_editor_and_paginated_facets_are_wired():
    collections = (QML_LIBRARY / "CollectionsPage.qml").read_text()
    editor = (QML_LIBRARY / "CollectionEditorDialog.qml").read_text()
    genres = (QML_LIBRARY / "GenresPage.qml").read_text()
    composers = (QML_LIBRARY / "ComposersPage.qml").read_text()

    assert 'objectName: "createCollectionButton"' in collections
    assert "createCollection(" in collections
    assert 'value: "AND"' in editor and 'value: "OR"' in editor
    assert "rulesModel.append" in editor
    assert "function fetchMore()" in genres
    assert "root.lib.getGenres(root._genres.length, root.pageSize)" in genres
    assert "function fetchMore()" in composers
    assert "root.lib.getComposers(root._composers.length, root.pageSize)" in composers


def test_album_views_expose_state_and_host_restores_it():
    host = (QML_LIBRARY / "album" / "AlbumViewHost.qml").read_text()
    view_names = (
        "AlbumGridView.qml",
        "AlbumCoverFlowView.qml",
        "AlbumVinylWallView.qml",
        "AlbumTimelineView.qml",
        "AlbumMagazineView.qml",
    )

    assert "function saveCurrentViewState()" in host
    assert "function restoreCurrentViewState()" in host
    assert "root.saveCurrentViewState()" in host
    assert "Qt.callLater(root.restoreCurrentViewState)" in host
    for view_name in view_names:
        source = (QML_LIBRARY / "album" / view_name).read_text()
        assert "property alias scrollPosition:" in source
        assert "property alias selectionIndex:" in source
