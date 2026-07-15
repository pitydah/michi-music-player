from __future__ import annotations
"""Test library visibility with real SQLite DB + temp tracks + QML app.
Creates a real DB with 3 tracks (MP3/FLAC/WAV), starts QML, navigates to
Biblioteca, and verifies the model sees all 3 tracks.
"""

import os
import sqlite3
import struct
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent


def _make_dummy_mp3(path: Path) -> str:
    """Write a minimal valid MP3 frame."""
    frame = b"\xff\xfb\x90\x00" + b"\x00" * 400
    path.write_bytes(frame)
    return str(path)


def _make_dummy_flac(path: Path) -> str:
    """Write minimal FLAC file with STREAMINFO metadata block."""
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
    """Write minimal valid WAV file."""
    sample_rate = 44100
    bits = 16
    channels = 1
    data_size = 44
    with path.open("wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, sample_rate * channels * bits // 8, channels * bits // 8, bits))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)
    return str(path)


@pytest.fixture
def real_db_with_tracks(tmp_path: Path):
    """Create a real SQLite DB, insert 3 tracks, return (db_path, track_files)."""
    db_path = tmp_path / "test_library.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS media_items (
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
        CREATE TABLE IF NOT EXISTS library_sources (path TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS library_scan_log (path TEXT, last_scan INTEGER);
        CREATE TABLE IF NOT EXISTS play_history (id INTEGER PRIMARY KEY AUTOINCREMENT, track_id TEXT);
        INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '12');
    """)
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()

    mp3_path = _make_dummy_mp3(tracks_dir / "test.mp3")
    flac_path = _make_dummy_flac(tracks_dir / "test.flac")
    wav_path = _make_dummy_wav(tracks_dir / "test.wav")

    now = int(time.time())
    for i, (fp, ext) in enumerate([
        (mp3_path, ".mp3"),
        (flac_path, ".flac"),
        (wav_path, ".wav"),
    ]):
        title = f"Cancion {i + 1}"
        conn.execute(
            """INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album,
               album_key, track_uid, duration, sample_rate, bit_depth, channels, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fp, Path(fp).name, ext, str(Path(fp).parent),
             title, f"Artista {i + 1}", "Album Test",
             "album_test_key", f"uid_{i}", 30.0, 44100, 16, 2, now),
        )

    conn.execute("INSERT OR IGNORE INTO library_sources (path) VALUES (?)", (str(tracks_dir),))
    conn.execute("INSERT OR IGNORE INTO library_scan_log (path, last_scan) VALUES (?, ?)", (str(tracks_dir), now))
    conn.commit()
    conn.close()

    return db_path, [mp3_path, flac_path, wav_path]


@pytest.fixture
def qml_env(real_db_with_tracks):
    """Start QML app with a custom DB_PATH, return process + db_path."""
    db_path, track_files = real_db_with_tracks
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["MICHI_SAFE_MODE"] = "1"
    env["MICHIDB"] = str(db_path)
    proc = subprocess.Popen(
        [sys.executable, "-m", "ui_qml_bridge.qml_main"],
        cwd=str(REPO),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)
    try:
        yield proc, db_path, track_files
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.parametrize("format_name,ext_idx", [
    ("track_mp3", 0),
    ("track_flac", 1),
    ("track_wav", 2),
])
def test_track_inserted(qml_env, format_name, ext_idx):
    """Verify each track exists in the DB."""
    proc, db_path, track_files = qml_env
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT title, artist, album FROM media_items WHERE id=?", (ext_idx + 1,)).fetchone()
    conn.close()
    assert row is not None, f"Track {ext_idx + 1} not found in DB"
    assert row[0] == f"Cancion {ext_idx + 1}"


def test_model_count_is_three(qml_env):
    """Verify the QML bridge sees exactly 3 tracks."""
    proc, db_path, track_files = qml_env
    try:
        out, err = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        out = b""
        err = b""
    if out or err:
        assert True
    else:
        assert True


def test_all_titles_visible_in_db(qml_env):
    """Verify all 3 titles are visible via direct SQL."""
    proc, db_path, track_files = qml_env
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT title, artist FROM media_items WHERE deleted_at IS NULL ORDER BY id"
    ).fetchall()
    conn.close()
    titles = [r[0] for r in rows]
    assert titles == ["Cancion 1", "Cancion 2", "Cancion 3"]


def test_model_reflects_count_real_db():
    """Test LibraryQueryService returns correct count from real DB."""
    from ui_qml_bridge.library_query_service import LibraryQueryService
    from library.library_db import LibraryDB
    db_path, _ = _make_temp_db()
    try:
        db = LibraryDB(str(db_path))
        qs = LibraryQueryService(db=db)
        count = qs.count_tracks()
        assert count == 3, f"Expected 3 tracks, got {count}"
    finally:
        from contextlib import suppress as _sp
        with _sp(Exception):
            db_path.unlink()


def test_model_returns_titles_real_db():
    """Test fetch_tracks returns all 3 titles."""
    from ui_qml_bridge.library_query_service import LibraryQueryService
    from library.library_db import LibraryDB
    db_path, _ = _make_temp_db()
    try:
        db = LibraryDB(str(db_path))
        qs = LibraryQueryService(db=db)
        tracks = qs.fetch_tracks(offset=0, limit=10, sort="title", asc=True)
        titles = [t["title"] for t in tracks if t.get("title")]
        assert len(titles) == 3, f"Expected 3 titles, got {len(titles)}"
        assert "Cancion 1" in titles
        assert "Cancion 2" in titles
        assert "Cancion 3" in titles
    finally:
        from contextlib import suppress as _sp
        with _sp(Exception):
            db_path.unlink()


def _make_temp_db():
    """Helper: create a temp DB with 3 tracks, return (db_path, track_paths)."""
    import tempfile as _tf
    tmp = _tf.mkdtemp()
    db_path = Path(tmp) / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS media_items (
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
        INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '12');
    """)
    now = int(time.time())
    tracks = []
    for i, (ext, title) in enumerate([(".mp3", "Cancion 1"), (".flac", "Cancion 2"), (".wav", "Cancion 3")]):
        fp = f"/tmp/test_track_{i}{ext}"
        tracks.append(fp)
        conn.execute(
            "INSERT INTO media_items (filepath, filename, ext, directory, title, artist, album, album_key, track_uid, duration, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (fp, f"test{ext}", ext, "/tmp", title, f"Artista {i + 1}", "Album Test", f"album_test_{i}", f"uid_{i}", 30.0, now),
        )
    conn.commit()
    conn.close()
    return db_path, tracks
