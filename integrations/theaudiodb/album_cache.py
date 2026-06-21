"""AlbumCache — local SQLite + file storage for album metadata."""
import json
import os
import sqlite3
import time

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

CACHE_DIR = os.path.expanduser("~/.cache/astra/artist_metadata/albums")
DB_PATH = os.path.join(CACHE_DIR, "index.sqlite")


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
            row = conn.execute(
                "SELECT * FROM album_metadata WHERE album_key=?",
                (album_key,)).fetchone()
            conn.close()
            if row:
                cols = [c[0] for c in conn.execute(
                    "PRAGMA table_info(album_metadata)").fetchall()]
                return dict(zip(cols, row, strict=False))
        except (sqlite3.Error, OSError):
            pass
        return None

    def save_metadata(self, album_key: str, data: dict):
        _ensure_db()
        cols = ["album_key", "artist", "album", "year", "genre", "style",
                "mood", "description", "track_count", "duration",
                "thumb_path", "fanart_path", "theaudiodb_album_id",
                "theaudiodb_artist_id", "match_confidence",
                "dominant_color", "updated_at", "raw_json"]
        values = [data.get(c, "") for c in cols]
        values[0] = album_key
        data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        values[-3] = data["updated_at"]
        values[-1] = json.dumps(data, ensure_ascii=False)
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
