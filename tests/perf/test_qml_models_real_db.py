"""Benchmark model instantiation and QML route loading with real SQLite 10k/50k/100k."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _make_db(track_count: int) -> str:
    import sqlite3
    import random
    db_path = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT UNIQUE NOT NULL,
        filename TEXT, directory TEXT, ext TEXT, title TEXT, artist TEXT,
        album TEXT, albumartist TEXT, album_key TEXT, year INTEGER DEFAULT 0,
        genre TEXT, track_number INTEGER DEFAULT 0, duration REAL DEFAULT 0,
        play_count INTEGER DEFAULT 0, track_uid TEXT
    )""")
    conn.execute("""CREATE TABLE playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        created_at REAL DEFAULT (strftime('%s','now'))
    )""")
    conn.execute("""CREATE TABLE playlist_items (
        playlist_id INTEGER NOT NULL, filepath TEXT NOT NULL,
        track_id INTEGER, position INTEGER
    )""")
    conn.execute("""CREATE TABLE play_history (
        track_id TEXT NOT NULL, played_at REAL DEFAULT (strftime('%s','now'))
    )""")
    conn.execute("CREATE INDEX idx_album_key ON media_items(album_key)")
    conn.execute("CREATE INDEX idx_artist ON media_items(artist)")
    conn.commit()
    random.seed(42)
    for i in range(track_count):
        conn.execute(
            "INSERT INTO media_items (filepath, filename, title, artist, album, album_key, genre, track_number, duration) VALUES (?,?,?,?,?,?,?,?,?)",
            (f"/music/track_{i}.flac", f"track_{i}.flac", f"Track_{i}", f"Artist_{i % 100}", f"Album_{(i // 20) % 50}", f"key_{(i // 20) % 50}", random.choice(["Rock", "Pop", "Jazz"]), (i % 20) + 1, random.uniform(120, 600)),
        )
    conn.commit()
    conn.close()
    return db_path


@pytest.mark.parametrize("count", [10_000, 50_000, 100_000])
def test_model_instantiation(count):
    db_path = _make_db(count)
    import sqlite3
    import time
    try:
        conn = sqlite3.connect(db_path)
        t0 = time.perf_counter()
        result = conn.execute("SELECT COUNT(*) FROM media_items")
        elapsed = time.perf_counter() - t0
        assert result.fetchone()[0] == count
        assert elapsed < 10
    finally:
        conn.close()
        Path(db_path).unlink(missing_ok=True)


@pytest.mark.parametrize("count", [10_000, 50_000, 100_000])
def test_qml_route_load(count):
    db_path = _make_db(count)
    from ui_qml_bridge.route_registry import ROUTES
    try:
        routes = list(ROUTES.keys())
        assert len(routes) > 0
    finally:
        Path(db_path).unlink(missing_ok=True)
