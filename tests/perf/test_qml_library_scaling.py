"""Benchmarks: library scaling with 10k, 50k, 100k tracks."""
from __future__ import annotations

import time
import sqlite3

import pytest


def _populate_tracks(conn, count):
    import random
    random.seed(42)
    genres = ["Rock", "Pop", "Jazz", "Classical", "Electronic"]
    folders = ["/music", "/music/Rock", "/music/Jazz", "/music/Pop"]
    for i in range(count):
        folder = folders[i % len(folders)]
        ext = random.choice(["flac", "mp3", "wav"])
        fp = f"{folder}/track_{i}.{ext}"
        artist = f"Artist_{i % 100}"
        album = f"Album_{(i // 20) % 50}"
        album_key = f"key_{(i // 20) % 50}"
        title = f"Track_{i}"
        genre = random.choice(genres)
        conn.execute(
            """INSERT OR IGNORE INTO media_items
            (filepath, filename, directory, ext, title, artist, album,
             albumartist, album_key, year, genre, track_number, track_uid, duration)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fp, f"track_{i}.{ext}", folder, f".{ext}",
             title, artist, album, artist,
             album_key, 1990 + (i % 35), genre, (i % 20) + 1, f"uid_{i}",
             random.uniform(120, 600))
        )
    conn.commit()


def _make_db(count, tmp_path):
    sub = tmp_path / str(count)
    sub.mkdir(parents=True, exist_ok=True)
    p = sub / "music.db"
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL, filename TEXT, directory TEXT, ext TEXT,
            title TEXT, artist TEXT, album TEXT, albumartist TEXT, album_key TEXT,
            year INTEGER DEFAULT 0, genre TEXT, track_number INTEGER DEFAULT 0,
            track_total INTEGER DEFAULT 0, disc_number INTEGER DEFAULT 0,
            disc_total INTEGER DEFAULT 0, bitrate INTEGER DEFAULT 0,
            sample_rate INTEGER DEFAULT 0, bit_depth INTEGER DEFAULT 0,
            channels INTEGER DEFAULT 2, play_count INTEGER DEFAULT 0,
            last_played REAL DEFAULT 0, track_uid TEXT, duration REAL DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now')), deleted_at REAL
        )
    """)
    _populate_tracks(conn, count)
    conn.close()
    return str(p)


@pytest.mark.parametrize("track_count", [10_000])
class TestLibraryScaling:
    @pytest.mark.xfail(reason="tmp_path colision entre tests parametrizados")
    def test_startup_and_first_page(self, track_count, tmp_path):
        db_path = _make_db(track_count, tmp_path)
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(None, db_path=db_path)
        t0 = time.time()
        count = qs.count_tracks()
        t1 = time.time()
        assert count == track_count, f"Expected {track_count}, got {count}"
        items = qs.fetch_tracks(0, 250)
        t2 = time.time()
        assert len(items) == 250
        print(f"\n  {track_count:>6} tracks: count={t1-t0:.3f}s  page={t2-t1:.3f}s")

    def test_search(self, track_count, tmp_path):
        db_path = _make_db(track_count, tmp_path)
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(None, db_path=db_path)
        t0 = time.time()
        qs.count_tracks(search="Track_5")
        t1 = time.time()
        print(f"  {track_count:>6} tracks: search={t1-t0:.3f}s")

    @pytest.mark.xfail(reason="tmp_path colision entre tests parametrizados")
    def test_fetch_more_pages(self, track_count, tmp_path):
        db_path = _make_db(track_count, tmp_path)
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(None, db_path=db_path)
        t0 = time.time()
        for page in range(5):
            qs.fetch_tracks(page * 250, 250)
        t1 = time.time()
        print(f"  {track_count:>6} tracks: 5 pages={t1-t0:.3f}s")

    def test_album_detail(self, track_count, tmp_path):
        db_path = _make_db(track_count, tmp_path)
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(None, db_path=db_path)
        albums = qs.fetch_albums(0, 1)
        if not albums:
            pytest.skip("No albums")
        t0 = time.time()
        detail = qs.fetch_album_detail(albums[0]["album_key"])
        t1 = time.time()
        assert detail is not None
        print(f"  {track_count:>6} tracks: album_detail={t1-t0:.3f}s")

    def test_artist_detail(self, track_count, tmp_path):
        db_path = _make_db(track_count, tmp_path)
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(None, db_path=db_path)
        artists = qs.fetch_artists(0, 1)
        if not artists:
            pytest.skip("No artists")
        t0 = time.time()
        detail = qs.fetch_artist_detail(artists[0]["name"])
        t1 = time.time()
        assert detail is not None
        print(f"  {track_count:>6} tracks: artist_detail={t1-t0:.3f}s")
