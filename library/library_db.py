"""Library database, scanner, and data model for the music player.

Features:
    - SQLite with WAL mode (thread-safe, check_same_thread=False)
    - Recursive directory scanner with GStreamer Discoverer metadata
    - QAbstractListModel for QListView/QTableView
    - Playlist CRUD
    - Device detection
"""

import os
import sqlite3
import time
import hashlib
from dataclasses import dataclass, field
from typing import Callable

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import Gst, GstPbutils

from PySide6.QtCore import (
    QAbstractListModel, QModelIndex, Qt, Signal, QObject,
)

Gst.init(None)

# ── Extensions ──

AUDIO_EXTS = frozenset({
    ".ogg", ".oga", ".opus", ".flac", ".wav", ".wv", ".spx",
    ".mp3", ".dsf", ".dff", ".aiff", ".aif", ".ape", ".tta",
    ".m4a", ".aac", ".ac3", ".shn", ".wma",
})
ALL_EXTS = AUDIO_EXTS

DB_PATH = os.path.expanduser("~/.local/share/astra-music-player/library.db")


def media_kind(ext: str) -> str:
    return "audio" if ext.lower() in AUDIO_EXTS else "unknown"


# ── Schema ──

# see LibraryDB.__init__ for inline schema creation

# ── Data class ──

