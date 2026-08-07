"""Favorites integrity (FASE 4, P0): identity, inheritance, bulk, readback.

The canonical track identity is track_uid; group favorites inherit to their
tracks with origin/parent_entity; bulk never aborts on a missing id; every
mutation reads back against the requested state.
"""
from __future__ import annotations

import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.favorite_service import FavoriteService
from library.schema import Schema

TRACKS = [
    (1, "/m/a.flac", "a.flac", "/m", "album-a", "Artist A", "uid-a"),
    (2, "/m/b.flac", "b.flac", "/m", "album-a", "Artist A", "uid-b"),
    (3, "/m/c.flac", "c.flac", "/m", "album-b", "Artist B", "uid-c"),
]


def _seed(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO media_items "
        "(id, filepath, filename, directory, ext, kind, title, artist, album, "
        "album_key, track_uid) VALUES (?, ?, ?, ?, 'flac', 'audio', ?, ?, ?, ?, ?)",
        [
            (rid, fp, fn, d, f"Track {rid}", artist, album_key, album_key, uid)
            for rid, fp, fn, d, album_key, artist, uid in TRACKS
        ],
    )
    conn.commit()


@pytest.fixture
def stack():
    conn = sqlite3.connect(":memory:")
    Schema.initialize(conn)
    _seed(conn)
    db = SimpleNamespace(conn=conn)
    return conn, FavoriteService(db=db)


def test_bulk_mixed_ids(stack) -> None:
    """A missing id is not_found; the batch completes without KeyError/abort."""
    conn, svc = stack
    result = svc.set_track_favorites_bulk([1, 2, 999], True)
    assert result.ok is True
    assert result.data["applied"] == 2
    assert result.data["not_found"] == 1
    assert result.data["count"] == 2
    assert result.data["results"] == {1: "applied", 2: "applied", 999: "not_found"}
    rows = conn.execute(
        "SELECT entity_id, origin FROM favorites WHERE entity_type = 'track'"
    ).fetchall()
    assert sorted(rows) == [("uid-a", "direct"), ("uid-b", "direct")]

    removed = svc.set_track_favorites_bulk([1, 2, 999], False)
    assert removed.ok is True
    assert removed.data["applied"] == 2
    assert removed.data["not_found"] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM favorites WHERE entity_type = 'track'"
    ).fetchone()[0] == 0


def test_direct_favorite_inside_favorited_album(stack) -> None:
    """Track X has a direct favorite; album unfavorite leaves it intact."""
    conn, svc = stack
    assert svc.set_favorite("track", "uid-a", "track_1", True).ok is True
    assert svc.set_album_favorite("album-a", True).ok is True
    assert svc.set_album_favorite("album-a", False).ok is True

    assert svc.is_favorite("track", "uid-a") is True
    assert svc.is_favorite("track", "uid-b") is False
    assert svc.is_favorite("album", "album-a") is False
    row = conn.execute(
        "SELECT entity_id, origin FROM favorites WHERE entity_type = 'track'"
    ).fetchone()
    assert row == ("uid-a", "direct")


def test_unfavorite_album_removes_only_inherited(stack) -> None:
    """Unfavorite removes inherited rows + direct album row, keeps direct tracks."""
    conn, svc = stack
    assert svc.set_favorite("track", "uid-c", "track_3", True).ok is True
    assert svc.set_album_favorite("album-a", True).ok is True
    assert svc.set_album_favorite("album-a", False).ok is True

    rows = conn.execute(
        "SELECT entity_id, origin, parent_entity FROM favorites "
        "WHERE entity_type = 'track' ORDER BY entity_id"
    ).fetchall()
    assert rows == [("uid-c", "direct", None)]
    assert conn.execute(
        "SELECT COUNT(*) FROM favorites WHERE entity_type = 'album'"
    ).fetchone()[0] == 0


