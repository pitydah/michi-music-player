"""Benchmark: insert 100k tracks."""
import time
import sqlite3
import pytest
@pytest.mark.perf
def test_perf_library_100k():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, filepath TEXT, title TEXT, artist TEXT, album TEXT, duration REAL)")
    t0 = time.time()
    for i in range(100000):
        conn.execute("INSERT INTO media_items VALUES (?,?,?,?,?,?)",
                     (i, f"/music/track_{i}.flac", f"Track {i}", f"Artist {i%1000}", f"Album {i%500}", 200.0))
    conn.commit()
    t = time.time() - t0
    conn.close()
    assert t < 60, f"Too slow: {t:.1f}s"
    print(f"OK: 100k inserts in {t:.1f}s")