@dataclass
class MediaItem:
    id: int = 0
    filepath: str = ""
    filename: str = ""
    directory: str = ""
    ext: str = ""
    kind: str = ""
    size: int = 0
    mtime: float = 0.0
    duration: float = 0.0
    channels: int = 0
    sample_rate: int = 0
    bitrate: int = 0
    title: str = ""
    artist: str = ""
    album: str = ""
    year: int = 0
    genre: str = ""
    track_number: int = 0
    composer: str = ""

    @property
    def display_title(self) -> str:
        if self.artist and self.title:
            return f"{self.artist} — {self.title}"
        return self.title or self.filename

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return ""
        m = int(self.duration // 60)
        s = int(self.duration % 60)
        if self.duration >= 3600:
            h = int(self.duration // 3600)
            m = int((self.duration % 3600) // 60)
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @classmethod
    def from_row(cls, row: tuple) -> "MediaItem":
        return cls(
            id=row[0], filepath=row[1], filename=row[2], directory=row[3],
            ext=row[4] or "", kind=row[5] or "", size=row[6] or 0,
            mtime=row[7] or 0.0, duration=row[8] or 0.0,
            channels=row[9] or 0, sample_rate=row[10] or 0,
            bitrate=row[11] or 0, title=row[12] or "",
            artist=row[13] or "", album=row[14] or "",
            year=row[15] if len(row) > 15 and row[15] else 0,
            genre=row[16] if len(row) > 16 and row[16] else "",
            track_number=row[17] if len(row) > 17 and row[17] else 0,
            composer=row[18] if len(row) > 18 and row[18] else "",
        )


# ── Metadata extraction ──

def extract_metadata(filepath: str) -> dict:
    """Extract duration, sample_rate, channels, bitrate, tags via GStreamer."""
    info = {"duration": 0.0, "channels": 0, "sample_rate": 0,
            "bitrate": 0, "title": "", "artist": "", "album": ""}
    try:
        uri = "file://" + os.path.abspath(filepath)
        discoverer = GstPbutils.Discoverer.new(5 * Gst.SECOND)
        disc = discoverer.discover_uri(uri)
        if disc is None:
            return info

        dur = disc.get_duration()
        if dur > 0:
            info["duration"] = dur / 1e9

        tags = disc.get_tags()
        if tags:
            ok, v = tags.get_string(Gst.TAG_TITLE)
            if ok: info["title"] = v
            ok, v = tags.get_string(Gst.TAG_ARTIST)
            if ok: info["artist"] = v
            ok, v = tags.get_string(Gst.TAG_ALBUM)
            if ok: info["album"] = v

        streams = disc.get_audio_streams()
        if streams:
            s = streams[0]
            info["sample_rate"] = s.get_sample_rate() or 0
            info["channels"] = s.get_channels() or 0
            info["bitrate"] = s.get_bitrate() or 0
    except Exception:
        pass
    return info


def extract_metadata_full(filepath: str) -> dict:
    """Extract full metadata including year, genre, track, composer, cover art via mutagen."""
    info = {"year": 0, "genre": "", "track_number": 0, "composer": "",
            "cover_mime": "", "cover_data": b""}
    try:
        from mutagen import File as MutagenFile
        mf = MutagenFile(filepath)
        if mf is None:
            return info
        if mf.tags:
            if hasattr(mf.tags, 'get'):
                def get_tag(tags, *names):
                    for n in names:
                        val = tags.get(n)
                        if val:
                            if isinstance(val, list):
                                return str(val[0])
                            return str(val)
                    return ""
                info["composer"] = get_tag(mf.tags, "composer", "TPE1", "©wrt", "TCOM")
                genre_val = get_tag(mf.tags, "genre", "TCON", "©gen")
                try:
                    if genre_val and genre_val.startswith("(") and ")" in genre_val:
                        genre_val = genre_val.split(")", 1)[-1].strip()
                except Exception:
                    pass
                info["genre"] = genre_val
                year_val = get_tag(mf.tags, "date", "year", "TYER", "©day", "TDRC")
                try:
                    info["year"] = int(year_val[:4]) if year_val else 0
                except Exception:
                    info["year"] = 0
                track_val = get_tag(mf.tags, "tracknumber", "TRCK", "track", "trkn")
                try:
                    info["track_number"] = int(track_val.split("/")[0]) if track_val else 0
                except Exception:
                    info["track_number"] = 0
        for tag_type in mf or []:
            if tag_type and (b'APIC' in str(tag_type).encode() or 'APIC' in str(tag_type)):
                try:
                    cover = mf.tags.get(tag_type)
                    if cover:
                        info["cover_mime"] = cover.mime if hasattr(cover, 'mime') else "image/jpeg"
                        info["cover_data"] = cover.data if hasattr(cover, 'data') else b""
                except Exception:
                    pass
                break
        if not info["cover_data"]:
            for key in (b'APIC:', 'APIC:'):
                try:
                    val = mf.tags.get(key)
                    if val:
                        info["cover_mime"] = getattr(val, 'mime', 'image/jpeg')
                        info["cover_data"] = getattr(val, 'data', b'')
                        break
                except Exception:
                    pass
        if not info["cover_data"] and hasattr(mf, 'pictures'):
            pics = getattr(mf, 'pictures', [])
            if pics:
                try:
                    p = pics[0]
                    info["cover_mime"] = getattr(p, 'mime', 'image/jpeg')
                    info["cover_data"] = getattr(p, 'data', b'')
                except Exception:
                    pass
    except Exception:
        pass
    return info


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
        self._run_migrations()
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_dir ON media_items(directory)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_kind ON media_items(kind)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_title ON media_items(title)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_artist ON media_items(artist)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_album ON media_items(album)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_genre ON media_items(genre)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_year ON media_items(year)")
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS playlists (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL UNIQUE,
            created REAL DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS playlist_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
            filepath    TEXT NOT NULL,
            position    INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS queue_state (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath    TEXT NOT NULL,
            position    INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS play_history (
            track_id    TEXT NOT NULL,
            device      TEXT NOT NULL,
            play_count  INTEGER DEFAULT 0,
            last_played REAL DEFAULT 0,
            PRIMARY KEY (track_id, device)
        );
        CREATE TABLE IF NOT EXISTS favorites (
            track_id    TEXT NOT NULL,
            device      TEXT NOT NULL,
            PRIMARY KEY (track_id, device)
        );
        CREATE TABLE IF NOT EXISTS album_art_cache (
            album_hash  TEXT PRIMARY KEY,
            mime        TEXT NOT NULL,
            data        BLOB NOT NULL
        );
        """)
        self._conn.commit()

    def _run_migrations(self):
        existing = {r[0] for r in self._conn.execute("PRAGMA table_info(media_items)").fetchall()}
        for col, col_def in [("year", "INTEGER"), ("genre", "TEXT"),
                              ("track_number", "INTEGER"), ("composer", "TEXT")]:
            if col not in existing:
                try:
                    self._conn.execute(f"ALTER TABLE media_items ADD COLUMN {col} {col_def}")
                except sqlite3.OperationalError:
                    pass

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

        try:
            cur = self._conn.execute(
                """INSERT OR REPLACE INTO media_items
                   (filepath,filename,directory,ext,kind,size,mtime,
                    duration,channels,sample_rate,bitrate,title,artist,album,
                    year,genre,track_number,composer)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (filepath, fname, dname, ext, kind, stat.st_size,
                 stat.st_mtime, meta["duration"], meta["channels"],
                 meta["sample_rate"], meta["bitrate"], title, artist, album,
                 year, genre, track_number, composer),
            )
            self._conn.commit()

            if meta_full.get("cover_data") and album:
                album_hash = hashlib.md5(album.encode()).hexdigest()
                try:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO album_art_cache (album_hash, mime, data) "
                        "VALUES (?,?,?)",
                        (album_hash, meta_full["cover_mime"] or "image/jpeg",
                         meta_full["cover_data"]))
                    self._conn.commit()
                except Exception:
                    pass

            return cur.lastrowid
        except Exception:
            return None

    def remove_file(self, filepath: str):
        self._conn.execute("DELETE FROM media_items WHERE filepath=?", (filepath,))
        self._conn.commit()

    def remove_missing(self) -> int:
        rows = self._conn.execute("SELECT id,filepath FROM media_items").fetchall()
        n = 0
        for rid, fp in rows:
            if not os.path.exists(fp):
                self._conn.execute("DELETE FROM media_items WHERE id=?", (rid,))
                n += 1
        self._conn.commit()
        return n

    def get_all(self, kind: str | None = None, search: str | None = None,
                group_by: str = "") -> list[MediaItem]:
        if group_by == "album":
            query = (
                "SELECT m.* FROM media_items m "
                "JOIN (SELECT album, artist, MIN(id) as mid FROM media_items "
                "WHERE album != '' GROUP BY album, artist) g "
                "ON m.id = g.mid WHERE 1=1"
            )
        elif group_by == "artist":
            query = (
                "SELECT m.* FROM media_items m "
                "JOIN (SELECT artist, MIN(id) as mid FROM media_items "
                "WHERE artist != '' GROUP BY artist) g "
                "ON m.id = g.mid WHERE 1=1"
            )
        else:
            query = "SELECT * FROM media_items WHERE 1=1"

        params: list = []
        if kind:
            query += " AND kind=?"
            params.append(kind)
        if search:
            query += " AND (title LIKE ? OR artist LIKE ? OR album LIKE ? OR filename LIKE ?)"
            t = f"%{search}%"
            params.extend([t, t, t, t])
        query += " ORDER BY title COLLATE NOCASE"
        rows = self._conn.execute(query, params).fetchall()
        return [MediaItem.from_row(r) for r in rows]

    def get_directories(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT directory FROM media_items ORDER BY directory"
        ).fetchall()
        return [r[0] for r in rows]

    def get_stats(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
        audio = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE kind='audio'").fetchone()[0]
        video = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE kind='video'").fetchone()[0]
        return {"total": total, "audio": audio, "video": video}

    def scan_directory(self, path: str,
                       progress: Callable = None) -> int:
        files = []
        for root, dirs, fnames in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in fnames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in ALL_EXTS:
                    files.append(os.path.join(root, fn))

        added = 0
        for i, fp in enumerate(files):
            if self.add_file(fp) is not None:
                added += 1
            if progress:
                progress(i + 1, len(files), fp)
        return added

    # ── Playlists ──

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
            "SELECT id,name,created FROM playlists ORDER BY name").fetchall()
        return [{"id": r[0], "name": r[1], "created": r[2]} for r in rows]

    def add_to_playlist(self, pid: int, filepath: str):
        pos = self._conn.execute(
            "SELECT COALESCE(MAX(position),-1)+1 FROM playlist_items "
            "WHERE playlist_id=?", (pid,)).fetchone()[0]
        self._conn.execute(
            "INSERT INTO playlist_items (playlist_id,filepath,position) "
            "VALUES (?,?,?)", (pid, filepath, pos))
        self._conn.commit()

    def get_playlist_items(self, pid: int) -> list[MediaItem]:
        rows = self._conn.execute(
            "SELECT m.* FROM media_items m "
            "JOIN playlist_items pi ON m.filepath=pi.filepath "
            "WHERE pi.playlist_id=? ORDER BY pi.position", (pid,)
        ).fetchall()
        return [MediaItem.from_row(r) for r in rows]

    def save_queue(self, filepaths: list[str], current_index: int):
        self._conn.execute("DELETE FROM queue_state")
        for i, fp in enumerate(filepaths):
            self._conn.execute(
                "INSERT INTO queue_state (filepath, position) VALUES (?,?)",
                (fp, i))
        idx = max(-1, current_index)
        self._conn.execute(f"PRAGMA user_version = {idx}")
        self._conn.commit()

    def load_queue(self) -> tuple[list[str], int]:
        rows = self._conn.execute(
            "SELECT filepath FROM queue_state ORDER BY position").fetchall()
        idx_row = self._conn.execute("PRAGMA user_version").fetchone()
        idx = idx_row[0] if idx_row else -1
        return [r[0] for r in rows], idx

    def clear_queue_state(self):
        self._conn.execute("DELETE FROM queue_state")
        self._conn.commit()

    def update_play_history(self, track_id: str, device: str = "desktop"):
        self._conn.execute(
            "INSERT INTO play_history (track_id, device, play_count, last_played) "
            "VALUES (?,?,1,strftime('%s','now')) "
            "ON CONFLICT(track_id, device) DO UPDATE SET "
            "play_count=play_count+1, last_played=strftime('%s','now')",
            (track_id, device))
        self._conn.commit()

    def toggle_favorite(self, track_id: str, device: str = "desktop") -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM favorites WHERE track_id=? AND device=?",
            (track_id, device))
        if cur.fetchone():
            self._conn.execute(
                "DELETE FROM favorites WHERE track_id=? AND device=?",
                (track_id, device))
            self._conn.commit()
            return False
        self._conn.execute(
            "INSERT INTO favorites (track_id, device) VALUES (?,?)",
            (track_id, device))
        self._conn.commit()
        return True

    def get_favorites(self, device: str = "desktop") -> list[str]:
        rows = self._conn.execute(
            "SELECT track_id FROM favorites WHERE device=?", (device,)).fetchall()
        return [r[0] for r in rows]

    def get_play_history(self, device: str = "desktop") -> list[dict]:
        rows = self._conn.execute(
            "SELECT track_id, play_count, last_played FROM play_history "
            "WHERE device=? ORDER BY last_played DESC", (device,)).fetchall()
        return [{"track_id": r[0], "play_count": r[1], "last_played": r[2]}
                for r in rows]


# ── Scanner Worker (QThread-safe) ──

class ScannerWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(int)

    def __init__(self, db: LibraryDB, path: str, parent=None):
        super().__init__(parent)
        self._db = db
        self._path = path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        files = []
        for root, dirs, fnames in os.walk(self._path):
            if self._cancelled: break
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in fnames:
                if os.path.splitext(fn)[1].lower() in ALL_EXTS:
                    files.append(os.path.join(root, fn))

        total = len(files)
        added = 0
        for i, fp in enumerate(files):
            if self._cancelled: break
            if self._db.add_file(fp) is not None:
                added += 1
            self.progress.emit(i + 1, total, fp)
        self.finished.emit(added)


# ── Devices ──

def get_mounted_devices() -> list[dict]:
    devices = []
    import subprocess
    try:
        r = subprocess.run(["lsblk", "-ln", "-o", "NAME,MOUNTPOINT,FSTYPE,LABEL"],
                          capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) < 2 or not parts[1].startswith("/"): continue
            mount = parts[1]
            if mount in ("/", "/boot", "/home", "/etc", "/var", "/usr", "/opt"): continue
            if any(mount.startswith(x) for x in ("/sys", "/proc", "/dev", "/run/")): continue
            label = parts[3] if len(parts) > 3 else os.path.basename(mount)
            devices.append({"name": label, "mount": mount})
    except Exception:
        pass
    for base in ("/run/media/" + os.environ.get("USER", ""), "/media"):
        if os.path.isdir(base):
            for e in os.listdir(base):
                mp = os.path.join(base, e)
                if (os.path.ismount(mp) or os.path.isdir(mp)) and \
                   not any(d["mount"] == mp for d in devices):
                    devices.append({"name": e, "mount": mp})
    return devices


def scan_device_music(mount: str) -> list[str]:
    files = []
    try:
        for root, dirs, fnames in os.walk(mount):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in fnames:
                if os.path.splitext(fn)[1].lower() in ALL_EXTS:
                    files.append(os.path.join(root, fn))
            if len(files) > 500: break
    except PermissionError:
        pass
    return files
