"""Tests for playlist relinker."""
from __future__ import annotations

import sqlite3

from library.playlists.playlist_relinker import find_candidates, score_candidate


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, filename TEXT, directory TEXT, ext TEXT, kind TEXT,
        title TEXT, artist TEXT, album TEXT, duration REAL,
        track_uid TEXT, content_hash TEXT, bitrate INTEGER
    )""")
    conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind, title, artist, album, duration, track_uid, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("/m/original.flac", "original.flac", "/m", "flac", "audio", "Song", "Artist", "Album", 200.0, "uid-abc", "hash-123"))
    conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind, title, artist, album, duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("/m/relocated.flac", "original.flac", "/m", "flac", "audio", "Song", "Artist", "Album", 200.0))
    conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind, title, artist, album, duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("/m/other.flac", "other.flac", "/m", "flac", "audio", "Other", "Someone", "Diff", 180.0))
    conn.commit()
    return conn


def _make_lost_item():
    from library.playlists.playlist_models import PlaylistTrackRef
    return PlaylistTrackRef(
        track_id=0, filepath="/m/original.flac", title="Song", artist="Artist",
        album="Album", duration=200.0, track_uid="uid-abc", content_hash="hash-123",
    )


class TestPlaylistRelinker:

    def test_find_candidates_by_uid(self):
        conn = _make_db()
        item = _make_lost_item()
        cands = find_candidates(item, conn)
        uid = [c for c in cands if c.match_type == "uid"]
        assert len(uid) >= 1

    def test_find_candidates_by_filename(self):
        conn = _make_db()
        item = _make_lost_item()
        item.track_uid = "nonexistent_uid"
        item.content_hash = ""
        item.title = "UniqueTitleNoMatch"
        item.artist = "UniqueArtistNoMatch"
        cands = find_candidates(item, conn)
        filename = [c for c in cands if c.match_type == "filename"]
        assert len(filename) >= 1

    def test_find_candidates_by_title_artist(self):
        conn = _make_db()
        item = _make_lost_item()
        item.track_uid = ""
        item.content_hash = ""
        item.filepath = "/gone/missing.flac"
        cands = find_candidates(item, conn)
        ta = [c for c in cands if c.match_type == "title_artist"]
        assert len(ta) >= 1

    def test_score_candidate(self):
        conn = _make_db()
        item = _make_lost_item()
        cands = find_candidates(item, conn)
        if cands:
            assert score_candidate(item, cands[0]) >= 60
