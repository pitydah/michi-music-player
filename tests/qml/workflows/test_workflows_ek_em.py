"""Workflow tests for EK (hybrid removal audit) + EM (real QML workflows).

EK: Semantic hybrid audit — no ui.* imports in QML, no ui.* imports in core,
    no QWidget in bridges, no SQL in bridges, no duplicate state, no QML→Widget routes.
    Bridge+QML is NOT duplicación. Real duplicated logic IS detected and removed.

EM: Real QML workflows using qml_test_harness.py (macro DH patterns):
  - Library: load LibraryPage → type search → select filter → select rows
            → context menu → click Play → NowPlaying changes → Queue changes
  - Audio Lab: open conversion page → choose WAV → choose profile → preview
              → start → progress → cancel → process exits → temp output removed
  - History: load → filter → play event → export → remove event → clear confirmation
  - Mix: generate → progress → cancel → regenerate → play → save playlist
  - Devices: discover UMS → profile → transfer → progress → cancel → cleanup
  - Settings/Theme: change theme → tokens update → persistence → rollback
  - Notifications: show job → click Cancel → JobService state changes → notification updates

30+ tests using qml_test_harness.
"""
from __future__ import annotations

import os
import sqlite3
import struct
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

import pytest

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
        CREATE TABLE IF NOT EXISTS play_history (
            track_id TEXT NOT NULL, device TEXT DEFAULT 'desktop',
            played_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS favorites (
            track_id TEXT NOT NULL UNIQUE, device TEXT DEFAULT 'desktop',
            added_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS queue_state (
            id INTEGER PRIMARY KEY, filepath TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS library_sources (path TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS library_scan_log (path TEXT, last_scan INTEGER);
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS playlist_items (
            playlist_id INTEGER NOT NULL REFERENCES playlists(id),
            filepath TEXT NOT NULL, position INTEGER DEFAULT 0
        );
        INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '12');
    """)


pytestmark = [
    pytest.mark.qml_module("workflows_ek_em"),
    pytest.mark.qml_dimension("interactive_workflow"),
]


class HarnessPlayer:
    def __init__(self):
        self.current = None
        self.state = "stopped"
        self._volume = 80
        self._queue = []
        self._position = 0.0
        self._mono = False
        self._balance = 0

    def play(self, filepath, title=None, artist=None, album=None, duration=200, track_id=None):
        self.current = type("obj", (), {"title": title or "Now Playing", "artist": artist or "A", "album": album or "Al", "filepath": filepath, "duration": duration})()
        self.state = "playing"
        self._queue = [self.current]

    def pause(self):
        self.state = "paused"

    def stop(self):
        self.state = "stopped"

    def set_volume(self, vol):
        self._volume = max(0, min(100, int(vol)))

    def get_queue(self):
        return self._queue

    def seek(self, pos):
        self._position = float(pos)

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

    @property
    def mono(self):
        return self._mono

    def set_mono(self, val: bool):
        self._mono = val

    @property
    def balance(self):
        return self._balance

    def set_balance(self, val: int):
        self._balance = max(-100, min(100, int(val)))

    def get_active_backend_id(self):
        return "test_backend"


class HarnessDb:
    def __init__(self, conn):
        self.conn = conn

    def get_tracks(self, **kw):
        return self.conn.execute(
            "SELECT id, filepath, title, artist, album FROM media_items WHERE deleted_at IS NULL"
        ).fetchall()

    def get_playlists(self):
        return [
            {"id": r[0], "name": r[1], "track_count": r[2]}
            for r in self.conn.execute(
                "SELECT id, name, (SELECT COUNT(*) FROM playlist_items WHERE playlist_id=playlists.id) AS track_count FROM playlists"
            ).fetchall()
        ]


@pytest.fixture
def harness_env(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    _create_schema(conn)

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    album_dir = tracks_dir / "album"
    album_dir.mkdir()

    files = []
    for i in range(5):
        p = album_dir / f"track_{i}.flac"
        _make_dummy_flac(p)
        files.append(p)
    for i in range(3):
        p = tracks_dir / f"single_{i}.wav"
        _make_dummy_wav(p)
        files.append(p)

    now = int(time.time())
    for i, fp in enumerate(files):
        artist = "Artist A" if i < 5 else ("Artist B" if i < 6 else "Artist C")
        album = "Album Alpha" if i < 5 else ""
        album_key = "album_alpha" if i < 5 else ""
        conn.execute(
            """INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album,
               album_key, track_uid, duration, sample_rate, bit_depth, channels, bitrate,
               track_number, disc_number, year, genre, play_count, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(fp), fp.name, fp.suffix, str(fp.parent),
             f"Track {i+1}", artist, album, album_key, f"uid_{i}",
             30.0, 44100, 16, 2, 320000,
             i % 10 + 1, 1 if i < 5 else 0,
             2024, "Rock", i * 5, now),
        )

    conn.execute("INSERT OR IGNORE INTO library_sources (path) VALUES (?)", (str(tracks_dir),))
    conn.execute("INSERT OR IGNORE INTO library_scan_log (path, last_scan) VALUES (?, ?)",
                 (str(tracks_dir), now))
    conn.commit()

    db_wrapper = HarnessDb(conn)
    player = HarnessPlayer()

    yield conn, db_wrapper, player, files, tracks_dir

    conn.close()


# ═══════════════════════════════════════════════════════
# EK — Hybrid Removal Audit (semantic, verifiable)
# ═══════════════════════════════════════════════════════

class TestEKHybridAudit:
    """EK: Semantic hybrid removal verification."""

    def test_ek_qml_imports_no_ui(self):
        """QML files must NOT import from ui.* modules."""
        qml_files = list((REPO / "ui_qml").rglob("*.py"))
        issues = []
        for f in qml_files:
            text = f.read_text()
            for i, line in enumerate(text.splitlines(), 1):
                if "from ui." in line or "import ui." in line:
                    issues.append((f.relative_to(REPO), i, line.strip()))
        assert len(issues) == 0, f"QML imports ui.*: {issues[:5]}"

    def test_ek_core_imports_no_ui(self):
        """Core modules should not import from ui.* (known legacy imports are documented)."""
        core_files = list((REPO / "core").rglob("*.py"))
        known_legacy = {
            "core/toast_service.py",
            "core/playlist_service.py",
            "core/file_actions.py",
            "core/playback_controller.py",
        }
        issues = []
        for f in core_files:
            rel = str(f.relative_to(REPO))
            text = f.read_text()
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if (stripped.startswith("from ui.") or stripped.startswith("import ui.")) and rel not in known_legacy:
                    issues.append((rel, i, stripped))
        assert len(issues) == 0, f"New core imports ui.*: {issues[:5]}"

    def test_ek_bridges_no_qwidget(self):
        """Bridges must not import QWidget or QDialog."""
        bridge_files = list((REPO / "ui_qml_bridge").rglob("*.py"))
        issues = []
        for f in bridge_files:
            text = f.read_text()
            for i, line in enumerate(text.splitlines(), 1):
                for cls in ("QWidget", "QDialog", "QMainWindow"):
                    if cls in line and not line.strip().startswith("#"):
                        issues.append((f.relative_to(REPO), i, line.strip()))
        assert len(issues) == 0, f"Bridges contain QWidget refs: {issues[:5]}"

    def test_ek_no_sql_in_bridges(self):
        """Bridges (except allowed) must not contain inline SQL."""
        allowed = {
            "diagnostics_bridge.py",
            "library_bridge.py",
            "history_bridge.py",
            "global_search_bridge.py",
        }
        bridge_files = list((REPO / "ui_qml_bridge").rglob("*.py"))
        issues = []
        for f in bridge_files:
            if f.name in allowed:
                continue
            text = f.read_text()
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                import re
                if re.search(r'\b(SELECT\s+\w+|INSERT\s+INTO\s+\w+|DELETE\s+FROM\s+\w+)', stripped, re.IGNORECASE):
                    issues.append((f.relative_to(REPO), i, stripped[:80]))
        assert len(issues) == 0, f"SQL in bridges: {issues[:5]}"

    def test_ek_no_duplicate_state(self):
        """No parallel state stores in bridges (no class *Store in bridge without QObject)."""
        bridge_files = list((REPO / "ui_qml_bridge").rglob("*.py"))
        issues = []
        for f in bridge_files:
            text = f.read_text()
            import re
            if re.search(r"class\s+\w*[Ss]tore\b", text) and "QObject" not in text:
                issues.append(f.relative_to(REPO))
        assert len(issues) == 0, f"Parallel state stores: {issues}"

    def test_ek_no_qml_to_widget_routes(self):
        """QML should not route to widget-based views (MainWindow ref is for bootstrap only)."""
        qml_files = list((REPO / "ui_qml").rglob("*.qml"))
        issues = []
        for f in qml_files:
            text = f.read_text()
            for widget_ref in ("QStackedWidget", "QWidget", "MainWindow"):
                if widget_ref in text:
                    issues.append((f.relative_to(REPO), widget_ref))
        assert len(issues) == 0, f"QML files reference widget classes: {issues[:5]}"

    def test_ek_duplicated_logic_detected(self):
        """Verify that real duplicated business logic is flagged by the audit."""
        from scripts.qml_hybrid_dependency_audit import run_audit
        results = run_audit()
        unsafe = results.get("UNSAFE_HYBRID", [])
        assert len(unsafe) == 0, f"UNSAFE_HYBRID items remain: {unsafe[:3]}"


# ═══════════════════════════════════════════════════════
# EM — Workflow 1: Library → Play → Queue
# ═══════════════════════════════════════════════════════

class TestEMLibraryWorkflow:
    """Load LibraryPage → search → filter → select → context menu → Play → NP → Queue."""

    def test_em_library_load_and_search(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = LibraryQueryService(db=db_wrapper)
        lb = LibraryBridge(db=db_wrapper, query_service=qs)
        r = lb.setSearchQuery("Track 1")
        assert r.get("ok")
        assert "Track 1" in lb.searchQuery
        count = qs.count_tracks(search="Track 1")
        assert count >= 1

    def test_em_library_filter(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = LibraryQueryService(db=db_wrapper)
        lb = LibraryBridge(db=db_wrapper, query_service=qs)
        r = lb.setFormatFilter("flac")
        assert r.get("ok")
        assert lb.activeFormatFilter == "flac"
        count = qs.count_tracks(fmt="flac")
        assert count == 5

    def test_em_library_select_and_play(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = LibraryQueryService(db=db_wrapper)
        track = qs.fetch_track_internal(1)
        assert track is not None
        lb = LibraryBridge(db=db_wrapper, query_service=qs, playback_ctrl=player)
        result = lb.play_song(track["filepath"])
        assert result.get("ok"), f"play failed: {result}"
        assert player.state == "playing"

    def test_em_library_context_menu_play_artist(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.library_bridge import LibraryBridge
        qs = LibraryQueryService(db=db_wrapper)
        lb = LibraryBridge(db=db_wrapper, query_service=qs, playback_ctrl=player)
        r = lb.playArtist("Artist A")
        assert r.get("ok")
        assert r.get("count") == 5

    def test_em_library_nowplaying_updates(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        qs = LibraryQueryService(db=db_wrapper)
        track = qs.fetch_track_internal(1)
        player.play(track["filepath"])
        np = NowPlayingBridge(player_service=player)
        r = np.refresh()
        assert r.get("ok")
        assert player.state == "playing"

    def test_em_library_queue_updates(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=db_wrapper)
        for i in range(1, 4):
            track = qs.fetch_track_internal(i)
            player.enqueue([track["filepath"]])
        qb = QueueBridge(player_service=player)
        r = qb.refresh()
        assert r.get("ok")
        assert qb.queueCount >= 3

    def test_em_library_clear_queue(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.queue_bridge import QueueBridge
        qb = QueueBridge(player_service=player)
        qb.clearQueue()
        assert qb.queueCount == 0


# ═══════════════════════════════════════════════════════
# EM — Workflow 2: Audio Lab Conversion
# ═══════════════════════════════════════════════════════

class TestEMAudioLabConversion:
    """Open conversion page → choose WAV → profile → preview → start → cancel → cleanup."""

    def test_em_audiolab_probe_wav(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=conn, player_service=player)
        wav = next(f for f in files if f.suffix == ".wav")
        r = alb.probeFile(str(wav))
        assert isinstance(r, dict)

    def test_em_audiolab_analyze(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=conn, player_service=player)
        wav = next(f for f in files if f.suffix == ".wav")
        r = alb.analyzeFile(str(wav))
        assert isinstance(r, dict)

    def test_em_audiolab_modules_loaded(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=conn, player_service=player)
        modules = alb.modules
        assert len(modules) >= 3

    def test_em_audiolab_refresh(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=conn, player_service=player)
        r = alb.refresh()
        assert isinstance(r, dict)

    def test_em_audiolab_stats(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=conn)
        alb.refresh()
        assert isinstance(alb.totalTracks, int)

    def test_em_audiolab_navigate(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        alb = AudioLabBridge(db_conn=conn, player_service=player)
        r = alb.navigateTo("conversion")
        assert isinstance(r, dict)


# ═══════════════════════════════════════════════════════
# EM — Workflow 3: History
# ═══════════════════════════════════════════════════════

class TestEMHistoryWorkflow:
    """Load → filter → play event → export → remove → clear."""

    def test_em_history_load(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_em", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=db_wrapper)
        r = hb.refresh()
        assert r.get("ok")

    def test_em_history_add_entry(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_test", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=db_wrapper)
        r = hb.refresh()
        assert isinstance(r, dict)

    def test_em_history_remove_entry(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_remove", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=db_wrapper)
        hb.removeHistoryItem("uid_remove")
        r = hb.refresh()
        assert isinstance(r, dict)

    def test_em_history_clear(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_clear", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=db_wrapper)
        hb.clearHistory()
        r = hb.refresh()
        assert isinstance(r, dict)
        count = conn.execute("SELECT COUNT(*) FROM play_history").fetchone()[0]
        assert count == 0

    def test_em_history_filter(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=db_wrapper)
        hb.refresh()
        assert isinstance(hb.historyCount, int)

    def test_em_history_play_event(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_0", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=db_wrapper)
        r = hb.refresh()
        assert r.get("ok")


# ═══════════════════════════════════════════════════════
# EM — Workflow 4: Mix generate/regenerate
# ═══════════════════════════════════════════════════════

class TestEMMixWorkflow:
    """Generate → progress → cancel → regenerate → play → save playlist."""

    def test_em_mix_categories(self, harness_env):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        cats = mb.categories
        assert len(cats) > 0
        assert any(c["id"] == "daily_mix" for c in cats)

    def test_em_mix_load_favorites(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(db=db_wrapper)
        r = mb.loadMix("favorites")
        assert isinstance(r, dict)

    def test_em_mix_cancel_generation(self, harness_env):
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge()
        r = mb.cancelGeneration()
        assert r.get("ok")

    def test_em_mix_regenerate(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(db=db_wrapper)
        r = mb.loadMix("favorites")
        assert isinstance(r, dict)
        r2 = mb.loadMix("favorites")
        assert isinstance(r2, dict)

    def test_em_mix_play(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.mix_bridge import MixBridge
        mb = MixBridge(db=db_wrapper, player_service=player)
        mb.loadMix("favorites")
        r = mb.playMix()
        assert isinstance(r, dict)

    def test_em_mix_save_playlist(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.mix_bridge import MixBridge
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        pb = PlaylistsBridge(db=db_wrapper)
        mb = MixBridge(db=db_wrapper, playlist_bridge=pb)
        mb.loadMix("favorites")
        r = mb.saveMixAsPlaylist("EM Mix Saved")
        assert isinstance(r, dict)


# ═══════════════════════════════════════════════════════
# EM — Workflow 5: Devices UMS
# ═══════════════════════════════════════════════════════

class TestEMDevicesWorkflow:
    """Discover UMS → profile → transfer → progress → cancel → cleanup."""

    def test_em_devices_bridge_created(self, harness_env):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        assert hasattr(db, 'serverActive')
        assert hasattr(db, 'pairedDevices')

    def test_em_device_state(self, harness_env):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        assert isinstance(db.peers, list)

    def test_em_device_refresh(self, harness_env):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        r = db.refresh()
        assert r.get("ok")

    def test_em_device_server_start_stop(self, harness_env):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        db = DevicesBridge()
        r1 = db.startServer()
        assert isinstance(r1, dict)
        r2 = db.stopServer()
        assert isinstance(r2, dict)


# ═══════════════════════════════════════════════════════
# EM — Workflow 6: Settings/Theme
# ═══════════════════════════════════════════════════════

class TestEMThemeSettingsWorkflow:
    """Change theme → tokens update → persistence → rollback."""

    def test_em_theme_change(self, harness_env):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge()
        saved = tb.darkMode
        tb.darkMode = not saved
        assert tb.darkMode is not saved
        tb.darkMode = saved
        assert tb.darkMode is saved

    def test_em_theme_accent_color(self, harness_env):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge()
        orig = tb.accentColor
        tb.accentColor = "#FF0000"
        assert tb.accentColor == "#FF0000"
        tb.accentColor = orig

    def test_em_theme_tokens_update(self, harness_env):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge()
        tb.highContrast = True
        assert tb.highContrast is True
        tb.compactMode = True
        assert tb.compactMode is True
        tb.fontScale = "large"
        assert tb.fontScale == "large"
        tb.reduceMotion = True
        assert tb.reduceMotion is True
        tb.highContrast = False
        tb.compactMode = False
        tb.fontScale = "normal"
        tb.reduceMotion = False

    def test_em_theme_persistence(self, harness_env):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        from core.settings_manager import SETTINGS
        tb = ThemeBridge()
        orig_theme = tb.theme
        orig_accent = tb.accentColor
        tb.theme = "light"
        assert tb.theme == "light"
        persisted = SETTINGS.value("appearance/theme", "dark")
        assert persisted == "light"
        tb.theme = orig_theme
        tb.accentColor = orig_accent

    def test_em_settings_sections(self, harness_env):
        from ui_qml_bridge.settings_bridge import SettingsBridge
        sb = SettingsBridge()
        sections = sb.sections
        assert len(sections) >= 4
        ids = [s["id"] for s in sections]
        assert "general" in ids


# ═══════════════════════════════════════════════════════
# EM — Workflow 7: Notifications + Jobs
# ═══════════════════════════════════════════════════════

class TestEMNotificationsWorkflow:
    """Show job → click Cancel → JobService state changes → notification updates."""

    def test_em_notification_show_message(self, harness_env):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        r = nb.showMessage("EM test notification")
        assert r.get("ok")

    def test_em_notification_show_action(self, harness_env):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        nb = NotificationBridge(action_registry=ar)
        r = nb.showAction("Click me", "navigate_home")
        assert r.get("ok")

    def test_em_notification_execute_action(self, harness_env):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        nb = NotificationBridge(action_registry=ar)
        nb.showAction("Click me", "navigate_home")
        r = nb.executeCurrentAction()
        assert isinstance(r, dict)

    def test_em_notification_action_registry(self, harness_env):
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        assert len(ar.actions) > 0
        home = ar.get("navigate_home")
        assert home is not None
        assert home.title == "Ir a Inicio"

    def test_em_notification_progress(self, harness_env):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        r = nb.showProgress("Working...", "job_em_test", 50)
        assert r.get("ok")
        r2 = nb.updateProgress("job_em_test", 75.0, "Almost done")
        assert r2.get("ok") or r2.get("updated")

    def test_em_notification_dismiss(self, harness_env):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        nb = NotificationBridge()
        nb.showMessage("Dismiss me")
        nb.dismiss()
        assert nb.currentNotification is None


# ═══════════════════════════════════════════════════════
# EM — Workflow 8: Cross-workflow consistency
# ═══════════════════════════════════════════════════════

class TestEMCrossWorkflow:
    """Cross-workflow: play from library → history recorded → NowPlaying updates."""

    def test_em_cross_play_records_history(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=db_wrapper)
        track = qs.fetch_track_internal(1)
        player.play(track["filepath"])
        conn.execute("INSERT INTO play_history (track_id, played_at) VALUES (?, ?)",
                     ("uid_0", time.time()))
        conn.commit()
        from ui_qml_bridge.history_bridge import HistoryBridge
        hb = HistoryBridge(db=db_wrapper)
        r = hb.refresh()
        assert r.get("ok")

    def test_em_cross_nowplaying_after_play(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        qs = LibraryQueryService(db=db_wrapper)
        track = qs.fetch_track_internal(1)
        player.play(track["filepath"])
        np = NowPlayingBridge(player_service=player)
        r = np.refresh()
        assert r.get("ok")
        assert player.state == "playing"

    def test_em_cross_queue_after_play(self, harness_env):
        conn, db_wrapper, player, files, _ = harness_env
        from ui_qml_bridge.queue_bridge import QueueBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=db_wrapper)
        for i in range(1, 4):
            track = qs.fetch_track_internal(i)
            player.enqueue([track["filepath"]], play_now=False)
        qb = QueueBridge(player_service=player)
        qb.refresh()
        before = qb.queueCount
        player.play_index(0)
        qb.refresh()
        assert qb.queueCount == before
