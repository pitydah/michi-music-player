"""Benchmark with real SQLite: 10k and 50k tracks.

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

import pytest


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
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            cover_path TEXT DEFAULT '', description TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS playlist_items (
            playlist_id INTEGER NOT NULL REFERENCES playlists(id),
            filepath TEXT NOT NULL, track_id INTEGER REFERENCES media_items(id),
            position INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS play_history (
            track_id TEXT NOT NULL,
            device TEXT DEFAULT 'desktop',
            played_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS queue_state (
            id INTEGER PRIMARY KEY, filepath TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_media_items_album_key ON media_items(album_key);
        CREATE INDEX IF NOT EXISTS idx_media_items_artist ON media_items(artist);
        CREATE INDEX IF NOT EXISTS idx_media_items_deleted ON media_items(deleted_at);
        CREATE INDEX IF NOT EXISTS idx_play_history_played_at ON play_history(played_at);
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
    conn.execute("PRAGMA query_only=0")
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


# ── Scenario functions ──

def _scenario_startup(conn, db_path):
    conn2 = sqlite3.connect(db_path)
    conn2.execute("SELECT 1")
    conn2.close()


def _scenario_count(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.count_tracks()


def _scenario_model_init(conn, db_path):
    from ui_qml.models.BasePagedListModel import BasePagedListModel
    from ui_qml_bridge.query_executor import QueryExecutor
    qe = QueryExecutor()
    BasePagedListModel(page_size=100, query_executor=qe)


def _scenario_first_page(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.fetch_tracks(0, 100)


def _scenario_five_pages(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    for p in range(5):
        qs.fetch_tracks(p * 100, 100)


def _scenario_fts_search(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.count_tracks(search="Track")


def _scenario_like_fallback(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.count_tracks(search="Track_5")


def _scenario_artist_filter(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.count_tracks(artist="Artist_1")


def _scenario_album_filter(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.count_tracks(album="Album_0_0")


def _scenario_sort(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    qs.fetch_tracks(0, 100, sort="year", asc=False)


def _scenario_album_detail(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    detail = qs.fetch_album_detail("key_0")
    assert detail is not None


def _scenario_history_count(conn, db_path):
    cur = conn.execute("SELECT COUNT(*) FROM play_history")
    return cur.fetchone()[0]


def _scenario_history_page(conn, db_path):
    cur = conn.execute("SELECT track_id, played_at FROM play_history ORDER BY played_at DESC LIMIT 100")
    return len(cur.fetchall())


def _run_simple_db_scenario(conn, db_path, fn):
    return fn(conn, db_path)


def _scenario_mix_favorites(conn, db_path):
    cur = conn.execute("SELECT id, filepath, title, artist, album, duration, play_count, track_uid "
                       "FROM media_items WHERE deleted_at IS NULL AND play_count > 0 "
                       "ORDER BY play_count DESC LIMIT 100")
    return len(cur.fetchall())


def _scenario_mix_recent(conn, db_path):
    cur = conn.execute("SELECT m.id, m.filepath, m.title, m.artist, m.album, m.duration, m.track_uid "
                       "FROM media_items m JOIN play_history h ON m.filepath = h.track_id "
                       "WHERE m.deleted_at IS NULL "
                       "GROUP BY m.id ORDER BY MAX(h.played_at) DESC LIMIT 100")
    return len(cur.fetchall())


def _scenario_playlists_list(conn, db_path):
    cur = conn.execute("SELECT id, name, cover_path, description FROM playlists ORDER BY name")
    return len(cur.fetchall())


def _scenario_global_search_fts(conn, db_path):
    from ui_qml_bridge.library_query_service import LibraryQueryService
    qs = LibraryQueryService(None, db_path=db_path)
    results = qs.search_fts("Track_1", limit=50)
    return len(results)


SCENARIOS_10K_50K = [
    ("startup_db", _scenario_startup, 150, 300),
    ("count", _scenario_count, 80, 150),
    ("model_init", _scenario_model_init, 150, 300),
    ("first_page", _scenario_first_page, 250, 450),
    ("five_pages", _scenario_five_pages, 500, 1000),
    ("fts_search", _scenario_fts_search, 250, 500),
    ("like_fallback", _scenario_like_fallback, 400, 800),
    ("artist_filter", _scenario_artist_filter, 100, 200),
    ("album_filter", _scenario_album_filter, 100, 200),
    ("sort", _scenario_sort, 200, 400),
    ("album_detail", _scenario_album_detail, 100, 200),
    ("history_count", _scenario_history_count, 50, 100),
    ("history_page", _scenario_history_page, 50, 100),
    ("mix_favorites", _scenario_mix_favorites, 100, 200),
    ("mix_recent", _scenario_mix_recent, 100, 200),
    ("playlists_list", _scenario_playlists_list, 50, 100),
    ("global_search_fts", _scenario_global_search_fts, 200, 400),
]

SCENARIOS_CRITICAL = [
    ("count", _scenario_count, 500),
    ("first_page", _scenario_first_page, 750),
    ("fts_search", _scenario_fts_search, 900),
    ("album_detail", _scenario_album_detail, 300),
]


BENCHMARK_RESULTS = {}


@pytest.mark.parametrize("track_count", [10_000, 50_000])
class TestQmlRealDB:
    @pytest.fixture(autouse=True)
    def _setup(self, track_count):
        self.track_count = track_count
        self.results_key = f"benchmark_{track_count}"

    def _run_and_record(self, name: str, scenario_fn, threshold_10k: float, threshold_50k: float):
        threshold = threshold_10k if self.track_count == 10_000 else threshold_50k
        scored = _run_scenario(scenario_fn, self.track_count, repeats=3)
        median_s = scored["median"]
        assert median_s < threshold / 1000.0, (
            f"{name} median={median_s:.3f}s exceeds threshold {threshold}ms"
        )
        if self.results_key not in BENCHMARK_RESULTS:
            BENCHMARK_RESULTS[self.results_key] = {}
        BENCHMARK_RESULTS[self.results_key][name] = scored

    def test_startup_db(self):
        self._run_and_record("startup_db", _scenario_startup, 150, 300)

    def test_count(self):
        self._run_and_record("count", _scenario_count, 80, 150)

    def test_model_init(self):
        self._run_and_record("model_init", _scenario_model_init, 150, 300)

    def test_first_page(self):
        self._run_and_record("first_page", _scenario_first_page, 250, 450)

    def test_five_pages(self):
        self._run_and_record("five_pages", _scenario_five_pages, 500, 1000)

    def test_fts_search(self):
        self._run_and_record("fts_search", _scenario_fts_search, 250, 500)

    def test_like_fallback(self):
        self._run_and_record("like_fallback", _scenario_like_fallback, 400, 800)

    def test_artist_filter(self):
        self._run_and_record("artist_filter", _scenario_artist_filter, 100, 200)

    def test_album_filter(self):
        self._run_and_record("album_filter", _scenario_album_filter, 100, 200)

    def test_sort(self):
        self._run_and_record("sort", _scenario_sort, 200, 400)

    def test_album_detail(self):
        self._run_and_record("album_detail", _scenario_album_detail, 100, 200)

    def test_history_count(self):
        scored = _run_scenario(_scenario_history_count, self.track_count, repeats=3)
        BENCHMARK_RESULTS.setdefault(self.results_key, {})["history_count"] = scored

    def test_history_page(self):
        scored = _run_scenario(_scenario_history_page, self.track_count, repeats=3)
        BENCHMARK_RESULTS.setdefault(self.results_key, {})["history_page"] = scored

    def test_mix_favorites(self):
        scored = _run_scenario(_scenario_mix_favorites, self.track_count, repeats=3)
        BENCHMARK_RESULTS.setdefault(self.results_key, {})["mix_favorites"] = scored

    def test_mix_recent(self):
        scored = _run_scenario(_scenario_mix_recent, self.track_count, repeats=3)
        BENCHMARK_RESULTS.setdefault(self.results_key, {})["mix_recent"] = scored

    def test_playlists_list(self):
        scored = _run_scenario(_scenario_playlists_list, self.track_count, repeats=3)
        BENCHMARK_RESULTS.setdefault(self.results_key, {})["playlists_list"] = scored

    def test_global_search_fts(self):
        scored = _run_scenario(_scenario_global_search_fts, self.track_count, repeats=3)
        BENCHMARK_RESULTS.setdefault(self.results_key, {})["global_search_fts"] = scored
