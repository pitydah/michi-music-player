"""Tests for library database operations."""

import os
import tempfile


def test_db_init():
    from library.library_db import LibraryDB
    db = LibraryDB(":memory:")
    assert db.get_stats()["total"] == 0
    db.close()


def test_add_file():
    from library.library_db import LibraryDB
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"dummy")
        path = f.name
    db = LibraryDB(":memory:")
    db.add_file(path)
    assert db.get_stats()["audio"] == 1
    os.unlink(path)
    db.close()


def test_playlist_crud():
    from library.library_db import LibraryDB
    db = LibraryDB(":memory:")
    pid = db.create_playlist("Test")
    assert pid > 0
    playlists = db.get_playlists()
    assert any(p["name"] == "Test" for p in playlists)
    db.delete_playlist(pid)
    assert not any(p["name"] == "Test" for p in db.get_playlists())
    db.close()


def test_scanner():
    from library.library_db import LibraryDB
    from library.indexer import Indexer
    import os
    with tempfile.TemporaryDirectory() as d:
        for ext in [".mp3", ".txt", ".ogg"]:
            path = os.path.join(d, f"test{ext}")
            with open(path, "w") as f:
                f.write("")
        db = LibraryDB(":memory:")
        idx = Indexer(db, d)
        idx.run()
        assert db.get_stats()["audio"] == 2  # mp3 + ogg, no txt
        db.close()
