"""Tests for playlist smart engine."""
from __future__ import annotations

import json
import sqlite3
from library.playlists.playlist_smart_engine import evaluate_rules, preview_smart_playlist


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE media_items (id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, filename TEXT, directory TEXT, ext TEXT, kind TEXT,
        title TEXT, artist TEXT, album TEXT, genre TEXT,
        year INTEGER, duration REAL, sample_rate INTEGER, bit_depth INTEGER, bitrate INTEGER,
        bpm REAL, track_uid TEXT, content_hash TEXT)""")
    conn.execute("INSERT INTO media_items VALUES (1,'/m/r1.flac','r1.flac','/m','flac','audio','Rock Song','Artist A','Album R','Rock',2020,200.0,44100,16,1411,120.0,'uid1','h1')")
    conn.execute("INSERT INTO media_items VALUES (2,'/m/r2.flac','r2.flac','/m','flac','audio','Rock 2','Artist B','Album R2','Rock',2021,180.0,96000,24,2304,140.0,'uid2','h2')")
    conn.execute("INSERT INTO media_items VALUES (3,'/m/j1.flac','j1.flac','/m','flac','audio','Jazz Song','Artist C','Album J','Jazz',2019,300.0,44100,16,1411,80.0,'uid3','h3')")
    conn.commit()
    return conn


class TestSmartEngine:
    def test_by_genre(self):
        db = _make_db()
        ids = evaluate_rules(json.dumps({"rules": [{"field": "genre", "op": "equals", "value": "Rock"}]}), db)
        assert len(ids) == 2

    def test_by_year(self):
        db = _make_db()
        ids = evaluate_rules(json.dumps({"rules": [{"field": "year", "op": "greater_than", "value": "2020"}]}), db)
        assert len(ids) == 1

    def test_preview(self):
        db = _make_db()
        ids = preview_smart_playlist(json.dumps({"rules": [{"field": "genre", "op": "equals", "value": "Jazz"}]}), db)
        assert len(ids) == 1

    def test_multiple_rules(self):
        db = _make_db()
        ids = evaluate_rules(json.dumps({"rules": [{"field": "genre", "op": "equals", "value": "Rock"}, {"field": "sample_rate", "op": "greater_than", "value": "48000"}]}), db)
        assert len(ids) == 1

    def test_empty_rules_safe(self):
        db = _make_db()
        assert evaluate_rules("", db) == []
