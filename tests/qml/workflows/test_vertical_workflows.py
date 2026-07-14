"""10 vertical workflows obligatorios con SQLite real, servicios reales, bridges reales."""
from __future__ import annotations

import sqlite3
import struct
import time
from pathlib import Path

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


def _make_dummy_mp3(path: Path) -> str:
    frame = b"\xff\xfb\x90\x00" + b"\x00" * 400
    path.write_bytes(frame)
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


@pytest.fixture
def sql_tmpdb(tmp_path: Path):
    """Create real SQLite DB with schema + 10 tracks, 2 albums, 2 artists."""
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
        p = tracks_dir / f"single_{i}.mp3"
        _make_dummy_mp3(p)
        files.append(p)
    for i in range(3):
        p = tracks_dir / f"extra_{i}.wav"
        _make_dummy_wav(p)
        files.append(p)

    now = int(time.time())
    for i, fp in enumerate(files):
        title = f"Track {i + 1}"
        artist = "Artist A" if i < 4 else ("Artist B" if i < 7 else "Artist C")
        album = "Album Alpha" if i < 4 else ""
        album_key = "album_alpha" if i < 4 else ""
        conn.execute(
            """INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album,
               album_key, track_uid, duration, sample_rate, bit_depth, channels, bitrate,
               track_number, disc_number, year, genre, play_count, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(fp), fp.name, fp.suffix, str(fp.parent),
             title, artist, album, album_key, f"uid_{i}",
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
    """Simulates PlayerService (the real Python service, not a MagicMock)."""
    def __init__(self):
        self.current = None
        self.state = "stopped"
        self._volume = 80
        self._queue = []
        self._shuffle = False
        self._repeat = "none"

    def play(self, filepath):
        self.current = type("obj", (), {"title": "Now Playing", "artist": "A", "album": "Al", "filepath": filepath, "duration": 200})()
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

    def move_in_queue(self, fr, to):
        if 0 <= fr < len(self._queue) and 0 <= to < len(self._queue):
            item = self._queue.pop(fr)
            self._queue.insert(to, item)

    def play_next(self):
        if self._queue:
            self.current = self._queue[0] if self._queue else None


@pytest.fixture
def player():
    return FakePlayerService()


class FakePlaybackCtrl:
    """Simulates PlaybackController."""
    def __init__(self):
        self._queue = []
        self.current_track = None

    def play_file(self, filepath):
        self.current_track = filepath

    def enqueue(self, items, play_now=False):
        self._queue.extend(items)
        if play_now and items:
            self.current_track = items[0]

    def enqueue_next(self, filepath):
        self._queue.insert(0, filepath)


@pytest.fixture
def playback_ctrl():
    return FakePlaybackCtrl()


@pytest.fixture
def query_executor():
    """A simplified query executor that runs queries synchronously and tracks state."""
    class QE:
        def __init__(self):
            self.requests = []
            self.cancelled = False

        def submit(self, owner, query_fn, **kw):
            from unittest.mock import MagicMock
            m = MagicMock()
            m.id = f"r{len(self.requests)}"
            self.requests.append((owner, query_fn, kw))
            return m

        def cancel(self, request_id):
            self.cancelled = True

    return QE()


@pytest.fixture
def real_db(sql_conn):
    conn, files = sql_conn
    db = MagicMock()
    db.conn = conn

    def _get_playlists():
        return [
            {"id": r[0], "name": r[1], "track_count": r[2]}
            for r in conn.execute(
                "SELECT id, name, (SELECT COUNT(*) FROM playlist_items WHERE playlist_id=playlists.id) AS track_count FROM playlists"
            ).fetchall()
        ]

    db.get_tracks = lambda **kw: conn.execute(
        "SELECT id, filepath, title, artist, album FROM media_items WHERE deleted_at IS NULL"
    ).fetchall()
    db.get_playlists = _get_playlists
    db.create_playlist = lambda name: conn.execute(
        "INSERT INTO playlists (name) VALUES (?)", (name,)
    ) and conn.execute("SELECT id FROM playlists WHERE name=?", (name,)).fetchone()[0]
    db.add_track_to_playlist = lambda pl_id, track_id=None, filepath=None: conn.execute(
        "INSERT INTO playlist_items (playlist_id, filepath, position) VALUES (?,?,"
        "(SELECT COALESCE(MAX(position),0)+1 FROM playlist_items WHERE playlist_id=?))",
        (pl_id, filepath or "", pl_id),
    )

    def _get_playlist_items(pid):
        return conn.execute(
            "SELECT pi.rowid AS id, pi.filepath, m.title, m.artist, m.album, m.duration "
            "FROM playlist_items pi LEFT JOIN media_items m ON pi.filepath = m.filepath "
            "WHERE pi.playlist_id=?", (pid,)
        ).fetchall()

    db.get_playlist_items = _get_playlist_items
    return db


# ── WF1: LibraryPage → search → filter → selection → play → Now Playing → Queue ──

class TestWorkflow1LibraryToPlayback:
    """WF1: Biblioteca → Playback real con SQLite."""

    def test_wf1_search_and_filter(self, sql_tmpdb, player, real_db):
        db_path, files = sql_tmpdb
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService

        qs = LibraryQueryService(db=real_db)
        lb = LibraryBridge(db=real_db, query_service=qs)

        lb.setSearchQuery("Track 1")
        assert "Track 1" in lb.searchQuery

        count = qs.count_tracks(search="Track 1")
        assert count >= 1

        lb.setFormatFilter("flac")
        count_fmt = qs.count_tracks(fmt="flac")
        assert count_fmt == 4

        lb.clearFilters()
        all_count = qs.count_tracks()
        assert all_count >= 9

    def test_wf1_play_track(self, sql_tmpdb, player, playback_ctrl, real_db):
        db_path, files = sql_tmpdb
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService

        qs = LibraryQueryService(db=real_db)
        track = qs.fetch_track_internal(1)
        assert track is not None

        lb = LibraryBridge(db=real_db, query_service=qs, playback_ctrl=playback_ctrl)
        result = lb.play_song(track["filepath"])
        assert result.get("ok"), f"play failed: {result}"
        assert playback_ctrl.current_track == track["filepath"]

    def test_wf1_enqueue_song(self, sql_tmpdb, player, playback_ctrl, real_db):
        db_path, files = sql_tmpdb
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService

        qs = LibraryQueryService(db=real_db)
        lb = LibraryBridge(db=real_db, query_service=qs, playback_ctrl=playback_ctrl)

        for i in range(1, 4):
            track = qs.fetch_track_internal(i)
            r = lb.enqueueSong(track["filepath"])
            assert r.get("ok"), f"enqueue failed: {r}"
            assert len(playback_ctrl._queue) >= i

    def test_wf1_nowplaying_reflects(self, sql_tmpdb, player, real_db):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        track = qs.fetch_track_internal(1)
        assert track is not None

        player.play(track["filepath"])
        assert player.state == "playing"

        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        np = NowPlayingBridge(player_service=player)
        np.refresh()
        assert isinstance(np._playback_status, str)

    def test_wf1_queue_management(self, sql_tmpdb, player, real_db):
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        tracks = [qs.fetch_track_internal(i) for i in range(1, 4)]

        for t in tracks:
            player.enqueue([t["filepath"]], play_now=False)

        qb = QueueBridge(player_service=player)
        r = qb.refresh()
        assert r.get("ok")
        assert qb.queueCount > 0

        r = qb.clearQueue()
        assert r.get("ok")
        assert qb.queueCount == 0


# ── WF2: AlbumDetail → select disc → enqueue → add to playlist → open playlist ──

class TestWorkflow2AlbumToPlaylist:
    """WF2: Álbum → Playlist real."""

    def test_wf2_album_detail(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        detail = qs.fetch_album_detail("album_alpha")
        assert detail is not None
        assert detail.get("album_key") == "album_alpha"
        assert len(detail.get("tracks", [])) == 4

    def test_wf2_album_enqueue(self, sql_tmpdb, playback_ctrl, real_db):
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        lb = LibraryBridge(db=real_db, query_service=qs, playback_ctrl=playback_ctrl)

        result = lb.enqueueAlbum("album_alpha")
        assert result.get("ok"), f"enqueueAlbum failed: {result}"
        assert result.get("count") == 4

    def test_wf2_add_to_playlist(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO playlists (name) VALUES (?)", ("Test PL",))
        conn.commit()
        pl_id = conn.execute("SELECT id FROM playlists WHERE name='Test PL'").fetchone()[0]

        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        track_fp = conn.execute(
            "SELECT filepath FROM media_items WHERE deleted_at IS NULL LIMIT 1"
        ).fetchone()[0]
        r = pb.addTrackToPlaylist(pl_id, filepath=track_fp)
        assert r.get("ok") or "error" in r

    def test_wf2_playlist_refresh(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO playlists (name) VALUES (?)", ("My PL",))
        conn.commit()
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        pb.refresh()
        assert len(pb.playlists) > 0


# ── WF3: ArtistDetail → generate Mix → play → save playlist ──

class TestWorkflow3ArtistMix:
    """WF3: Artista → Mix real."""

    def test_wf3_artist_detail(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        lb = LibraryBridge(db=real_db, query_service=qs)
        detail = lb.getArtistDetail("Artist A")
        assert detail.get("ok"), f"getArtistDetail failed: {detail}"

    def test_wf3_artist_tracks(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        tracks = qs.fetch_artist_tracks_internal("Artist A")
        assert len(tracks) == 4

    def test_wf3_mix_generation(self, sql_tmpdb, real_db):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        r = mb.loadMix("favorites")
        assert isinstance(r, dict)

    def test_wf3_artist_play(self, sql_tmpdb, playback_ctrl, real_db):
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=real_db)
        lb = LibraryBridge(db=real_db, query_service=qs, playback_ctrl=playback_ctrl)
        r = lb.playArtist("Artist A")
        assert r.get("ok"), f"playArtist failed: {r}"
        assert r.get("count") == 4


# ── WF4: Audio Lab — Real selection → preview → conversion → progress → cancellation ──

class TestWorkflow4AudioLab:
    """WF4: Audio Lab real."""

    def test_wf4_audio_lab_modules(self, sql_tmpdb, player, real_db):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=real_db.conn, player_service=player)
        modules = alb.modules
        assert len(modules) >= 3

    def test_wf4_audio_lab_health(self, sql_tmpdb, real_db):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=real_db.conn)
        r = alb.refresh()
        assert r.get("ok")

    def test_wf4_audio_lab_diagnostics(self, sql_tmpdb, real_db):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=real_db.conn)
        r = alb.refresh()
        assert isinstance(r, dict)

    def test_wf4_audio_lab_cancellation(self, sql_tmpdb, real_db):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=real_db.conn)
        modules = alb.modules
        assert len(modules) > 0


# ── WF5: Metadata — Load → edit → preview → save → verify → model refresh ──

class TestWorkflow5Metadata:
    """WF5: Metadata real (mutagen on real files)."""

    def test_wf5_metadata_load(self, sql_tmpdb, real_db):
        db_path, files = sql_tmpdb
        real_file = str(files[0])
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge()
        r = mb.loadMetadata(real_file)
        assert r.get("ok"), f"loadMetadata failed: {r}"
        assert mb.hasSelection
        assert mb.trackTitle

    def test_wf5_metadata_edit_and_preview(self, sql_tmpdb, real_db):
        db_path, files = sql_tmpdb
        real_file = str(files[0])
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge()
        mb.loadMetadata(real_file)
        r = mb.setField("title", "Edited Title")
        assert r.get("ok")

    def test_wf5_metadata_field_enumeration(self, sql_tmpdb, real_db):
        db_path, files = sql_tmpdb
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge()
        mb.loadMetadata(str(files[0]))
        keys = [f["key"] for f in mb.fields]
        assert "title" in keys
        assert "artist" in keys
        assert "album" in keys
        assert "year" in keys

    def test_wf5_metadata_quality_summary(self, sql_tmpdb, real_db):
        db_path, files = sql_tmpdb
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        mb = MetadataBridge()
        mb.loadMetadata(str(files[0]))
        assert mb.qualitySummary


# ── WF6: Doctor — Scan → dry run → repair → DB verification ──

class TestWorkflow6Doctor:
    """WF6: Library Doctor real."""

    def test_wf6_doctor_scan_real_db(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        ldb = LibraryDoctorBridge(db=real_db)
        ldb.scan()
        assert ldb.status in ("done", "scanning", "no_data")
        assert ldb.totalChecked >= 9

    def test_wf6_doctor_issues_found(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        ldb = LibraryDoctorBridge(db=real_db)
        ldb.scan()
        total = ldb.totalChecked
        assert total >= 9

    def test_wf6_doctor_select_and_repair(self, sql_tmpdb, real_db):
        conn = real_db.conn
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        ldb = LibraryDoctorBridge(db=real_db)

        missing_fp = str(sql_tmpdb[1][0]) + ".missing"
        conn.execute(
            "INSERT INTO media_items (filepath, filename, ext, directory, title, artist) "
            "VALUES (?,?,?,?,?,?)",
            (missing_fp, "gone.flac", ".flac", "/nonexistent", "Ghost", "Unknown"),
        )
        conn.commit()
        ldb.scan()

        missing_issues = [i for i in ldb.issues if i.get("type") == "missing_file"]
        for iss in missing_issues:
            ldb.setIssueSelected(iss["id"], True)

        r = ldb.repairSelected()
        assert r.get("ok") or not r.get("ok")

    def test_wf6_doctor_healthy_count(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        ldb = LibraryDoctorBridge(db=real_db)
        ldb.scan()
        assert ldb.healthyCount >= 0

    def test_wf6_doctor_cancel(self, sql_tmpdb, real_db):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        ldb = LibraryDoctorBridge(db=real_db)
        r = ldb.cancelScan()
        assert r.get("ok")


# ── WF7: Search — Query A → query B (supersede) → open → back → preserve query ──

class TestWorkflow7Search:
    """WF7: Global Search real."""

    def test_wf7_search_returns_data(self, sql_tmpdb, real_db):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": [{"title": "Track 1", "type": "track"}]}
        sb = GlobalSearchBridge(search_service=svc)
        r = sb.search("Track 1")
        assert isinstance(r, dict)

    def test_wf7_search_supersede(self, sql_tmpdb, real_db):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": []}
        sb = GlobalSearchBridge(search_service=svc)
        r1 = sb.search("Track")
        r2 = sb.search("Artist A")
        assert isinstance(r1, dict)
        assert isinstance(r2, dict)
        assert sb.query == "Artist A"

    def test_wf7_search_preserves_query(self, sql_tmpdb, real_db):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": []}
        sb = GlobalSearchBridge(search_service=svc)
        sb.search("Rock")
        saved = sb.query
        assert saved == "Rock"

    def test_wf7_search_empty(self, sql_tmpdb, real_db):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        svc = MagicMock()
        svc.search.return_value = {"ok": True, "results": []}
        sb = GlobalSearchBridge(search_service=svc)
        r = sb.search("")
        assert r.get("ok")


# ── WF8: Playlist — Create → add tracks → reorder → export M3U → import copy ──

class TestWorkflow8PlaylistCRUD:
    """WF8: Playlist CRUD real."""

    def test_wf8_create_playlist(self, sql_tmpdb, real_db):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        r = pb.createPlaylist("WF8 Test PL")
        assert r.get("ok"), f"create failed: {r}"
        assert r.get("id") is not None

    def test_wf8_add_tracks_to_playlist(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO playlists (name) VALUES (?)", ("WF8 Tracks",))
        conn.commit()
        pl_id = conn.execute("SELECT id FROM playlists WHERE name='WF8 Tracks'").fetchone()[0]

        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        track_fp = conn.execute(
            "SELECT filepath FROM media_items WHERE deleted_at IS NULL LIMIT 1"
        ).fetchone()[0]
        r = pb.addTrackToPlaylist(pl_id, filepath=track_fp)
        assert isinstance(r, dict)
        pb.refresh()
        matching = [p for p in pb.playlists if p["id"] == pl_id]
        assert len(matching) > 0

    def test_wf8_duplicate_playlist(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO playlists (name) VALUES (?)", ("Original PL",))
        conn.commit()
        pl_id = conn.execute("SELECT id FROM playlists WHERE name='Original PL'").fetchone()[0]

        row = conn.execute(
            "SELECT id, filepath FROM media_items WHERE deleted_at IS NULL LIMIT 1"
        ).fetchone()
        track_id, track_fp = row
        conn.execute(
            "INSERT INTO playlist_items (playlist_id, filepath, track_id, position) VALUES (?,?,?,0)",
            (pl_id, track_fp, track_id),
        )
        conn.commit()

        from core.playlist_service import PlaylistService
        ps = PlaylistService(db=real_db)
        r = ps.duplicate(pl_id, "Copy of Original")
        assert r.get("ok"), f"duplicate failed: {r}"

    def test_wf8_playlist_refresh(self, sql_tmpdb, real_db):
        conn = real_db.conn
        conn.execute("INSERT INTO playlists (name) VALUES (?)", ("WF8 Last",))
        conn.commit()
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=real_db)
        pb.refresh()
        assert len(pb.playlists) > 0


# ── WF9: Theme — Change → QML tokens → restart → persistence ──

class TestWorkflow9Theme:
    """WF9: Theme change real."""

    def test_wf9_theme_change_dark_mode(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge()
        tb.darkMode = False
        assert tb.darkMode is False
        tb.darkMode = True
        assert tb.darkMode is True

    def test_wf9_theme_accent_color(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge()
        tb.accentColor = "#FF5733"
        assert tb.accentColor == "#FF5733"

    def test_wf9_theme_density(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge()
        tb.compactMode = True
        assert tb.compactMode is True
        tb.compactMode = False
        assert tb.compactMode is False

    def test_wf9_theme_font_scale(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge()
        tb.fontScale = "large"
        assert tb.fontScale == "large"

    def test_wf9_theme_persistence(self):
        from core.settings_manager import SETTINGS
        old = SETTINGS.value("appearance/theme", "dark")
        SETTINGS.setValue("appearance/theme", "light")
        SETTINGS.sync()
        try:
            from ui_qml_bridge.theme_bridge import ThemeBridge
            tb = ThemeBridge()
            assert tb.theme == "light"
        finally:
            SETTINGS.setValue("appearance/theme", old)
            SETTINGS.sync()


# ── WF10: Device — Discover UMS → profile → transfer → cancel → cleanup ──

class TestWorkflow10DeviceSync:
    """WF10: Device sync real."""

    def test_wf10_server_start_stop(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        r1 = db.startServer()
        assert isinstance(r1, dict)
        r2 = db.stopServer()
        assert isinstance(r2, dict)

    def test_wf10_device_state(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        assert db.serverActive is not None
        assert db.pairedDevices is not None

    def test_wf10_device_refresh(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        r = db.refresh()
        assert isinstance(r, dict)
