"""Artist metadata cache — stores artist data and images locally."""
import json
import os
import time

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

CACHE_DIR = os.path.expanduser("~/.cache/astra/artist_metadata")
METADATA_DIR = os.path.join(CACHE_DIR, "metadata")
IMAGES_DIR = os.path.join(CACHE_DIR, "images")


def _ensure_dirs():
    os.makedirs(METADATA_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)


class ArtistCache(QObject):
    image_downloaded = Signal(str, str)  # artist_key, local_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        _ensure_dirs()

    def get_cached_artist(self, artist_key: str) -> dict | None:
        path = os.path.join(METADATA_DIR, f"{artist_key}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def save_artist(self, artist_key: str, data: dict):
        _ensure_dirs()
        path = os.path.join(METADATA_DIR, f"{artist_key}.json")
        try:
            with open(path, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def is_stale(self, artist_key: str, days: int = 30) -> bool:
        path = os.path.join(METADATA_DIR, f"{artist_key}.json")
        if not os.path.exists(path):
            return True
        stale = time.time() - os.path.getmtime(path)
        return stale > (days * 86400)

    def download_image(self, url: str, target_name: str, artist_key: str):
        if not url or os.path.exists(target_name):
            return
        _ensure_dirs()
        req = QNetworkRequest(QUrl(url))
        reply = self._nam.get(req)
        reply.finished.connect(
            lambda r=reply, t=target_name, k=artist_key:
            self._on_image_done(r, t, k))

    def _on_image_done(self, reply: QNetworkReply, target: str, artist_key: str):
        err = reply.error()
        if err == QNetworkReply.NoError:
            data = bytes(reply.readAll())
            os.makedirs(os.path.dirname(target), exist_ok=True)
            try:
                with open(target, "wb") as f:
                    f.write(data)
                self.image_downloaded.emit(artist_key, target)
            except OSError:
                pass
        reply.deleteLater()

    def clear_artist_cache(self, artist_key: str):
        meta = os.path.join(METADATA_DIR, f"{artist_key}.json")
        if os.path.exists(meta):
            os.remove(meta)
        for prefix in [f"{artist_key}_thumb", f"{artist_key}_banner",
                        f"{artist_key}_logo"]:
            for ext in (".jpg", ".png"):
                p = os.path.join(IMAGES_DIR, prefix + ext)
                if os.path.exists(p):
                    os.remove(p)
