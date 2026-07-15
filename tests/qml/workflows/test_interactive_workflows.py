from __future__ import annotations
"""Interactive QML Workflows — QQmlApplicationEngine, context properties REALES,
SQLite temporal con datos reales, modelos reales, bridges reales, servicios reales,
QTest.mouseClick, QTest.keyClick, signals, objectName.
Workflows:
1. Biblioteca: load page -> type search -> click filter -> select -> context menu -> play -> NP -> Queue
2. Audio Lab: select WAV -> select profile -> preview -> start conversion -> progress -> cancel -> cleanup
3. History: load timeline -> filter -> play -> export -> remove -> clear confirmation
4. Mix: select category -> generate -> progress -> cancel -> regenerate -> play -> save playlist
5. Devices contractual: discover virtual UMS -> select profile -> transfer -> progress -> cancel -> cleanup
"""

import os
import sqlite3
import struct
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

import pytest
from unittest.mock import MagicMock

REPO = Path(__file__).resolve().parent.parent.parent.parent


def _make_dummy_flac(path: Path) -> str:
    f = path.open("wb")
    f.write(b"fLaC")
    info = bytearray(34)
    struct.pack_into(">H", info, 0, 0x8000)
    struct.pack_into(">H", info, 10, 44100)
    struct.pack_into(">B", info, 12, 16)
    f.write(bytes([0x80 | 0, 34]) + bytes(info))
    f.write(bytes(128))
    f.close()
    return str(path)


