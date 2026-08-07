"""Vertical slice: real composition + real PlaylistService on a tmp DB.

create_playlist / delete_playlist are driven through the ACTUAL assistant
composition (assistant_initializer + register_builtin_tools + ToolRegistryV2
with gateway-evidence capabilities) and the playlist is read back through
PlaylistService to prove the tool reached a real operation.

This guards the two historical killer bugs:
- attribute mismatch (playlist vs playlists) → CAPABILITY_UNAVAILABLE
- delete_playlist → create_playlist (wrong operation on real data)
"""
from __future__ import annotations

from core.assistant_initializer import create_assistant_composition
from core.playlist_service import PlaylistService
from library.library_db import LibraryDB

TRACKS = [
    ("/m/one.flac", "one.flac", "/m", ".flac", "One", "Artist A", "Album A", "album-a", "uid-1"),
    ("/m/two.flac", "two.flac", "/m", ".flac", "Two", "Artist A", "Album A", "album-a", "uid-2"),
    ("/m/three.flac", "three.flac", "/m", ".flac", "Three", "Artist B", "Album B", "album-b", "uid-3"),
]


def _make_db() -> LibraryDB:
    db = LibraryDB(":memory:")
    db.conn.executemany(
        "INSERT INTO media_items "
        "(filepath, filename, directory, ext, kind, title, artist, album, "
        "album_key, track_uid) VALUES (?, ?, ?, ?, 'audio', ?, ?, ?, ?, ?)",
        TRACKS,
    )
    db.conn.commit()
    return db


def _stack():
    db = _make_db()
    playlist_service = PlaylistService(db=db)
    comp = create_assistant_composition(
        library_db=db,
        playlist_service=playlist_service,
        library_query_service=None,
    )
    return db, playlist_service, comp


def test_create_playlist_tool_reaches_real_service() -> None:
    db, playlist_service, comp = _stack()

    result = comp.tool_registry.execute(
        "create_playlist", {"name": "Mi Lista", "track_ids": ["1", "2"]}
    )

    assert result.ok is True, f"create_playlist failed: {result.error}"
    pid = int(result.data["playlist"]["id"])
    assert result.data["added"] == 2

    readback = playlist_service.list()
    assert any(p["id"] == pid and p["name"] == "Mi Lista" for p in readback)
    detail = playlist_service.get_detail(pid)
    assert detail["count"] == 2


def test_delete_playlist_tool_removes_for_real() -> None:
    db, playlist_service, comp = _stack()

    created = playlist_service.create("Para Borrar")
    assert created["ok"]
    pid = int(created["id"])

    result = comp.tool_registry.execute("delete_playlist", {"playlist_id": str(pid)})

    assert result.ok is True, f"delete_playlist failed: {result.error}"
    assert result.data.get("status") == "DELETED"
    assert playlist_service.list() == [], "playlist still exists after delete"
    detail = playlist_service.get_detail(pid)
    assert detail.get("ok") is False, "get_detail should fail for deleted playlist"


def test_delete_playlist_never_creates() -> None:
    """The historical bug: delete_playlist → create_playlist."""
    db, playlist_service, comp = _stack()
    before = playlist_service.list()

    comp.tool_registry.execute("delete_playlist", {"playlist_id": "9999"})

    assert playlist_service.list() == before, (
        "delete_playlist created a playlist — wrong mapping!"
    )


def test_playlist_capabilities_are_available_with_real_services() -> None:
    _db, _pl, comp = _stack()
    caps = comp.capability_resolver.resolve("playlist.modify")
    assert caps["playlist.modify"].available is True
