"""AlbumCache — local SQLite + file storage for album metadata."""
import json
import os
import sqlite3
import time

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Legacy paths (kept for migration compatibility)
_CACHE_DIR_LEGACY = os.path.expanduser("~/.cache/michi/artist_metadata/albums")
_DB_PATH_LEGACY = os.path.join(_CACHE_DIR_LEGACY, "index.sqlite")


def _default_cache_dir() -> str:
    from core.paths import artist_metadata_cache_dir
    return artist_metadata_cache_dir()


def _default_db_path() -> str:
    from core.paths import album_metadata_cache_db_path
    return album_metadata_cache_db_path()


CACHE_DIR = _default_cache_dir()
DB_PATH = _default_db_path()

# Full column set — everything the cache knows about
_ALL_COLS = [
    "album_key", "artist", "album", "year", "genre", "style",
    "mood", "description", "track_count", "duration",
    "thumb_path", "fanart_path", "theaudiodb_album_id",
    "theaudiodb_artist_id", "match_confidence",
    "dominant_color", "updated_at", "raw_json",
    # Cover Art Archive / extended fields (migration)
    "cover_url", "cover_path", "thumb_url",
    "fanart_url", "fanart_path",
    "musicbrainz_artist_mbid", "musicbrainz_release_group_mbid",
    "musicbrainz_release_mbid",
    "cover_source", "license",
    "fetched_at", "expires_at",
    "schema_version",
]


def _add_column(conn, col_name, col_type="TEXT DEFAULT ''"):
    """Add a column if it doesn't exist. Safe to call repeatedly."""
    existing = {r[1] for r in conn.execute("PRAGMA table_info(album_metadata)").fetchall()}
    if col_name not in existing:
        conn.execute(f"ALTER TABLE album_metadata ADD COLUMN {col_name} {col_type}")


def _ensure_db():
    os.makedirs(CACHE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS album_metadata (
            album_key TEXT PRIMARY KEY,
            artist TEXT, album TEXT, year TEXT, genre TEXT,
            style TEXT, mood TEXT, description TEXT,
            track_count INTEGER, duration REAL,
            thumb_path TEXT, fanart_path TEXT,
            theaudiodb_album_id TEXT, theaudiodb_artist_id TEXT,
            match_confidence REAL, dominant_color TEXT,
            updated_at TEXT, raw_json TEXT
        )
    """)
    # Run migrations — add missing columns non-destructively
    for col_name, col_type in [
        ("cover_url", "TEXT DEFAULT ''"), ("cover_path", "TEXT DEFAULT ''"),
        ("thumb_url", "TEXT DEFAULT ''"),
        ("fanart_url", "TEXT DEFAULT ''"), ("fanart_path", "TEXT DEFAULT ''"),
        ("musicbrainz_artist_mbid", "TEXT DEFAULT ''"),
        ("musicbrainz_release_group_mbid", "TEXT DEFAULT ''"),
        ("musicbrainz_release_mbid", "TEXT DEFAULT ''"),
        ("cover_source", "TEXT DEFAULT ''"), ("license", "TEXT DEFAULT ''"),
        ("fetched_at", "TEXT DEFAULT ''"), ("expires_at", "TEXT DEFAULT ''"),
        ("schema_version", "INTEGER DEFAULT 1"),
    ]:
        _add_column(conn, col_name, col_type)

    conn.commit()
    conn.close()


class AlbumCache(QObject):
    image_downloaded = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        _ensure_db()
        self._nam = QNetworkAccessManager(self)

    def get_metadata(self, album_key: str) -> dict | None:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.execute(
                "SELECT * FROM album_metadata WHERE album_key=?",
                (album_key,))
            row = cur.fetchone()
            cols = [d[0] for d in cur.description] if cur.description else []
            conn.close()
            if row and cols:
                result = dict(zip(cols, row, strict=False))
                # Merge raw_json if present (handles extra fields not in schema)
                raw = result.get("raw_json", "")
                if raw:
                    try:
                        extra = json.loads(raw)
                        if isinstance(extra, dict):
                            for k, v in extra.items():
                                if k not in result or not result.get(k):
                                    result[k] = v
                    except json.JSONDecodeError:
                        pass
                return result
        except (sqlite3.Error, OSError):
            pass
        return None

    def save_metadata(self, album_key: str, data: dict):
        _ensure_db()
        cols = _ALL_COLS
        values = [data.get(c, "") for c in cols]
        values[0] = album_key
        data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # updated_at is at index 16, raw_json is at index 17
        for ci, cname in enumerate(cols):
            if cname == "updated_at":
                values[ci] = data["updated_at"]
            elif cname == "raw_json":
                values[ci] = json.dumps(data, ensure_ascii=False)
            elif cname == "schema_version":
                values[ci] = 2

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                f"INSERT OR REPLACE INTO album_metadata"
                f" ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
                values)
            conn.commit()
            conn.close()
        except (sqlite3.Error, OSError):
            pass

    def is_stale(self, album_key: str, days: int = 30) -> bool:
        data = self.get_metadata(album_key)
        if not data:
            return True
        updated = data.get("updated_at", "")
        try:
            t = time.mktime(time.strptime(updated, "%Y-%m-%d %H:%M:%S"))
            return time.time() - t > days * 86400
        except (ValueError, TypeError):
            return True

    def cache_not_found(self, album_key: str):
        """Save negative cache entry to avoid repeated lookups."""
        self.save_metadata(album_key, {
            "_not_found": True,
            "album_key": album_key,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    def is_negative(self, album_key: str) -> bool:
        data = self.get_metadata(album_key)
        return bool(data and data.get("_not_found"))

    def download_image(self, url: str, target: str, callback_key: str):
        if not url or os.path.exists(target):
            return
        os.makedirs(os.path.dirname(target), exist_ok=True)
        req = QNetworkRequest(QUrl(url))
        reply = self._nam.get(req)
        reply.finished.connect(
            lambda r=reply, t=target, k=callback_key:
            self._on_image(r, t, k))

    def _on_image(self, reply: QNetworkReply, target: str, key: str):
        if reply.error() == QNetworkReply.NoError:
            try:
                with open(target, "wb") as f:
                    f.write(bytes(reply.readAll()))
                self.image_downloaded.emit(key, target)
            except OSError:
                pass
        reply.deleteLater()

    def clear_album(self, album_key: str):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM album_metadata WHERE album_key=?",
                         (album_key,))
            conn.commit()
            conn.close()
        except (sqlite3.Error, OSError):
            pass
