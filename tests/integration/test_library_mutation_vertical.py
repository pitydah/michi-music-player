"""Vertical slice: real DB + LibraryMutationService + FavoriteService + EventBus.

Favorites are set through the canonical entity identity, read back, unset, and
announced through the EventBus. The bridge layer is verified separately by
test_bridge_has_no_direct_sql; here the services own the SQL.
"""
from __future__ import annotations

import sqlite3

from core.event_bus import EventBus
from core.favorite_service import FavoriteService
from core.library_mutation_service import LibraryMutationService
from library.schema import Schema


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    Schema.initialize(conn)
    conn.executemany(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, title, artist, album, "
        "album_key, track_uid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("/m/one.flac", "one.flac", "/m", ".flac", "audio", "One",
             "Artist A", "Album A", "album-a", "uid-1"),
            ("/m/two.flac", "two.flac", "/m", ".flac", "audio", "Two",
             "Artist A", "Album A", "album-a", "uid-2"),
            ("/m/three.flac", "three.flac", "/m", ".flac", "audio", "Three",
             "Artist B", "Album B", "album-b", "uid-3"),
        ],
    )
    conn.commit()
    return conn


class _Db:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn


def _stack():
    conn = _make_db()
    db = _Db(conn)
    bus = EventBus()
    favorites = FavoriteService(db=db, event_bus=bus)
    mutation = LibraryMutationService(db=db, event_bus=bus,
                                      favorite_service=favorites)
    return conn, db, bus, favorites, mutation


def test_schema_migrates_favorite_entity_columns() -> None:
    conn = _make_db()
    columns = {r[1] for r in conn.execute("PRAGMA table_info(favorites)")}
    assert {"entity_type", "entity_id", "public_ref", "created_at", "source"} <= columns


def test_set_track_favorite_canonical_readback_and_event() -> None:
    conn, _db, bus, favorites, _mutation = _stack()
    events = []
    bus.on("favorite.set", lambda payload: events.append(payload))
    bus.on("favorite.unset", lambda payload: events.append(payload))

    result = favorites.set_favorite("track", "uid-1", "track_1", True)
    assert result.ok is True
    assert favorites.is_favorite("track", "uid-1") is True
    row = conn.execute(
        "SELECT track_id, entity_type, entity_id, public_ref FROM favorites"
    ).fetchone()
    assert row == ("/m/one.flac", "track", "uid-1", "track_1")

    unset = favorites.set_favorite("track", "uid-1", "track_1", False)
    assert unset.ok is True
    assert favorites.is_favorite("track", "uid-1") is False

    assert [e["favorite"] for e in events] == [True, False]
    assert events[0]["entity_type"] == "track"
    assert events[0]["entity_id"] == "uid-1"


def test_legacy_filepath_favorite_readback() -> None:
    _conn, db, _bus, favorites, _mutation = _stack()
    db.conn.execute(
        "INSERT INTO favorites (track_id) VALUES ('/m/one.flac')")
    db.conn.commit()
    assert favorites.is_favorite("track", "/m/one.flac") is True


def test_album_group_favorite_via_mutation_service() -> None:
    _conn, _db, bus, _favorites, mutation = _stack()
    events = []
    bus.on("favorite.set", lambda payload: events.append(payload))

    result = mutation.set_favorite("album", "album-a", "album:album-a", True)
    assert result.ok is True
    assert mutation.set_favorite("album", "album-a", "album:album-a", True).ok
    row = _conn.execute(
        "SELECT track_id, entity_type, entity_id FROM favorites"
    ).fetchone()
    assert row == ("album:album-a", "album", "album-a")
    assert events[0]["entity_type"] == "album"

    unset = mutation.set_favorite("album", "album-a", "album:album-a", False)
    assert unset.ok is True
    assert mutation.set_favorite("album", "album-a", "album:album-a", False).ok is True


def test_bulk_favorites_are_transactional_with_readback() -> None:
    conn, _db, bus, favorites, mutation = _stack()
    events = []
    bus.on("favorite.bulk", lambda payload: events.append(payload))

    result = mutation.set_track_favorites_bulk([1, 2, 3], True)
    assert result.ok is True
    assert result.data["count"] == 3
    assert favorites.counts()["total"] == 3
    assert favorites.is_favorite("track", "uid-2") is True

    removed = mutation.set_track_favorites_bulk([2, 3], False)
    assert removed.ok is True
    assert removed.data["total_favorites"] == 0
    assert favorites.is_favorite("track", "uid-2") is False
    assert favorites.is_favorite("track", "uid-1") is True
    assert len(events) == 2


def test_track_removal_is_soft_and_announced() -> None:
    conn, _db, bus, _favorites, mutation = _stack()
    events = []
    bus.on("library.tracks.removed", lambda payload: events.append(payload))

    result = mutation.remove_tracks_from_library([1, 2])
    assert result.ok is True
    assert result.data["count"] == 2
    active = conn.execute(
        "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL AND id IN (1, 2)"
    ).fetchone()[0]
    assert active == 0
    assert events[0]["track_ids"] == [1, 2]
