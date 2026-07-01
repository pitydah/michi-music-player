"""Tests for playlist smart engine."""
from __future__ import annotations

import json
import sqlite3

from library.playlists.playlist_smart_engine import evaluate_rules, preview_smart_playlist


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, filename TEXT, directory TEXT, ext TEXT, kind TEXT,
        title TEXT, artist TEXT, album TEXT, genre TEXT,
        year INTEGER, duration REAL, sample_rate INTEGER, bit_depth INTEGER, bitrate INTEGER,
        bpm REAL, track_uid TEXT, content_hash TEXT
    )""")
    conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind, title, artist, genre, year, duration, sample_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("/m/rock1.flac", "r1.flac", "/m", "flac", "audio", "Rock Song", "Artist A", "Rock", 2020, 200.0, 44100))
    conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind, title, artist, genre, year, duration, sample_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("/m/rock2.flac", "r2.flac", "/m", "flac", "audio", "Rock 2", "Artist B", "Rock", 2021, 180.0, 96000))
    conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind, title, artist, genre, year, duration, sample_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("/m/jazz1.flac", "j1.flac", "/m", "flac", "audio", "Jazz Song", "Artist C", "Jazz", 2019, 300.0, 44100))
    conn.commit()
    return conn


class TestSmartEngine:

    def test_evaluate_by_genre(self):
        db = _make_db()
        rules = json.dumps({"rules": [{"field": "genre", "op": "equals", "value": "Rock"}]})
        ids = evaluate_rules(rules, db)
        assert len(ids) == 2

    def test_evaluate_by_year_range(self):
        db = _make_db()
        rules = json.dumps({"rules": [{"field": "year", "op": "greater_than", "value": "2020"}]})
        ids = evaluate_rules(rules, db)
        assert len(ids) == 1

    def test_preview_smart(self):
        db = _make_db()
        rules = json.dumps({"rules": [{"field": "genre", "op": "equals", "value": "Jazz"}]})
        ids = preview_smart_playlist(rules, db)
        assert len(ids) == 1

    def test_multiple_rules(self):
        db = _make_db()
        rules = json.dumps({"rules": [
            {"field": "genre", "op": "equals", "value": "Rock"},
            {"field": "sample_rate", "op": "greater_than", "value": "48000"},
        ]})
        ids = evaluate_rules(rules, db)
        assert len(ids) == 1

    def test_invalid_rule_safe(self):
        db = _make_db()
        rules = json.dumps({"rules": [{"field": "nonexistent", "op": "equals", "value": "x"}]})
        ids = evaluate_rules(rules, db)
        assert isinstance(ids, list)

    def test_empty_rules_safe(self):
        db = _make_db()
        ids = evaluate_rules("", db)
        assert ids == []
