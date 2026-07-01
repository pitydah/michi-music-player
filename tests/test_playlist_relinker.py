"""Tests for playlist relinker."""
from __future__ import annotations

import sqlite3
from library.playlists.playlist_relinker import find_candidates, score_candidate
from library.playlists.playlist_models import PlaylistTrackRef


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE media_items (id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, filename TEXT, directory TEXT, ext TEXT, kind TEXT,
        title TEXT, artist TEXT, album TEXT, duration REAL,
        track_uid TEXT, content_hash TEXT, bitrate INTEGER)""")
    conn.execute("INSERT INTO media_items VALUES (1,'/m/orig.flac','orig.flac','/m','flac','audio','Song','Artist','Album',200.0,'uid-abc','hash-123',1411)")
    conn.execute("INSERT INTO media_items VALUES (2,'/m/reloc.flac','orig.flac','/m','flac','audio','Song','Artist','Album',200.0,NULL,NULL,NULL)")
    conn.execute("INSERT INTO media_items VALUES (3,'/m/other.flac','other.flac','/m','flac','audio','Other','Someone','Diff',180.0,NULL,NULL,NULL)")
    conn.commit()
    return conn


def _make_lost_item():
    return PlaylistTrackRef(track_id=0, filepath="/m/orig.flac", title="Song", artist="Artist", album="Album", duration=200.0, track_uid="uid-abc", content_hash="hash-123")


class TestPlaylistRelinker:
    def test_find_by_uid(self):
        conn = _make_db()
        cands = find_candidates(_make_lost_item(), conn)
        assert any(c.match_type == "uid" for c in cands)

    def test_find_by_filename(self):
        conn = _make_db()
        item = _make_lost_item()
        item.track_uid = "nonexistent"
        item.content_hash = ""
        item.title = "UniqueNoMatch"
        item.artist = "UniqueNoMatch"
        cands = find_candidates(item, conn)
        assert any(c.match_type == "filename" for c in cands)

    def test_score_candidate(self):
        conn = _make_db()
        cands = find_candidates(_make_lost_item(), conn)
        if cands:
            assert score_candidate(_make_lost_item(), cands[0]) >= 60
