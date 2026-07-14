from __future__ import annotations

import sqlite3
import pytest

from core.library.repositories.genre_repository import GenreRepository


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE IF NOT EXISTS media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, title TEXT, artist TEXT, album TEXT,
        albumartist TEXT DEFAULT '', album_key TEXT DEFAULT '',
        year INTEGER DEFAULT 0, genre TEXT DEFAULT '',
        duration REAL DEFAULT 0, track_number INTEGER DEFAULT 0,
        track_uid TEXT DEFAULT '', deleted_at REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS track_genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id INTEGER NOT NULL,
        genre TEXT NOT NULL,
        canonical_genre TEXT NOT NULL DEFAULT '',
        UNIQUE(track_id, genre)
    )""")
    c.commit()
    return c


@pytest.fixture
def repo(conn):
    return GenreRepository(lambda: conn)


def _insert_track(conn, filepath, title="Song", genre="Rock"):
    cur = conn.execute(
        "INSERT INTO media_items (filepath, title) VALUES (?,?)",
        (filepath, title),
    )
    return cur.lastrowid


def _add_genre(conn, track_id, canonical="Rock"):
    conn.execute(
        "INSERT OR IGNORE INTO track_genres (track_id, genre, canonical_genre) "
        "VALUES (?,?,?)",
        (track_id, canonical, canonical),
    )
    conn.commit()


class TestGenreRepository:
    def test_empty(self, repo):
        assert repo.count() == 0
        assert repo.get_all() == []

    def test_count(self, conn, repo):
        tid = _insert_track(conn, "/a.flac")
        _add_genre(conn, tid, "Rock")
        assert repo.count() == 1

    def test_get_all(self, conn, repo):
        tid1 = _insert_track(conn, "/a.flac")
        tid2 = _insert_track(conn, "/b.flac")
        _add_genre(conn, tid1, "Rock")
        _add_genre(conn, tid2, "Jazz")
        genres = repo.get_all()
        assert len(genres) == 2
        names = {g["name"] for g in genres}
        assert names == {"Rock", "Jazz"}

    def test_get_page(self, conn, repo):
        for i, g in enumerate(["Rock", "Jazz", "Classical"]):
            tid = _insert_track(conn, f"/{i}.flac")
            _add_genre(conn, tid, g)
        page = repo.get_page(limit=2)
        assert len(page) == 2

    def test_get_page_sorted(self, conn, repo):
        for i, g in enumerate(["Rock", "Jazz", "Classical"]):
            tid = _insert_track(conn, f"/{i}.flac")
            _add_genre(conn, tid, g)
        page = repo.get_page(sort="name", asc=True)
        assert page[0]["name"] == "Classical"

    def test_tracks_for_genre(self, conn, repo):
        tid = _insert_track(conn, "/a.flac")
        _add_genre(conn, tid, "Rock")
        tracks = repo.tracks_for_genre("Rock")
        assert len(tracks) == 1
        assert tracks[0]["track_id"] == tid
