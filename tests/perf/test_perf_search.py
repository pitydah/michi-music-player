"""Benchmark: FTS5 search."""
import sqlite3
import time
import pytest
@pytest.mark.perf
def test_perf_search():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE VIRTUAL TABLE media_fts USING fts5(title, artist)")
    for i in range(100000):
        conn.execute("INSERT INTO media_fts VALUES (?,?)", (f"Track {i}", f"Artist {i%1000}"))
    t0 = time.time()
    rows = conn.execute("SELECT rowid FROM media_fts WHERE media_fts MATCH ?", ("Track 42",)).fetchall()
    t = time.time() - t0
    conn.close()
    assert len(rows) > 0
    print(f"OK: search {len(rows)} results in {t:.3f}s")
