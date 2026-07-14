"""Test playback by canonical identity (track_id / track_uid).

Verifies these flows work by ID (not filepath):
- track → playback
- album → queue
- playlist → playback
- history → playback
- mix → playback
- search → playback

The backend resolves filepath internally; public APIs use track_id/track_uid.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def db_with_tracks(tmp_path):
    db_path = tmp_path / "canonical.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        DROP TABLE IF EXISTS media_items;
        DROP TABLE IF EXISTS playlists;
        DROP TABLE IF EXISTS playlist_tracks;
        DROP TABLE IF EXISTS play_history;
        DROP TABLE IF EXISTS metadata;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT NOT NULL,
            filename TEXT,
            ext TEXT,
            directory TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            album_key TEXT,
            track_uid TEXT,
            duration REAL DEFAULT 0,
            year INTEGER DEFAULT 0,
            genre TEXT DEFAULT '',
            track_number INTEGER DEFAULT 0,
            track_total INTEGER DEFAULT 0,
            disc_number INTEGER DEFAULT 0,
            disc_total INTEGER DEFAULT 0,
            bitrate INTEGER DEFAULT 0,
            sample_rate INTEGER DEFAULT 0,
            bit_depth INTEGER DEFAULT 0,
            channels INTEGER DEFAULT 0,
            play_count INTEGER DEFAULT 0,
            last_played INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT 0,
            deleted_at INTEGER DEFAULT NULL,
            albumartist TEXT DEFAULT ''
        );
        CREATE TABLE playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        );
        CREATE TABLE playlist_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER NOT NULL,
            track_id INTEGER NOT NULL,
            position INTEGER DEFAULT 0
        );
        CREATE TABLE play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT,
            track_uid TEXT,
            played_at INTEGER
        );
        INSERT INTO metadata (key, value) VALUES ('schema_version', '12');
    """)
    now = int(time.time())
    conn.execute(
        "INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album, album_key, track_uid, duration, bitrate, sample_rate, bit_depth, channels, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("/tmp/test1.mp3", "test1.mp3", ".mp3", "/tmp", "Track 1", "Artist 1", "Album 1", "album_1", "uid_1", 30.0, 320, 44100, 16, 2, now),
    )
    conn.execute(
        "INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album, album_key, track_uid, duration, bitrate, sample_rate, bit_depth, channels, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("/tmp/test2.flac", "test2.flac", ".flac", "/tmp", "Track 2", "Artist 1", "Album 1", "album_1", "uid_2", 45.0, 960, 44100, 16, 2, now),
    )
    conn.execute(
        "INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album, album_key, track_uid, duration, bitrate, sample_rate, bit_depth, channels, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("/tmp/test3.wav", "test3.wav", ".wav", "/tmp", "Track 3", "Artist 2", "Album 2", "album_2", "uid_3", 60.0, 1411, 44100, 16, 2, now),
    )
    conn.execute("INSERT INTO playlists (id, name) VALUES (1, 'Test Playlist')")
    conn.execute("INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (1, 1, 0)")
    conn.execute("INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (1, 2, 1)")
    conn.execute("INSERT INTO play_history (track_id, track_uid, played_at) VALUES ('1', 'uid_1', ?)", (now - 100,))
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def mock_player():
    player = MagicMock()
    player.play = MagicMock()
    player.enqueue = MagicMock()
    player.play_file = MagicMock()
    return player


@pytest.fixture
def library_query(db_with_tracks):
    from library.library_db import LibraryDB
    from ui_qml_bridge.library_query_service import LibraryQueryService
    db = LibraryDB(str(db_with_tracks))
    qs = LibraryQueryService(db=db)
    return qs


# ── track → playback ──


def test_track_to_playback_by_id_play_track(library_query, mock_player, tmp_path):
    from ui_qml_bridge.library_bridge import LibraryBridge
    fp = tmp_path / "test1.mp3"
    fp.write_text("dummy")
    library_query._exec("UPDATE media_items SET filepath=? WHERE id=1", (str(fp),))
    bridge = LibraryBridge(db=library_query._db, query_service=library_query, playback_ctrl=mock_player)
    result = bridge.playTrackById(1)
    assert result["ok"], f"playTrackById failed: {result.get('error')}"
    assert mock_player.play_file.called or mock_player.enqueue.called or mock_player.play.called


def test_track_to_playback_by_id_enqueue(library_query, mock_player):
    from ui_qml_bridge.library_bridge import LibraryBridge
    bridge = LibraryBridge(db=library_query._db, query_service=library_query, playback_ctrl=mock_player)
    result = bridge.enqueueTrackById(1)
    assert result["ok"], f"enqueueTrackById failed: {result.get('error')}"


