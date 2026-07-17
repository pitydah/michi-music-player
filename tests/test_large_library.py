"""Test library performance with large datasets."""
import sqlite3
import time

import pytest

from library.schema import Schema


BENCHMARKS = {}


def _create_large_db(num_tracks):
    conn = sqlite3.connect(":memory:")
    Schema.initialize(conn)
    artists = [f"Artist {i}" for i in range(1000)]
    albums = [f"Album {i}" for i in range(5000)]
    genres = ["Rock", "Pop", "Jazz", "Classical", "Electronic", "Hip Hop", "R&B", "Country"]
    batch = []
    for i in range(num_tracks):
        batch.append((
            f"/music/{artists[i % 1000]}/{albums[i % 5000]}/track_{i}.flac",
            f"track_{i}.flac",
            f"/music/{artists[i % 1000]}/{albums[i % 5000]}",
            "flac", "audio",
            f"Track {i}", artists[i % 1000], albums[i % 5000],
            2020 + (i % 5), genres[i % 8], 200.0 + (i % 100),
        ))
        if len(batch) >= 1000:
            conn.executemany("""
                INSERT INTO media_items
                    (filepath, filename, directory, ext, kind,
                     title, artist, album, year, genre, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            batch = []
    if batch:
        conn.executemany("""
            INSERT INTO media_items
                (filepath, filename, directory, ext, kind,
                 title, artist, album, year, genre, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
    return conn


@pytest.mark.perf
def test_insert_10000_tracks():
    start = time.time()
    conn = _create_large_db(10000)
    elapsed = time.time() - start
    count = conn.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
    conn.close()
    BENCHMARKS["insert_10000"] = elapsed
    assert count == 10000
    assert elapsed < 30


@pytest.mark.perf
def test_select_by_artist():
    conn = _create_large_db(10000)
    start = time.time()
    row = conn.execute(
        "SELECT COUNT(*) FROM media_items WHERE artist=?",
        ("Artist 42",),
    ).fetchone()
    elapsed = time.time() - start
    conn.close()
    assert row[0] > 0
    assert elapsed < 1.0
