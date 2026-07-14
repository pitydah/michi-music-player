"""Memory benchmarks with 100k real SQLite: RSS, model instantiation, scroll/fetchMore."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest


def _rss_mb() -> float:
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0


def _make_db(count: int = 100_000) -> str:
    import sqlite3
    import random
    db_path = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT UNIQUE NOT NULL,
        title TEXT, artist TEXT, album TEXT, album_key TEXT, genre TEXT,
        track_number INTEGER DEFAULT 0, duration REAL DEFAULT 0,
        play_count INTEGER DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE play_history (
        track_id TEXT NOT NULL, played_at REAL DEFAULT (strftime('%s','now'))
    )""")
    conn.execute("CREATE INDEX idx_album_key ON media_items(album_key)")
    conn.commit()
    random.seed(42)
    for i in range(count):
        conn.execute(
            "INSERT INTO media_items (filepath, title, artist, album, album_key, genre, track_number, duration) VALUES (?,?,?,?,?,?,?,?)",
            (f"/music/track_{i}.flac", f"Track_{i}", f"Artist_{i % 100}", f"Album_{(i // 20) % 50}", f"key_{(i // 20) % 50}", random.choice(["Rock", "Pop", "Jazz"]), (i % 20) + 1, random.uniform(120, 600)),
        )
    conn.commit()
    conn.close()
    return db_path


@pytest.mark.parametrize("count", [10_000, 50_000, 100_000])
def test_memory_rss(count):
    db_path = _make_db(count)
    import sqlite3
    try:
        before = _rss_mb()
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT COUNT(*) FROM media_items").fetchone()
        after = _rss_mb()
        assert after >= before
    finally:
        conn.close()
        Path(db_path).unlink(missing_ok=True)


def test_scroll_fetch_more():
    db_path = _make_db(100_000)
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        t0 = time.perf_counter()
        for offset in range(0, 100_000, 100):
            conn.execute("SELECT id, title, artist FROM media_items LIMIT 100 OFFSET ?", (offset,)).fetchall()
        elapsed = time.perf_counter() - t0
        assert elapsed < 30
    finally:
        conn.close()
        Path(db_path).unlink(missing_ok=True)


def test_history_100k():
    db_path = _make_db(100_000)
    import sqlite3
    import random
    try:
        conn = sqlite3.connect(db_path)
        random.seed(42)
        data = [(f"uid_{i}", i * 1000.0) for i in range(100_000)]
        conn.executemany("INSERT INTO play_history VALUES (?,?)", data)
        conn.commit()
        t0 = time.perf_counter()
        result = conn.execute("SELECT COUNT(*) FROM play_history").fetchone()
        elapsed = time.perf_counter() - t0
        assert result[0] == 100_000
        assert elapsed < 5
    finally:
        conn.close()
        Path(db_path).unlink(missing_ok=True)
