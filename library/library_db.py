"""Library database, scanner, and data model for the music player.

Features:
    - SQLite with WAL mode (thread-safe, check_same_thread=False)
    - Recursive directory scanner with GStreamer Discoverer metadata
    - Playlist CRUD
    - Device detection
"""
import os
import sqlite3
import logging
import contextlib
from typing import Callable

logger = logging.getLogger("astra.library")

from PySide6.QtCore import Signal, QObject  # noqa: E402

# ── Re-exports from split modules ──
from library.metadata_extractor import AUDIO_EXTS, ALL_EXTS, extract_metadata, extract_metadata_full  # noqa: E402, F401
from library.media_item import MediaItem, media_kind  # noqa: E402
from library.devices import get_mounted_devices, scan_device_music  # noqa: E402, F401

DB_PATH = os.path.expanduser("~/.local/share/astra-music-player/library.db")


# ── Schema ──

# see LibraryDB.__init__ for inline schema creation


# ── Database ──

class LibraryDB:
    def __init__(self, db_path: str = DB_PATH):
        dir_name = os.path.dirname(db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS media_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath    TEXT UNIQUE NOT NULL,
            filename    TEXT NOT NULL,
            directory   TEXT NOT NULL,
            ext         TEXT NOT NULL,
            kind        TEXT NOT NULL,
            size        INTEGER,
            mtime       REAL,
            duration    REAL,
            channels    INTEGER,
            sample_rate INTEGER,
            bitrate     INTEGER,
            title       TEXT,
            artist      TEXT,
            album       TEXT,
            year        INTEGER,
            genre       TEXT,
            track_number INTEGER,
            composer    TEXT,
            date_added  REAL DEFAULT (strftime('%s','now'))
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS playlists (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cover_path TEXT DEFAULT '',
            cover_type TEXT DEFAULT 'mosaic',
            description TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s','now'))
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS playlist_items (
            playlist_id INTEGER NOT NULL REFERENCES playlists(id),
            filepath    TEXT NOT NULL
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS queue_state (
            id INTEGER PRIMARY KEY,
            filepath TEXT NOT NULL
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS play_history (
            track_id   TEXT NOT NULL,
            device     TEXT DEFAULT 'desktop',
            played_at  REAL DEFAULT (strftime('%s','now'))
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS favorites (
            track_id TEXT NOT NULL UNIQUE,
            device   TEXT DEFAULT 'desktop',
            added_at REAL DEFAULT (strftime('%s','now'))
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS album_art_cache (
            album_hash TEXT PRIMARY KEY,
            mime       TEXT,
            data       BLOB
        )""")
        self._conn.execute("""CREATE TABLE IF NOT EXISTS detected_tracks (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT NOT NULL,
            artist    TEXT NOT NULL,
            album     TEXT,
            year      INTEGER,
            genre     TEXT,
            duration  REAL,
            source    TEXT DEFAULT '',
            provider  TEXT DEFAULT '',
            confidence REAL,
            isrc      TEXT,
            artwork_url TEXT,
            external_url TEXT,
            filepath  TEXT,
            matched_library_id INTEGER,
            raw_json  TEXT,
            detected_at REAL NOT NULL
        )""")
        self._conn.commit()

        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pl_filepath ON playlist_items(filepath)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pl_playlist ON playlist_items(playlist_id)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_detected_tracks_time ON detected_tracks(detected_at DESC)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_detected_tracks_artist_title ON detected_tracks(artist, title)")
        self._conn.commit()
        self._run_migrations()

    def _run_migrations(self):
        existing = {r[0] for r in self._conn.execute("PRAGMA table_info(media_items)").fetchall()}
        for col, col_def in [("year", "INTEGER"), ("genre", "TEXT"),
                              ("track_number", "INTEGER"), ("composer", "TEXT"),
                              ("albumartist", "TEXT"), ("disc_number", "INTEGER"),
                              ("disc_total", "INTEGER"), ("track_total", "INTEGER"),
                              ("mb_track_id", "TEXT"), ("mb_album_id", "TEXT"),
                              ("cover_hash", "TEXT"), ("rating", "INTEGER DEFAULT 0"),
                              ("play_count", "INTEGER DEFAULT 0"), ("skip_count", "INTEGER DEFAULT 0"),
                              ("last_played", "REAL"), ("bpm", "INTEGER"),
                              ("replaygain_track", "REAL"), ("replaygain_album", "REAL")]:
            if col not in existing:
                with contextlib.suppress(sqlite3.OperationalError):
                    self._conn.execute(f"ALTER TABLE media_items ADD COLUMN {col} {col_def}")

        # Playlist cover fields
        playlist_existing = {r[0] for r in self._conn.execute("PRAGMA table_info(playlists)").fetchall()}
        for col, col_def in [("cover_path", "TEXT DEFAULT ''"),
                              ("cover_type", "TEXT DEFAULT 'mosaic'"),
                              ("description", "TEXT DEFAULT ''"),
                              ("created_at", "REAL DEFAULT (strftime('%s','now'))")]:
            if col not in playlist_existing:
                with contextlib.suppress(sqlite3.OperationalError):
                    self._conn.execute(f"ALTER TABLE playlists ADD COLUMN {col} {col_def}")

        # Detected tracks extended fields
        dt_existing = {r[0] for r in self._conn.execute("PRAGMA table_info(detected_tracks)").fetchall()}
        for col, col_def in [("source_type", "TEXT DEFAULT ''"),
                              ("source_label", "TEXT DEFAULT ''"),
                              ("source_uri", "TEXT DEFAULT ''"),
                              ("match_status", "TEXT DEFAULT ''"),
                              ("matched_filepath", "TEXT DEFAULT ''"),
                              ("provider_track_id", "TEXT DEFAULT ''"),
                              ("provider_artist_id", "TEXT DEFAULT ''"),
                              ("album_art_path", "TEXT DEFAULT ''"),
                              ("latency_ms", "INTEGER DEFAULT 0")]:
            if col not in dt_existing:
                with contextlib.suppress(sqlite3.OperationalError):
                    self._conn.execute(f"ALTER TABLE detected_tracks ADD COLUMN {col} {col_def}")

    def close(self):
        self._conn.close()

    def add_file(self, filepath: str) -> int | None:
        if not os.path.exists(filepath):
            return None
        ext = os.path.splitext(filepath)[1].lower()
        kind = media_kind(ext)
        if kind == "unknown":
            return None

        stat = os.stat(filepath)
        meta = extract_metadata(filepath)
        meta_full = extract_metadata_full(filepath)
        fname = os.path.basename(filepath)
        dname = os.path.dirname(filepath)
        title = meta["title"] or fname
        artist = meta["artist"] or ""
        album = meta["album"] or ""
        year = meta_full.get("year", 0)
        genre = meta_full.get("genre", "")
        track_number = meta_full.get("track_number", 0)
        composer = meta_full.get("composer", "")

        # Store embedded cover art in album_art_cache
        cover_data = meta_full.get("cover_data", b"")
        if cover_data and album:
            import hashlib
            album_hash = hashlib.md5(album.encode()).hexdigest()
            cover_mime = meta_full.get("cover_mime", "image/jpeg")
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO album_art_cache (album_hash, mime, data) VALUES (?,?,?)",
                    (album_hash, cover_mime, cover_data))
                self._conn.commit()
            except Exception:
                import logging
                logging.getLogger("astra").debug("Failed to cache embedded cover for %s", album)

        try:
            cur = self._conn.execute(
                "INSERT OR REPLACE INTO media_items "
                "(filepath, filename, directory, ext, kind, size, mtime, duration, "
                " channels, sample_rate, bitrate, title, artist, album, year, genre, "
                " track_number, composer) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (filepath, fname, dname, ext, kind, stat.st_size, stat.st_mtime,
                 meta["duration"], meta["channels"], meta["sample_rate"], meta["bitrate"],
                 title[:256], artist[:256], album[:256], year, genre[:128],
                 track_number, composer[:256]))
            self._conn.commit()
            return cur.lastrowid
        except Exception:
            import logging
            logging.getLogger("astra").debug("Scanner: commit after add_file failed")

    def remove_file(self, filepath: str):
        self._conn.execute("DELETE FROM media_items WHERE filepath=?", (filepath,))
        self._conn.commit()

    def remove_missing(self) -> int:
        rows = self._conn.execute("SELECT id, filepath FROM media_items").fetchall()
        missing = [rid for rid, fp in rows if not os.path.exists(fp)]
        for rid in missing:
            self._conn.execute("DELETE FROM media_items WHERE id=?", (rid,))
        self._conn.commit()
        return len(missing)

    def get_all(self, kind: str | None = None, search: str | None = None,
                 group_by: str = "") -> list[MediaItem]:
        query = "SELECT * FROM media_items"
        params = []
        conditions = []
        if kind:
            conditions.append("kind = ?")
            params.append(kind)
        if search:
            conditions.append(
                "(title LIKE ? OR artist LIKE ? OR album LIKE ? OR filepath LIKE ?)")
            q = f"%{search}%"
            params.extend([q, q, q, q])
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        if group_by and group_by in ("artist", "album", "genre"):
            query += f" ORDER BY {group_by} ASC, title ASC"
        else:
            query += " ORDER BY title ASC"
        rows = self._conn.execute(query, params).fetchall()
        return [MediaItem.from_row(r) for r in rows]

    def get_directories(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT directory FROM media_items ORDER BY directory").fetchall()
        return [r[0] for r in rows]

    def get_stats(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
        audio = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE kind='audio'").fetchone()[0]
        video = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE kind='video'").fetchone()[0]
        dur = self._conn.execute(
            "SELECT COALESCE(SUM(duration),0) FROM media_items").fetchone()[0] or 0
        return {"total": total, "audio": audio, "video": video, "duration": dur}

    def scan_directory(self, path: str,
                       progress_callback: Callable | None = None) -> int:
        files = []
        for root, dirs, fnames in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in fnames:
                if os.path.splitext(fn)[1].lower() in ALL_EXTS:
                    files.append(os.path.join(root, fn))
        added = 0
        total = len(files)
        for i, fp in enumerate(files):
            if self.add_file(fp) is not None:
                added += 1
            if progress_callback:
                progress_callback(i + 1, total)
        return added

    # ── Playlists ──

    # Extracted to library/playlist_store.py — CRUD playlists
    def create_playlist(self, name: str) -> int:
        cur = self._conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        self._conn.commit()
        return cur.lastrowid

    def delete_playlist(self, pid: int):
        self._conn.execute("DELETE FROM playlist_items WHERE playlist_id=?", (pid,))
        self._conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
        self._conn.commit()

    def get_playlists(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, name, cover_path, cover_type, description, created_at "
            "FROM playlists ORDER BY name").fetchall()
        return [{"id": r[0], "name": r[1], "cover_path": r[2] or "",
                 "cover_type": r[3] or "mosaic", "description": r[4] or "",
                 "created_at": r[5] if len(r) > 5 else 0}
                for r in rows]

    def update_playlist(self, pid: int, name: str = "", description: str = "",
                        cover_path: str = "", cover_type: str = ""):
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if cover_path is not None:
            updates.append("cover_path = ?")
            params.append(cover_path)
        if cover_type is not None:
            updates.append("cover_type = ?")
            params.append(cover_type)
        if updates:
            params.append(pid)
            self._conn.execute(
                f"UPDATE playlists SET {', '.join(updates)} WHERE id = ?", params)
            self._conn.commit()

    def add_to_playlist(self, pid: int, filepath: str):
        self._conn.execute(
            "INSERT OR IGNORE INTO playlist_items (playlist_id, filepath) VALUES (?,?)",
            (pid, filepath))
        self._conn.commit()

    def get_playlist_items(self, pid: int) -> list[MediaItem]:
        rows = self._conn.execute(
            "SELECT m.* FROM media_items m "
            "JOIN playlist_items p ON m.filepath = p.filepath "
            "WHERE p.playlist_id = ? ORDER BY m.title",
            (pid,)).fetchall()
        return [MediaItem.from_row(r) for r in rows]

    # Extracted to library/history_store.py — favorites, play history, detected tracks
    def save_queue(self, filepaths: list[str], current_index: int):
        self._conn.execute("DELETE FROM queue_state")
        for i, fp in enumerate(filepaths):
            self._conn.execute("INSERT INTO queue_state (id, filepath) VALUES (?,?)", (i, fp))
        self._conn.commit()

    def load_queue(self) -> tuple[list[str], int]:
        rows = self._conn.execute(
            "SELECT id, filepath FROM queue_state ORDER BY id").fetchall()
        filepaths = [r[1] for r in rows]
        return filepaths, 0

    def clear_queue_state(self):
        self._conn.execute("DELETE FROM queue_state")
        self._conn.commit()

    def update_play_history(self, track_id: str, device: str = "desktop"):
        self._conn.execute(
            "INSERT INTO play_history (track_id, device) VALUES (?,?)", (track_id, device))
        self._conn.commit()

    def toggle_favorite(self, track_id: str, device: str = "desktop") -> bool:
        cur = self._conn.execute(
            "SELECT track_id FROM favorites WHERE track_id = ?", (track_id,))
        if cur.fetchone():
            self._conn.execute("DELETE FROM favorites WHERE track_id = ?", (track_id,))
            self._conn.commit()
            return False
        self._conn.execute(
            "INSERT INTO favorites (track_id, device) VALUES (?,?)", (track_id, device))
        self._conn.commit()
        return True

    def get_favorites(self, device: str = "desktop") -> list[str]:
        rows = self._conn.execute(
            "SELECT track_id FROM favorites ORDER BY added_at DESC").fetchall()
        return [r[0] for r in rows]

    def get_play_history(self, device: str = "desktop") -> list[dict]:
        rows = self._conn.execute(
            "SELECT track_id, played_at FROM play_history ORDER BY played_at DESC LIMIT 100"
        ).fetchall()
        return [{"track_id": r[0], "played_at": r[1]} for r in rows]

    # ── Detected Tracks ──

    def add_detected_track(
        self, title: str, artist: str, album: str = "", year: int = 0,
        genre: str = "", duration: float = 0.0, source: str = "",
        provider: str = "", confidence: float = 0.0, isrc: str = "",
        artwork_url: str = "", external_url: str = "", filepath: str = "",
        matched_library_id: int = 0, raw_json: str = ""
    ):
        self._conn.execute(
            "INSERT INTO detected_tracks (title,artist,album,year,genre,duration,"
            "source,provider,confidence,isrc,artwork_url,external_url,filepath,"
            "matched_library_id,raw_json,detected_at) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,strftime('%s','now'))",
            (title, artist, album, year, genre, duration, source, provider,
             confidence, isrc, artwork_url, external_url, filepath,
             matched_library_id, raw_json))
        self._conn.commit()

    def get_detected_tracks(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM detected_tracks ORDER BY detected_at DESC LIMIT ?",
            (limit,)).fetchall()
        cols = [desc[0] for desc in self._conn.execute(
            "PRAGMA table_info(detected_tracks)").fetchall()]
        return [dict(zip(cols, r, strict=False)) for r in rows]

    def clear_detected_tracks(self):
        self._conn.execute("DELETE FROM detected_tracks")
        self._conn.commit()

    def delete_detected_track(self, track_id: int):
        self._conn.execute("DELETE FROM detected_tracks WHERE id = ?", (track_id,))
        self._conn.commit()

    def find_detected_track_recent(
        self, title: str, artist: str, max_age_hours: int = 24
    ) -> dict | None:
        rows = self._conn.execute(
            "SELECT * FROM detected_tracks WHERE title=? AND artist=? "
            "AND detected_at > strftime('%s','now') - ? ORDER BY detected_at DESC LIMIT 1",
            (title, artist, max_age_hours * 3600)).fetchall()
        if not rows:
            return None
        cols = [desc[0] for desc in self._conn.execute(
            "PRAGMA table_info(detected_tracks)").fetchall()]
        return dict(zip(cols, rows[0], strict=False))


# ── Scanner Worker (QThread-safe) ──

class ScannerWorker(QObject):
    finished = Signal(int)
    progress = Signal(int, int, str)

    def __init__(self, db: LibraryDB, path: str, parent=None):
        super().__init__(parent)
        self._db = db
        self._path = path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total = sum(1 for _ in self._walk_files())
        added = 0
        files = list(self._walk_files())
        for i, fp in enumerate(files):
            if self._cancelled:
                break
            if self._db.add_file(fp) is not None:
                added += 1
            self.progress.emit(i + 1, total, fp)
        self.finished.emit(added)

    def _walk_files(self):
        for root, dirs, fnames in os.walk(self._path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in fnames:
                if os.path.splitext(fn)[1].lower() in ALL_EXTS:
                    yield os.path.join(root, fn)


# Extracted to library/devices.py
# get_mounted_devices and scan_device_music are now in library/devices.py
