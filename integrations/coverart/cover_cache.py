"""CoverCache — download and cache cover art images from Cover Art Archive."""
import os
import time
import logging

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

_COVER_DIR_LEGACY = os.path.expanduser("~/.cache/michi/covers")  # legacy compat


def _default_cover_dir() -> str:
    from core.paths import remote_covers_cache_dir
    return remote_covers_cache_dir()


COVER_DIR = _default_cover_dir()
MAX_SIZE = 8 * 1024 * 1024  # 8 MB
NEGATIVE_TTL = 3600  # 1 hour for negative cache
VALID_MIME = {"image/jpeg", "image/png", "image/webp"}


def _ensure_dir():
    os.makedirs(COVER_DIR, exist_ok=True)


def _safe_filename(album_key: str, mbid: str = "") -> str:
    """Generate a safe filename from album_key + optional MBID."""
    import hashlib
    base = f"{album_key}_{mbid}" if mbid else album_key
    h = hashlib.sha256(base.encode()).hexdigest()[:16]
    return f"{h}.jpg"


class CoverCache(QObject):
    """Downloads cover art, validates content, caches locally with atomic writes."""

    cover_cached = Signal(str, str)       # album_key, local_path
    cache_failed = Signal(str, str)       # album_key, error

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        _ensure_dir()

    def cache_cover(self, album_key: str, image_url: str, mbid: str = ""):
        """Download and cache a cover image. Emits cover_cached or cache_failed."""
        if not image_url:
            return
        fname = _safe_filename(album_key, mbid)
        target = os.path.join(COVER_DIR, fname)

        # Already cached — reuse
        if os.path.exists(target) and os.path.getsize(target) > 0:
            self.cover_cached.emit(album_key, target)
            return

        # Download
        req = QNetworkRequest(QUrl(image_url))
        req.setRawHeader(b"User-Agent",
                         b"MichiMusicPlayer/0.1 (CoverArtArchive)")
        reply = self._nam.get(req)
        reply.finished.connect(
            lambda r=reply, k=album_key, t=target, m=mbid:
            self._on_download(r, k, t, m))

    def get_cached(self, album_key: str, mbid: str = "") -> str | None:
        """Return cached cover path if exists, else None."""
        fname = _safe_filename(album_key, mbid)
        target = os.path.join(COVER_DIR, fname)
        if os.path.exists(target) and os.path.getsize(target) > 0:
            return target
        return None

    def _on_download(self, reply: QNetworkReply, album_key: str,
                     target: str, mbid: str):
        err = reply.error()
        if err != QNetworkReply.NoError:
            self._log_negative(album_key)
            self.cache_failed.emit(album_key, reply.errorString())
            reply.deleteLater()
            return

        content_type = reply.rawHeader(b"Content-Type")
        ct_str = content_type.data().decode("ascii", errors="replace") if content_type else ""
        ct_str = ct_str.split(";")[0].strip().lower()

        if ct_str not in VALID_MIME:
            logging.getLogger("michi.covers").debug(
                "Rejected content-type: %s for %s", ct_str, album_key)
            self._log_negative(album_key)
            self.cache_failed.emit(album_key, f"Invalid content-type: {ct_str}")
            reply.deleteLater()
            return

        data = bytes(reply.readAll())
        if len(data) == 0 or len(data) > MAX_SIZE:
            self.cache_failed.emit(album_key, "Invalid size")
            reply.deleteLater()
            return

        # Atomic write: .tmp → rename
        tmp = target + ".tmp"
        try:
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, target)
            self._clear_negative(album_key)
            self.cover_cached.emit(album_key, target)
        except OSError as e:
            self.cache_failed.emit(album_key, str(e))
        finally:
            reply.deleteLater()

    def _neg_path(self, album_key: str) -> str:
        return os.path.join(COVER_DIR, f".{_safe_filename(album_key)}.neg")

    def _log_negative(self, album_key: str):
        try:
            with open(self._neg_path(album_key), "w") as f:
                f.write(str(int(time.time())))
        except OSError:
            pass

    def _clear_negative(self, album_key: str):
        try:
            p = self._neg_path(album_key)
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass

    def is_negative(self, album_key: str) -> bool:
        """Check if negative cache entry exists and is still valid."""
        p = self._neg_path(album_key)
        if os.path.exists(p):
            try:
                with open(p) as f:
                    t = int(f.read().strip())
                return time.time() - t < NEGATIVE_TTL
            except (ValueError, OSError):
                pass
        return False