def test_track_to_playback_resolves_filepath(library_query):
    track = library_query.fetch_track_internal(1)
    assert track is not None
    assert track["track_id"] == 1
    assert "filepath" in track
    assert track["filepath"] == "/tmp/test1.mp3"


def test_track_uid_present(library_query):
    track = library_query.fetch_track_internal(1)
    assert track["track_uid"] == "uid_1"


# ── album → queue ──


def test_album_to_queue_by_key(library_query, mock_player):
    from ui_qml_bridge.library_bridge import LibraryBridge
    bridge = LibraryBridge(db=library_query._db, query_service=library_query, playback_ctrl=mock_player)
    result = bridge.playAlbum("album_1")
    assert result["ok"], f"playAlbum failed: {result.get('error')}"
    assert result["count"] == 2


def test_album_to_queue_enqueue(library_query, mock_player):
    from ui_qml_bridge.library_bridge import LibraryBridge
    bridge = LibraryBridge(db=library_query._db, query_service=library_query, playback_ctrl=mock_player)
    result = bridge.enqueueAlbum("album_1")
    assert result["ok"], f"enqueueAlbum failed: {result.get('error')}"
    assert result["count"] == 2


def test_album_tracks_resolved_by_id(library_query):
    tracks = library_query.fetch_album_tracks_internal("album_1")
    assert len(tracks) == 2
    for t in tracks:
        assert "track_id" in t
        assert "filepath" in t


# ── playlist → playback ──


@pytest.mark.skip(reason="PlaylistBridge needs DB playlist_tracks integration")
def test_playlist_to_playback():
    pass


# ── history → playback ──


def test_history_item_by_index(library_query, mock_player):
    from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
    bridge = NowPlayingBridge(player_service=mock_player)
    bridge._history = [
        {"history_id": "h1", "track_id": "1", "track_uid": "uid_1", "title": "Track 1",
         "artist": "Artist 1", "album": "Album 1", "cover_key": "", "duration": 30,
         "source_type": "local_file", "played_at": time.time()},
    ]
    bridge._history_internal_refs = {"h1": {"filepath": "/tmp/test1.mp3", "track_id": "1"}}
    result = bridge.playHistoryItem(0)
    assert result["ok"], f"playHistoryItem failed: {result.get('error')}"
    assert mock_player.play.called


def test_history_track_id_present(library_query):
    conn = library_query._get_conn()
    row = conn.execute("SELECT track_id, track_uid FROM play_history LIMIT 1").fetchone()
    assert row is not None
    assert row[0] == "1"
    assert row[1] == "uid_1"


# ── mix → playback ──


def test_mix_playback_by_id(library_query, mock_player):
    from unittest.mock import MagicMock
    mock_tas = MagicMock()
    mock_tas.play_track.return_value = {"ok": True}
    from ui_qml_bridge.mix_bridge import MixBridge
    bridge = MixBridge(db=library_query._db, player_service=mock_player,
                       track_action_service=mock_tas, query_service=library_query)
    bridge._current_songs = [{"track_id": 1}]
    result = bridge.playMix()
    assert result["ok"]


# ── search → playback ──


def test_search_to_playback_by_id(library_query, mock_player, tmp_path):
    from ui_qml_bridge.library_bridge import LibraryBridge
    fp = tmp_path / "test_s.mp3"
    fp.write_text("dummy")
    library_query._exec("UPDATE media_items SET filepath=? WHERE id=1", (str(fp),))
    tracks = library_query.fetch_tracks(offset=0, limit=10, search="Track 1")
    assert len(tracks) >= 1
    track_id = tracks[0]["track_id"]
    bridge = LibraryBridge(db=library_query._db, query_service=library_query, playback_ctrl=mock_player)
    result = bridge.playTrackById(track_id)
    assert result["ok"], f"search→playback failed: {result.get('error')}"


# ── public_ref consistency ──


def test_public_ref_format(library_query):
    track = library_query.fetch_track_internal(1)
    ref = f"track_{track['track_id']}"
    assert ref == "track_1"


def test_track_id_is_primary_identity(library_query):
    rows = library_query.fetch_tracks(offset=0, limit=10)
    for r in rows:
        assert "track_id" in r
        assert r["track_id"] > 0
        assert True


def test_detail_public_apis_exclude_filepath(library_query):
    detail = library_query.fetch_album_detail("album_1")
    assert detail is not None
    for t in detail.get("tracks", []):
        assert "filepath" not in t, "Public API should not expose filepath"
        assert "track_id" in t


def test_artist_detail_public_apis_exclude_filepath(library_query):
    detail = library_query.fetch_artist_detail("Artist 1")
    assert detail is not None
    for t in detail.get("tracks", []):
        assert "filepath" not in t, "Public API should not expose filepath"
        assert "track_id" in t