def test_migrated_legacy_origin() -> None:
    """Migration 9 backfills pre-existing filepath-only rows as legacy."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE favorites (track_id TEXT NOT NULL UNIQUE, "
        "device TEXT DEFAULT 'desktop', added_at REAL DEFAULT 0)"
    )
    conn.execute("INSERT INTO favorites (track_id) VALUES ('/legacy/a.flac')")
    conn.commit()

    from library.migrations import migrate

    migrate(conn)
    row = conn.execute(
        "SELECT track_id, origin, entity_id, source FROM favorites"
    ).fetchone()
    assert row == ("/legacy/a.flac", "migrated_legacy", "", "legacy")


def test_identity_duplicates(stack) -> None:
    """Same track via filepath and track_uid dedups to one canonical row."""
    conn, svc = stack
    assert svc.set_favorite("track", "/m/a.flac", "", True).ok is True
    assert svc.set_favorite("track", "uid-a", "track_1", True).ok is True

    rows = conn.execute(
        "SELECT entity_id, origin FROM favorites WHERE entity_type = 'track'"
    ).fetchall()
    assert rows == [("uid-a", "direct")]


def test_missing_track_uid(stack) -> None:
    """A track without track_uid is NOT_FOUND; no filepath fallback."""
    conn, svc = stack
    conn.execute(
        "INSERT INTO media_items (id, filepath, filename, directory, ext, kind, "
        "title, track_uid) VALUES (9, '/m/nouid.flac', 'nouid.flac', '/m', "
        "'flac', 'audio', 'No Uid', '')"
    )
    conn.commit()

    result = svc.set_favorite("track", "/m/nouid.flac", "", True)
    assert result.ok is False
    assert result.code == "NOT_FOUND"

    bulk = svc.set_track_favorites_bulk([9], True)
    assert bulk.ok is True
    assert bulk.data["not_found"] == 1
    assert bulk.data["applied"] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM favorites"
    ).fetchone()[0] == 0


def test_relocated_path_survives(stack) -> None:
    """Canonical favorites keyed by track_uid survive a filepath change."""
    conn, svc = stack
    assert svc.set_favorite("track", "uid-a", "track_1", True).ok is True
    conn.execute(
        "UPDATE media_items SET filepath = '/moved/a.flac', "
        "filename = 'a.flac', directory = '/moved' WHERE id = 1"
    )
    conn.commit()

    assert svc.is_favorite("track", "uid-a") is True
    row = conn.execute(
        "SELECT entity_id, track_id FROM favorites WHERE entity_type = 'track'"
    ).fetchone()
    assert row == ("uid-a", "/m/a.flac")
    assert svc.list_favorites("track")[0]["entity_id"] == "uid-a"


def test_readback_mismatch(stack) -> None:
    """Divergence between requested and effective state → READBACK_MISMATCH."""
    conn, svc = stack
    with patch.object(svc, "is_favorite", return_value=False):
        result = svc.set_favorite("track", "uid-a", "track_1", True)
    assert result.ok is False
    assert result.code == "READBACK_MISMATCH"
    assert result.data["details"]["requested"] is True
    assert result.data["details"]["effective"] is False
    assert result.data["details"]["entity_id"] == "uid-a"
    assert conn.execute(
        "SELECT COUNT(*) FROM favorites WHERE entity_type = 'track'"
    ).fetchone()[0] == 1


def test_atomic_mode(stack) -> None:
    """Atomic bulk with an invalid id rolls back everything; zero applied."""
    conn, svc = stack
    result = svc.set_track_favorites_bulk([1, 2, 999], True, atomic=True)
    assert result.ok is True
    assert result.data["applied"] == 0
    assert result.data["not_found"] == 1
    assert result.data["rolled_back"] is True
    assert conn.execute(
        "SELECT COUNT(*) FROM favorites"
    ).fetchone()[0] == 0

    clean = svc.set_track_favorites_bulk([1, 2], True, atomic=True)
    assert clean.ok is True
    assert clean.data["applied"] == 2
    assert conn.execute(
        "SELECT COUNT(*) FROM favorites"
    ).fetchone()[0] == 2
