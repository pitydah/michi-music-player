"""Cover art service — unified cover art finding and quality labeling."""
from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from audio.audio_chain import get_quality_label
from library.artwork_cache import cache_cover, get_cached

logger = logging.getLogger("michi.cover_art")

_MAX_COVER_BYTES = 10 * 1024 * 1024

COVER_FILENAMES = [
    "cover.jpg", "cover.png", "folder.jpg", "folder.png",
    "front.jpg", "front.png", "albumart.jpg", "albumart.png",
    "AlbumArt.jpg", "AlbumArt.png", "album.jpg", "album.png",
]


@lru_cache(maxsize=512)
def _find_cover_cached(directory: str) -> str:
    return find_cover_in_dir(directory)


def find_cover_in_dir(directory: str) -> str | None:
    for name in COVER_FILENAMES:
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            return path
    if os.path.isdir(directory):
        for f in sorted(os.listdir(directory)):
            low = f.lower()
            if low.endswith((".jpg", ".jpeg", ".png")) and any(
                x in low for x in ("cover", "folder", "front", "album", "art", "portada")):
                return os.path.join(directory, f)
    return None


def _get_album_tag(filepath: str) -> str:
    try:
        import mutagen
        f = mutagen.File(filepath)
        if f is None:
            return ""
        tags = getattr(f, 'tags', None)
        if tags is None:
            return ""
        for key in ("album", "TALB", "\xa9alb", "©alb", "ALBUM"):
            val = tags.get(key)
            if val:
                return str(val[0] if isinstance(val, list) else val)
    except Exception:
        pass
    return ""


def _get_embedded_cover(album_name: str, artist: str = "",
                         albumartist: str = "", db=None):
    if not album_name:
        return None
    try:
        from library.album_key import make_album_key
        album_hash = make_album_key(albumartist or "", artist or "", album_name)
    except Exception:
        import hashlib as _hashlib
        album_hash = _hashlib.md5(album_name.encode()).hexdigest()
    row = None
    try:
        if db is not None:
            row = db.get_album_art_cache(album_hash)
        else:
            from core.paths import database_path
            import sqlite3
            conn = sqlite3.connect(database_path())
            row = conn.execute(
                "SELECT mime, data FROM album_art_cache WHERE album_hash=?",
                (album_hash,)).fetchone()
            conn.close()
    except Exception:
        logger.debug("Album art: embedded cover extraction failed")
    if row:
        pix = QPixmap()
        pix.loadFromData(row[1] if isinstance(row, tuple) else row["data"])
        if not pix.isNull():
            return pix
    return None


def _extract_embedded_cover_from_file(filepath: str, size: int = 280):
    try:
        import mutagen
        f = mutagen.File(filepath)
        if f is None:
            return None
        ext = os.path.splitext(filepath)[1].lower()
        data = None
        if ext == ".mp3" and hasattr(f, 'tags') and f.tags:
            for k in f.tags:
                if k.startswith("APIC:"):
                    data = f.tags[k].data
                    break
        if not data and hasattr(f, 'pictures') and f.pictures:
            data = f.pictures[0].data
        if not data and hasattr(f, 'tags') and f.tags:
            covr = f.tags.get("covr")
            if covr:
                data = bytes(covr[0])
        if data:
            if len(data) > _MAX_COVER_BYTES:
                return None
            pix = QPixmap()
            if pix.loadFromData(data):
                return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        pass
    return None


def _load_cover_pixmap(filepath: str, size: int = 280,
                       album: str = "", artist: str = "",
                       albumartist: str = ""):
    directory = os.path.dirname(filepath)
    album_name = album or _get_album_tag(filepath)

    if size <= 96:
        size_name = "thumb"
    elif size <= 260:
        size_name = "medium"
    else:
        size_name = "large"

    if album_name:
        embedded = _get_embedded_cover(album_name, artist=artist, albumartist=albumartist)
        if embedded:
            return embedded.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    cover_path = _find_cover_cached(directory)
    if cover_path:
        cached = get_cached(cover_path, size_name)
        if cached:
            return cached
        pix = QPixmap(cover_path)
        if not pix.isNull():
            try:
                if os.path.getsize(cover_path) > _MAX_COVER_BYTES:
                    logger.debug("Skipping oversized cover: %s (%d bytes)", cover_path, os.path.getsize(cover_path))
                    from library.album_cover_service import make_default_cover
                    return make_default_cover(os.path.basename(directory), size)
            except OSError:
                pass
            scaled = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            cache_cover(cover_path, pix, size_name)
            return scaled

    embedded_pix = _extract_embedded_cover_from_file(filepath, size)
    if embedded_pix:
        return embedded_pix

    from library.album_cover_service import make_default_cover
    return make_default_cover(os.path.basename(directory), size)


def _covers_cache_dir() -> str:
    from core.paths import covers_cache_dir
    return covers_cache_dir()


CACHE_DIR = _covers_cache_dir()


class CoverArtService:
    @staticmethod
    def get_cover_pixmap(filepath: str, size: int = 64):
        if not filepath:
            return None
        try:
            pix = _load_cover_pixmap(filepath, size)
            if pix and not pix.isNull():
                return pix
        except Exception:
            pass
        return None

    @staticmethod
    def find_cover(filepath: str) -> str:
        if not filepath:
            return ""
        try:
            d = os.path.dirname(filepath)
            cover = find_cover_in_dir(d)
            if cover:
                return cover

            pix = _extract_embedded_cover_from_file(filepath, 512)
            if pix and not pix.isNull():
                os.makedirs(CACHE_DIR, exist_ok=True)
                key = hashlib.sha256(filepath.encode()).hexdigest()[:32]
                cache_path = os.path.join(CACHE_DIR, f"{key}_embedded.png")
                pix.save(cache_path, "PNG")
                return cache_path
            return ""
        except Exception:
            logger.debug("find_cover failed for %s", filepath, exc_info=True)
            return ""

    @staticmethod
    def quality_label(filepath: str) -> tuple[str, str]:
        if not filepath:
            return "", ""
        try:
            return get_quality_label(filepath)
        except Exception:
            return "", ""
