"""Tests for library database operations."""

import os
import sqlite3
import tempfile


def test_db_init():
    from library.library_db import LibraryDB
    db = LibraryDB(":memory:")
    assert db.get_stats()["total"] == 0
    db.close()


def test_db_close_prevents_queries(tmp_path):
    """close() must invalidate the connection so queries fail."""
    import pytest
    from library.library_db import LibraryDB
    db_path = str(tmp_path / "library.db")
    db = LibraryDB(db_path)
    db.close()
    with pytest.raises(sqlite3.ProgrammingError):
        db.get_all()


def test_db_close_on_file_db(tmp_path):
    """close() on a file-based DB must release the file lock."""
    from library.library_db import LibraryDB
    db_path = str(tmp_path / "library.db")
    db = LibraryDB(db_path)
    assert os.path.isfile(db_path)
    db.close()
    # After close, a new connection should be able to open the file
    import sqlite3
    conn2 = sqlite3.connect(db_path)
    conn2.row_factory = None
    row = conn2.execute("SELECT 1").fetchone()
    assert row[0] == 1
    conn2.close()


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


def test_mark_files_deleted(tmp_path):
    from library.library_db import LibraryDB
    path = str(tmp_path / "song.mp3")
    tmp_path.joinpath("song.mp3").write_bytes(b"dummy")
    db = LibraryDB(":memory:")
    try:
        db.add_file(path)
        db.mark_files_deleted([path], deleted_at=12345.0)

        deleted = db.get_deleted_since(0)
        assert any(item["filepath"] == path for item in deleted)

        deleted_after = db.get_deleted_since(12345.0)
        assert any(item["filepath"] == path for item in deleted_after)

        deleted_later = db.get_deleted_since(12346.0)
        assert not any(item["filepath"] == path for item in deleted_later)

        db.mark_files_deleted([])
    finally:
        db.close()


def test_mark_files_deleted_ignores_unknown_paths():
    from library.library_db import LibraryDB
    db = LibraryDB(":memory:")
    try:
        db.mark_files_deleted(["/path/not/in/db.flac"], deleted_at=12345.0)
        not_deleted = db.get_deleted_since(0)
        assert len(not_deleted) == 0
    finally:
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
