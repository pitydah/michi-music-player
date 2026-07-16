from __future__ import annotations

import os
import sqlite3
import struct
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MICHI_SAFE_MODE"] = "1"

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QUrl, QTimer, Signal, QObject
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlContext
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt




def _make_dummy_flac(path: Path) -> str:
    with path.open("wb") as f:
        f.write(b"fLaC")
        info = bytearray(34)
        struct.pack_into(">H", info, 0, 0x8000)
        struct.pack_into(">H", info, 10, 44100)
        struct.pack_into(">B", info, 12, 16)
        f.write(bytes([0x80 | 0, 34]) + bytes(info))
        f.write(bytes(128))
    return str(path)


def _make_dummy_wav(path: Path) -> str:
    sr, bits, ch, ds = 44100, 16, 1, 44
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


SCHEMA_SQL = """
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
"""


def create_test_db(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    tracks_dir = Path(db_path).parent / "tracks"
    tracks_dir.mkdir(exist_ok=True)
    album_a_dir = tracks_dir / "album_a"
    album_a_dir.mkdir(exist_ok=True)
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
        artist = "Artist A" if i < 4 else "Artist B"
        album = "Album Alpha" if i < 4 else ""
        album_key = "album_alpha" if i < 4 else ""
        conn.execute(
            """INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album,
               album_key, track_uid, duration, sample_rate, bit_depth, channels, bitrate,
               track_number, disc_number, year, genre, play_count, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(fp), fp.name, fp.suffix, str(fp.parent),
             f"Track {i + 1}", artist, album, album_key, f"uid_{i}",
             30.0, 44100, 16, 2, 320000,
             i % 10 + 1, 1 if i < 4 else 0,
             2024, "Rock", i * 5, now),
        )
    conn.execute("INSERT OR IGNORE INTO library_sources (path) VALUES (?)", (str(tracks_dir),))
    conn.execute("INSERT OR IGNORE INTO library_scan_log (path, last_scan) VALUES (?, ?)",
                 (str(tracks_dir), now))
    conn.commit()
    return conn


class FakePlayerService:
    def __init__(self):
        self.current = None
        self.state = "stopped"
        self._volume = 80
        self._queue = []

    def play(self, filepath, title=None, artist=None, album=None, duration=200, track_id=None):
        self.current = type("obj", (), {"title": title or "Now Playing", "artist": artist or "A", "album": album or "Al", "filepath": filepath, "duration": duration})()
        self.state = "playing"
        self._queue = [self.current]

    def pause(self):
        self.state = "paused"

    def play_or_resume(self):
        self.state = "playing"

    def stop(self):
        self.state = "stopped"

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

    def play_next(self):
        if self._queue:
            self.current = self._queue[0]

    def shutdown(self):
        pass


class QmlTestHarness:
    def __init__(self, qml_path: str | Path | None = None):
        self._app = QGuiApplication.instance()
        if not self._app:
            self._app = QGuiApplication(sys.argv)
        self._engine = QQmlApplicationEngine()
        self._engine.addImportPath(str(Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"))
        self._bridges: dict[str, QObject] = {}
        self._qml_path = qml_path
        self._component: QQmlComponent | None = None
        self._root_obj: QObject | None = None
        self._created = False
        self._tmpdir: tempfile.TemporaryDirectory | None = None
        self._db_conn: sqlite3.Connection | None = None
        self._db_wrapper: Any = None

    def setup_db(self) -> Path:
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "test.db"
        self._db_conn = create_test_db(db_path)

        class RealDbWrapper:
            def __init__(self, conn, path):
                self.conn = conn
                self.db_path = str(path)

            def close(self):
                self.conn.close()

            def get_tracks(self, **kw):
                return self.conn.execute(
                    "SELECT id, filepath, title, artist, album FROM media_items WHERE deleted_at IS NULL"
                ).fetchall()

        self._db_wrapper = RealDbWrapper(self._db_conn, db_path)
        return db_path

    def register_bridge(self, name: str, bridge: QObject):
        self._bridges[name] = bridge

    def _register_null_bridges(self, ctx: QQmlContext):
        required = [
            "appBridge", "navigationBridge", "themeBridge", "libraryBridge",
            "playbackBridge", "nowplayingBridge", "settingsBridge",
            "actionRegistry",
        ]
        missing = [n for n in required if n not in self._bridges]
        if missing:
            raise RuntimeError(f"QmlTestHarness: missing REQUIRED bridges: {missing}")

    def load_qml(self, qml_path: str | Path | None = None) -> QObject:
        path = qml_path or self._qml_path
        if not path:
            msg = "qml_path is required"
            raise ValueError(msg)
        path = Path(path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent.parent.parent.parent / path
        self._component = QQmlComponent(self._engine)

        from PySide6.QtCore import qInstallMessageHandler
        self._old_handler = qInstallMessageHandler(lambda msg_type, ctx, msg: None)
        qInstallMessageHandler(lambda msg_type, ctx, msg: None)

        self._component.loadUrl(QUrl.fromLocalFile(str(path)))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            s = self._component.status()
            if s != QQmlComponent.Loading:
                break
            QGuiApplication.processEvents()

        if self._component.status() != QQmlComponent.Ready:
            errs = [str(e) for e in self._component.errors()]
            raise RuntimeError(f"QML load failed: {errs}")

        ctx = self._engine.rootContext()
        if not ctx:
            ctx = QQmlContext(self._engine)
        self._register_null_bridges(ctx)

        for name, bridge in self._bridges.items():
            ctx.setContextProperty(name, bridge)

        self._root_obj = self._component.create()
        if self._root_obj is None:
            raise RuntimeError("QML create() returned None")

        self._created = True
        QGuiApplication.processEvents()
        return self._root_obj

    def find_control(self, object_name: str) -> QObject | None:
        if not self._root_obj:
            return None
        return self._root_obj.findChild(QObject, object_name)

    def find_controls(self, object_name: str) -> list[QObject]:
        if not self._root_obj:
            return []
        return self._root_obj.findChildren(QObject, object_name)

    def mouse_click(self, control: QObject):
        QTest.mouseClick(control, Qt.LeftButton)

    def key_clicks(self, control: QObject, text: str):
        QTest.keyClicks(control, text)

    def process_events(self, count: int = 1):
        for _ in range(count):
            QGuiApplication.processEvents()

    def wait_for_signal(self, signal: Signal, timeout_ms: int = 3000) -> bool:
        from PySide6.QtCore import QEventLoop
        loop = QEventLoop()
        result = [False]

        def on_signal(*args):
            result[0] = True
            loop.quit()

        signal.connect(on_signal)
        QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()
        signal.disconnect(on_signal)
        return result[0]

    def cleanup(self):
        self._created = False
        if self._root_obj:
            self._root_obj.deleteLater()
            self._root_obj = None
        if self._component:
            self._component = None
        if self._db_conn:
            import contextlib
            with contextlib.suppress(Exception):
                self._db_conn.close()
            self._db_conn = None
        if self._tmpdir:
            self._tmpdir.cleanup()
            self._tmpdir = None
        self._bridges.clear()
        self._engine = QQmlApplicationEngine()
        QGuiApplication.processEvents()

    @property
    def engine(self) -> QQmlApplicationEngine:
        return self._engine

    @property
    def root(self) -> QObject | None:
        return self._root_obj

    @property
    def db(self):
        return self._db_wrapper
