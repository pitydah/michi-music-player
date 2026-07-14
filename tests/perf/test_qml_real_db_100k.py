"""Benchmark with real SQLite: 100k tracks (critical scenarios only).

Scenarios: count, first page, FTS search, album detail.
Each scenario runs 3 times, reporting median and p95.
"""
from __future__ import annotations

import contextlib
import math
import random
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path

def _schema_sql() -> str:
    return """
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
        );
        CREATE INDEX IF NOT EXISTS idx_media_items_album_key ON media_items(album_key);
        CREATE INDEX IF NOT EXISTS idx_media_items_artist ON media_items(artist);
        CREATE INDEX IF NOT EXISTS idx_media_items_deleted ON media_items(deleted_at);
    """


def _populate_tracks(conn: sqlite3.Connection, count: int, seed: int = 42):
    random.seed(seed)
    genres = ["Rock", "Pop", "Jazz", "Classical", "Electronic", "Hip Hop", "Blues", "Reggae", "Folk", "Metal"]
    folders = ["/music", "/music/Rock", "/music/Jazz", "/music/Pop"]
    for i in range(count):
        folder = folders[i % len(folders)]
        ext = random.choice(["flac", "mp3", "wav", "aac"])
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


def _rebuild_fts(conn: sqlite3.Connection):
    try:
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS media_fts USING fts5("
                     "title, artist, album, genre, content='media_items', content_rowid='id')")
        conn.execute("INSERT INTO media_fts(rowid, title, artist, album, genre) "
                     "SELECT id, title, artist, album, genre FROM media_items WHERE deleted_at IS NULL")
        conn.commit()
    except Exception:
        pass


def _make_real_db(count: int) -> tuple[sqlite3.Connection, str]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.executescript(_schema_sql())
    _populate_tracks(conn, count)
    _rebuild_fts(conn)
    return conn, db_path


def _make_scored(values: list[float]) -> dict:
    if len(values) < 2:
        return {"median": round(values[0], 3) if values else 0, "p95": round(values[0], 3) if values else 0,
                "min": round(values[0], 3) if values else 0, "max": round(values[0], 3) if values else 0,
                "runs": len(values)}
    sorted_v = sorted(values)
    median = statistics.median(values)
    p95_idx = min(int(math.ceil(0.95 * len(sorted_v))) - 1, len(sorted_v) - 1)
    p95 = sorted_v[p95_idx]
    return {"median": round(median, 3), "p95": round(p95, 3),
            "min": round(sorted_v[0], 3), "max": round(sorted_v[-1], 3),
            "runs": len(values)}


def _run_scenario(scenario_fn, count: int, repeats: int = 3) -> dict:
    times = []
    for _ in range(repeats):
        conn, db_path = _make_real_db(count)
        try:
            t0 = time.perf_counter()
            scenario_fn(conn, db_path)
            elapsed = time.perf_counter() - t0
            times.append(elapsed)
        finally:
            with contextlib.suppress(Exception):
                conn.close()
            Path(db_path).unlink(missing_ok=True)
    return _make_scored(times)


def _scenario_count(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.count_tracks()


def _scenario_first_page(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.fetch_tracks(0, 100)


def _scenario_fts_search(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.count_tracks(search="Track")


def _scenario_album_detail(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    detail = qs.fetch_album_detail("key_0")
    assert detail is not None


THRESHOLDS = {
    "count": 500,
    "first_page": 750,
    "fts_search": 900,
    "album_detail": 300,
}

BENCHMARK_RESULTS = {}
TRACK_COUNT = 100_000


class TestQmlRealDB100k:
    def test_count(self):
        scored = _run_scenario(_scenario_count, TRACK_COUNT)
        assert scored["median"] < THRESHOLDS["count"] / 1000.0
        BENCHMARK_RESULTS["count"] = scored

    def test_first_page(self):
        scored = _run_scenario(_scenario_first_page, TRACK_COUNT)
        assert scored["median"] < THRESHOLDS["first_page"] / 1000.0
        BENCHMARK_RESULTS["first_page"] = scored

    def test_fts_search(self):
        scored = _run_scenario(_scenario_fts_search, TRACK_COUNT)
        assert scored["median"] < THRESHOLDS["fts_search"] / 1000.0
        BENCHMARK_RESULTS["fts_search"] = scored

    def test_album_detail(self):
        scored = _run_scenario(_scenario_album_detail, TRACK_COUNT)
        assert scored["median"] < THRESHOLDS["album_detail"] / 1000.0
        BENCHMARK_RESULTS["album_detail"] = scored