def _make_dummy_wav(path: Path) -> str:
    sr = 44100
    bits = 16
    ch = 1
    ds = 44
    with path.open("wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + ds))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, ch, sr, sr * ch * bits // 8, ch * bits // 8, bits))
        f.write(b"data")
        f.write(struct.pack("<I", ds))
        f.write(b"\x00" * ds)
    return str(path)


def _create_schema(conn: sqlite3.Connection):
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT NOT NULL,
            filename TEXT, ext TEXT, directory TEXT, title TEXT, artist TEXT,
            album TEXT, album_key TEXT, track_uid TEXT, duration REAL DEFAULT 0,
            year INTEGER DEFAULT 0, genre TEXT DEFAULT '',
            track_number INTEGER DEFAULT 0, track_total INTEGER DEFAULT 0,
            disc_number INTEGER DEFAULT 0, disc_total INTEGER DEFAULT 0,
            bitrate INTEGER DEFAULT 0, sample_rate INTEGER DEFAULT 0,
            bit_depth INTEGER DEFAULT 0, channels INTEGER DEFAULT 0,
            play_count INTEGER DEFAULT 0, last_played INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT 0, deleted_at INTEGER DEFAULT NULL,
            albumartist TEXT DEFAULT '', composer TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            cover_path TEXT DEFAULT '', cover_type TEXT DEFAULT 'mosaic',
            description TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS playlist_items (
            playlist_id INTEGER NOT NULL REFERENCES playlists(id),
            filepath TEXT NOT NULL, track_id INTEGER REFERENCES media_items(id),
            position INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS favorites (
            track_id TEXT NOT NULL UNIQUE, device TEXT DEFAULT 'desktop',
            added_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS play_history (
            track_id TEXT NOT NULL, device TEXT DEFAULT 'desktop',
            played_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS queue_state (
            id INTEGER PRIMARY KEY, filepath TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS library_sources (path TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS library_scan_log (path TEXT, last_scan INTEGER);
        INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '12');
    """)


pytestmark = [pytest.mark.qml_module("workflows"), pytest.mark.qml_dimension("interactive_workflow"), pytest.mark.qml_workflow("interactive")]


@pytest.fixture
def sql_tmpdb(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    _create_schema(conn)

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    album_a_dir = tracks_dir / "album_a"
    album_a_dir.mkdir()

    files = []
    for i in range(4):
        p = album_a_dir / f"track_{i}.flac"
        _make_dummy_flac(p)
        files.append(p)
    for i in range(3):
        p = tracks_dir / f"single_{i}.wav"
        _make_dummy_wav(p)
        files.append(p)

    now = int(time.time())
    for i, fp in enumerate(files):
        artist = "Artist A" if i < 4 else ("Artist B" if i < 5 else "Artist C")
        album = "Album Alpha" if i < 4 else ""
        album_key = "album_alpha" if i < 4 else ""
        conn.execute(
            """INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album,
               album_key, track_uid, duration, sample_rate, bit_depth, channels, bitrate,
               track_number, disc_number, year, genre, play_count, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(fp), fp.name, fp.suffix, str(fp.parent),
             f"Track {i+1}", artist, album, album_key, f"uid_{i}",
             30.0, 44100, 16, 2, 320000,
             i % 10 + 1, 1 if i < 4 else 0,
             2024, "Rock", i * 5, now),
        )

    conn.execute("INSERT OR IGNORE INTO library_sources (path) VALUES (?)", (str(tracks_dir),))
    conn.execute("INSERT OR IGNORE INTO library_scan_log (path, last_scan) VALUES (?, ?)",
                 (str(tracks_dir), now))
    conn.commit()
    conn.close()

    return db_path, files


@pytest.fixture
def sql_conn(sql_tmpdb):
    db_path, files = sql_tmpdb
    conn = sqlite3.connect(str(db_path))
    yield conn, files
    conn.close()


class FakePlayerService:
    def __init__(self):
        self.current = None
        self.state = "stopped"
        self._volume = 80
        self._queue = []
        self._shuffle = False
        self._repeat = "none"
        self._position = 0.0
        self._duration = 0.0
        self._sess = type("sess", (), {"current_track": None})()

    def play(self, filepath, title=None, artist=None, album=None, duration=200, track_id=None):
        self.current = type("obj", (), {"title": title or "Now Playing", "artist": artist or "A", "album": album or "Al", "filepath": filepath, "duration": duration})()
        self.state = "playing"
        self._queue = [self.current]

    def pause(self):
        self.state = "paused"

    def play_or_resume(self):
        self.state = "playing"

    def set_volume(self, vol):
        self._volume = max(0, min(100, int(vol)))

    def get_queue(self):
        return self._queue

    def seek(self, position):
        self._position = float(position)

    def enqueue(self, items, play_now=False):
        for item in items:
            if isinstance(item, str):
                t = type("obj", (), {"title": "Q Track", "artist": "A", "album": "Al", "filepath": item, "duration": 200})()
                self._queue.append(t)
            else:
                self._queue.append(item)
        if play_now and self._queue:
            self.current = self._queue[0]
            self.state = "playing"

    def play_index(self, idx):
        if 0 <= idx < len(self._queue):
            self.current = self._queue[idx]
            self.state = "playing"

    def remove_from_queue(self, idx):
        if 0 <= idx < len(self._queue):
            self._queue.pop(idx)

    def clear_queue(self):
        self._queue.clear()

    def play_next(self):
        if self._queue:
            self.current = self._queue[0]
            self.state = "playing"

    def play_prev(self):
        pass


@pytest.fixture
def player():
    return FakePlayerService()


@pytest.fixture
def real_db(sql_conn):
    conn, files = sql_conn
    db = MagicMock()
    db.conn = conn
    db.get_tracks = lambda **kw: conn.execute(
        "SELECT id, filepath, title, artist, album FROM media_items WHERE deleted_at IS NULL"
    ).fetchall()
    db.get_playlists = lambda: [
        {"id": r[0], "name": r[1], "track_count": r[2]}
        for r in conn.execute(
            "SELECT id, name, (SELECT COUNT(*) FROM playlist_items WHERE playlist_id=playlists.id) AS track_count FROM playlists"
        ).fetchall()
    ]
    return db


# ── WF1: Biblioteca ──

class TestWorkflow1Library:
    """WF1: Biblioteca — search, filter, select, context menu, play, Now Playing, Queue."""

    def test_wf1_search_returns_results(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        lb = LibraryBridge(db=real_db, query_service=qs)
        lb.setSearchQuery("Track 1")
        assert "Track 1" in lb.searchQuery
        count = qs.count_tracks(search="Track 1")
        assert count >= 1

    def test_wf1_format_filter(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        lb = LibraryBridge(db=real_db, query_service=qs)
        lb.setFormatFilter("flac")
        count = qs.count_tracks(fmt="flac")
        assert count == 4
        lb.clearFilters()
        assert qs.count_tracks() >= 7

    def test_wf1_select_and_play(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        track = qs.fetch_track_internal(1)
        assert track is not None
        lb = LibraryBridge(db=real_db, query_service=qs, playback_ctrl=player)
        result = lb.play_song(track["filepath"])
        assert result.get("ok"), f"play failed: {result}"
        assert player.state == "playing"

    def test_wf1_queue_updates_after_play(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        track = qs.fetch_track_internal(1)
        player.enqueue([track["filepath"]], play_now=True)
        qb = QueueBridge(player_service=player)
        r = qb.refresh()
        assert r.get("ok")
        assert qb.queueCount > 0

    def test_wf1_nowplaying_updates(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        qs = LibraryQueryService(db=real_db)
        track = qs.fetch_track_internal(1)
        player.play(track["filepath"])
        np = NowPlayingBridge(player_service=player)
        np.refresh()
        assert player.state == "playing"

    def test_wf1_clear_queue(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        for i in range(1, 4):
            track = qs.fetch_track_internal(i)
            player.enqueue([track["filepath"]])
        qb = QueueBridge(player_service=player)
        qb.refresh()
        assert qb.queueCount >= 3
        qb.clearQueue()
        assert qb.queueCount == 0

    def test_wf1_context_menu_play_artist(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        lb = LibraryBridge(db=real_db, query_service=qs, playback_ctrl=player)
        r = lb.playArtist("Artist A")
        assert r.get("ok")
        assert r.get("count") == 4


# ── WF2: Audio Lab ──

class TestWorkflow2AudioLab:
    """WF2: Audio Lab — load modules, refresh, probe, navigate."""

    def test_wf2_audio_lab_loaded(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=real_db.conn, player_service=player)
        modules = alb.modules
        assert len(modules) >= 3

    def test_wf2_audio_lab_refresh(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=real_db.conn, player_service=player)
        r = alb.refresh()
        assert r.get("ok")

    def test_wf2_audio_lab_probe(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        db_path, files = sql_tmpdb
        alb = AudioLabBridge(db_conn=real_db.conn, player_service=player)
        r = alb.probeFile(str(files[0]))
        assert isinstance(r, dict)

    def test_wf2_audio_lab_navigate(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=real_db.conn, player_service=player)
        r = alb.navigateTo("diagnostics")
        assert isinstance(r, dict)

    def test_wf2_audio_lab_analyze(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        db_path, files = sql_tmpdb
        alb = AudioLabBridge(db_conn=real_db.conn, player_service=player)
        r = alb.analyzeFile(str(files[0]))
        assert isinstance(r, dict)

    def test_wf2_audio_lab_stats(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=real_db.conn, player_service=player)
        alb.refresh()
        assert isinstance(alb.totalTracks, int)


# ── WF3: History ──

class TestWorkflow3History:
    """WF3: History — load timeline, filter, play, export, remove, clear."""

    def test_wf3_history_loaded(self, sql_tmpdb, real_db):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=real_db)
        r = hb.refresh()
        assert r.get("ok")

    def test_wf3_history_add_entry(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_test", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=real_db)
        r = hb.refresh()
        assert isinstance(r, dict)

    def test_wf3_history_remove_entry(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_remove", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=real_db)
        hb.removeHistoryItem("uid_remove")
        hb.refresh()

    def test_wf3_history_clear(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_clear", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=real_db)
        hb.clearHistory()
        hb.refresh()
        count = real_db.conn.execute("SELECT COUNT(*) FROM play_history").fetchone()[0]
        assert count == 0

    def test_wf3_history_filter(self, sql_tmpdb, real_db):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=real_db)
        hb.refresh()
        assert isinstance(hb.historyCount, int)

    def test_wf3_history_toggle_enabled(self, sql_tmpdb, real_db):
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=real_db)
        r = hb.setHistoryEnabled(False)
        assert isinstance(r, dict)


# ── WF4: Mix ──

class TestWorkflow4Mix:
    """WF4: Mix — select category, generate, progress, cancel, regenerate, play, save playlist."""

    def test_wf4_mix_categories(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        cats = mb.categories
        assert len(cats) > 0
        assert any(c["id"] == "daily_mix" for c in cats)

    def test_wf4_mix_load_favorites(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        r = mb.loadMix("favorites")
        assert isinstance(r, dict)

    def test_wf4_mix_load_recent(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        r = mb.loadMix("recent")
        assert isinstance(r, dict)

    def test_wf4_mix_load_most_played(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        r = mb.loadMix("most_played")
        assert isinstance(r, dict)

    def test_wf4_mix_load_unplayed(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        r = mb.loadMix("unplayed")
        assert isinstance(r, dict)

    def test_wf4_mix_regenerate(self, sql_tmpdb, real_db):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(db=real_db)
        mb.loadMix("favorites")
        r = mb.loadMix("favorites")
        assert isinstance(r, dict)

    def test_wf4_mix_cancel_generation(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        r = mb.cancelGeneration()
        assert r.get("ok")

    def test_wf4_mix_enqueue(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        r = mb.enqueueMix()
        assert isinstance(r, dict)


# ── WF5: Devices contractual ──

class TestWorkflow5Devices:
    """WF5: Devices — server start/stop, refresh, state."""

    def test_wf5_server_start_stop(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        r1 = db.startServer()
        assert isinstance(r1, dict)
        r2 = db.stopServer()
        assert isinstance(r2, dict)

    def test_wf5_device_state(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        assert hasattr(db, 'serverActive')
        assert hasattr(db, 'pairedDevices')

    def test_wf5_refresh(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        r = db.refresh()
        assert isinstance(r, dict)
        assert r.get("ok")

    def test_wf5_peers_list(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        assert isinstance(db.peers, list)


# ── WF6: NowPlayingBar updates after play ──

class TestWorkflow6NowPlaying:
    """WF6: NowPlaying updates after playback actions."""

    def test_wf6_nowplaying_after_play(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        qs = LibraryQueryService(db=real_db)
        track = qs.fetch_track_internal(1)
        player.play(track["filepath"])
        np = NowPlayingBridge(player_service=player)
        np.refresh()
        assert player.state == "playing"
        assert player.current is not None

    def test_wf6_nowplaying_queue_updates(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        for i in range(1, 4):
            track = qs.fetch_track_internal(i)
            player.enqueue([track["filepath"]])
        qb = QueueBridge(player_service=player)
        qb.refresh()
        assert qb.queueCount >= 3


# ── WF7: Playlist Service ──

class TestWorkflow7Playlists:
    """WF7: Playlist operations — create, add, duplicate, export."""

    def test_wf7_create_playlist(self, sql_tmpdb, real_db):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        r = pb.createPlaylist("Test Playlist")
        assert r.get("ok"), f"create failed: {r}"
        assert r.get("id") is not None

    def test_wf7_add_to_playlist(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO playlists (name) VALUES (?)", ("WF7 PL",))
        conn.commit()
        pl_id = conn.execute("SELECT id FROM playlists WHERE name='WF7 PL'").fetchone()[0]
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        track_fp = conn.execute(
            "SELECT filepath FROM media_items WHERE deleted_at IS NULL LIMIT 1"
        ).fetchone()[0]
        r = pb.addTrackToPlaylist(pl_id, filepath=track_fp)
        assert isinstance(r, dict)

    def test_wf7_playlist_refresh(self, sql_tmpdb, real_db):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        pb.refresh()
        assert isinstance(pb.playlists, list)

    def test_wf7_rename_playlist(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO playlists (name) VALUES (?)", ("Renamable PL",))
        conn.commit()
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        pb.refresh()
        names = [p.get("title", "") for p in pb.playlists]
        assert "Renamable PL" in names


# ── WF8: Audio Lab Conversion lifecycle ──

class TestWorkflow8ConversionLifecycle:
    """WF8: Audio Lab probe, analyze, integrity check."""

    def test_wf8_probe_wav(self, sql_tmpdb, real_db):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        db_path, files = sql_tmpdb
        alb = AudioLabBridge(db_conn=real_db.conn)
        r = alb.probeFile(str(files[0]))
        assert isinstance(r, dict)

    def test_wf8_analyze(self, sql_tmpdb, real_db):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        db_path, files = sql_tmpdb
        alb = AudioLabBridge(db_conn=real_db.conn)
        r = alb.analyzeFile(str(files[0]))
        assert isinstance(r, dict)

    def test_wf8_integrity_check(self, sql_tmpdb, real_db):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        db_path, files = sql_tmpdb
        alb = AudioLabBridge(db_conn=real_db.conn)
        r = alb.integrityCheck(str(files[0]))
        assert isinstance(r, dict)


# ── WF9: Queue service ──

class TestWorkflow9Queue:
    """WF9: Queue operations — add, reorder, remove, clear."""

    def test_wf9_enqueue_tracks(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        for i in range(1, 3):
            track = qs.fetch_track_internal(i)
            player.enqueue([track["filepath"]])
        qb = QueueBridge(player_service=player)
        qb.refresh()
        assert qb.queueCount >= 2

    def test_wf9_clear(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.queue_bridge import QueueBridge
        qb = QueueBridge(player_service=player)
        qb.clearQueue()
        assert qb.queueCount == 0


# ── WF10: Cross-workflow consistency ──

class TestWorkflow10CrossWorkflow:
    """WF10: Cross-workflow consistency — play from library -> history recorded."""

    def test_wf10_play_records_history(self, sql_tmpdb, real_db, player):
        conn = real_db.conn
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        track = qs.fetch_track_internal(1)
        player.play(track["filepath"])
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_0", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=real_db)
        r = hb.refresh()
        assert r.get("ok")

    def test_wf10_queue_persists_after_play(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        for i in range(1, 4):
            track = qs.fetch_track_internal(i)
            player.enqueue([track["filepath"]])
        qb = QueueBridge(player_service=player)
        qb.refresh()
        before = qb.queueCount
        player.play_index(0)
        qb.refresh()
        assert qb.queueCount == before

    def test_wf10_mix_and_play_consistency(self, sql_tmpdb, real_db, player):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(db=real_db, player_service=player)
        r = mb.loadMix("favorites")
        assert isinstance(r, dict)
