"""Album cover art — extraction and album grouping for CoverFlow."""

import os
import sqlite3
from functools import lru_cache
from dataclasses import dataclass
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

from library.artwork_cache import get_cached, cache_cover

_MAX_COVER_BYTES = 10 * 1024 * 1024  # 10 MB limit for embedded/external covers


@lru_cache(maxsize=512)
def _find_cover_cached(directory: str) -> str:
    """Cached wrapper for find_cover_in_dir."""
    return find_cover_in_dir(directory)

COVER_FILENAMES = ["cover.jpg", "cover.png", "folder.jpg", "folder.png",
                   "front.jpg", "front.png", "albumart.jpg", "albumart.png",
                   "AlbumArt.jpg", "AlbumArt.png", "album.jpg", "album.png"]


@dataclass
class _CoverFlowItem:
    pixmap: QPixmap
    title: str
    subtitle: str
    data: any = None
CoverFlowItem = _CoverFlowItem  # used by CoverFlow module


def find_cover_in_dir(directory: str) -> str | None:
    for name in COVER_FILENAMES:
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            return path
    # Also check for any jpg/png matching album name pattern
    if os.path.isdir(directory):
        for f in sorted(os.listdir(directory)):
            low = f.lower()
            if low.endswith((".jpg", ".jpeg", ".png")) and any(
                x in low for x in ("cover", "folder", "front", "album", "art", "portada")):
                return os.path.join(directory, f)
    return None


def make_default_cover(title: str = "", size: int = 280) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(QColor("#090B11"))  # Michi dark background
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    # Subtle border
    pen_border = QPen(QColor(255, 255, 255, 30), 1)
    painter.setPen(pen_border)
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 14, 14)

    # Note icon centered
    cx, cy = size / 2 - 10, size / 2 + 5
    r = min(size / 8, 20)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(143, 183, 255, 80))
    painter.drawEllipse(QPointF(cx, cy), r, r)

    pen = QPen(QColor(143, 183, 255, 120), max(2, int(size / 60)))
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(cx + r, cy), QPointF(cx + r, cy - r * 2.5))

    path = QPainterPath()
    path.moveTo(cx + r, cy - r * 2.5)
    path.cubicTo(cx + r + r * 1.2, cy - r * 2.2, cx + r + r * 1.5, cy - r * 1.5,
                 cx + r + r * 0.5, cy - r * 0.8)
    painter.setBrush(QColor(143, 183, 255, 120))
    painter.setPen(Qt.NoPen)
    painter.drawPath(path)

    if title:
        painter.setPen(QColor(255, 255, 255, 90))
        painter.setFont(QFont("sans-serif", max(8, int(size / 24))))
        painter.drawText(QRectF(12, size - 30, size - 24, 26),
                        Qt.AlignCenter | Qt.TextWordWrap, title[:40])

    painter.end()
    return pix


def _get_embedded_cover(album_name: str, artist: str = "",
                         albumartist: str = "", db=None) -> QPixmap | None:
    if not album_name:
        return None
    try:
        from library.album_key import make_album_key
        album_hash = make_album_key(albumartist or "", artist or "", album_name)
    except Exception:
        import hashlib
        album_hash = hashlib.md5(album_name.encode()).hexdigest()
    row = None
    try:
        if db is not None:
            row = db.get_album_art_cache(album_hash)
        else:
            from core.paths import database_path
            conn = sqlite3.connect(database_path())
            row = conn.execute(
                "SELECT mime, data FROM album_art_cache WHERE album_hash=?",
                (album_hash,)).fetchone()
            conn.close()
    except Exception:
        import logging
        logging.getLogger("michi").debug("Album art: embedded cover extraction failed")
    if row:
        pix = QPixmap()
        pix.loadFromData(row[1] if isinstance(row, tuple) else row["data"])
        if not pix.isNull():
            return pix
    return None


def load_cover_pixmap(filepath: str, size: int = 280,
                      album: str = "", artist: str = "",
                      albumartist: str = "") -> QPixmap:
    """Try to find and load cover art for a media file. Returns QPixmap."""
    directory = os.path.dirname(filepath)

    if size <= 96:
        size_name = "thumb"
    elif size <= 260:
        size_name = "medium"
    else:
        size_name = "large"

    # 1. Try embedded cover from DB cache (keyed by album tag)
    # Use passed album if available — avoid unnecessary mutagen call
    album_name = album or _get_album_tag(filepath)
    if album_name:
        embedded = _get_embedded_cover(album_name, artist=artist, albumartist=albumartist)
        if embedded:
            return embedded.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # 2. Try external cover files
    cover_path = _find_cover_cached(directory)
    if cover_path:
        cached = get_cached(cover_path, size_name)
        if cached:
            return cached
        pix = QPixmap(cover_path)
        if not pix.isNull():
            # Check file size to avoid huge covers
            try:
                if os.path.getsize(cover_path) > _MAX_COVER_BYTES:
                    logger = __import__('logging').getLogger('michi.artwork')
                    logger.debug("Skipping oversized cover: %s (%d bytes)", cover_path, os.path.getsize(cover_path))
                    return make_default_cover(os.path.basename(directory), size)
            except OSError:
                pass
            scaled = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            cache_cover(cover_path, pix, size_name)
            return scaled

    # 3. Fallback: extract embedded cover directly from the audio file via mutagen
    embedded_pix = _extract_embedded_cover_from_file(filepath, size)
    if embedded_pix:
        return embedded_pix

    title = os.path.basename(directory)
    return make_default_cover(title, size)


def _get_album_tag(filepath: str) -> str:
    """Read the album tag from an audio file quickly."""
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


def _extract_embedded_cover_from_file(filepath: str, size: int = 280) -> QPixmap | None:
    """Try to read embedded cover art directly from the audio file using mutagen."""
    try:
        import mutagen

        f = mutagen.File(filepath)
        if f is None:
            return None

        ext = os.path.splitext(filepath)[1].lower()
        data = None

        # MP3 — ID3 APIC
        if ext == ".mp3" and hasattr(f, 'tags') and f.tags:
            for k in f.tags:
                if k.startswith("APIC:"):
                    data = f.tags[k].data
                    break

        # FLAC — pictures
        if not data and hasattr(f, 'pictures') and f.pictures:
            data = f.pictures[0].data

        # MP4/M4A — covr
        if not data and hasattr(f, 'tags') and f.tags:
            covr = f.tags.get("covr")
            if covr:
                data = bytes(covr[0])

        if data:
            if len(data) > _MAX_COVER_BYTES:
                return None  # skip oversized embedded covers
            pix = QPixmap()
            if pix.loadFromData(data):
                return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        pass
    return None


def group_by_album(items: list) -> list[tuple[str, str, list]]:
    """Group media items by (album, artist). Returns sorted list of groups.
    Accepts MediaItem (has .album/.artist) or CoverFlowItem (has .title/.subtitle)."""
    groups: dict[tuple[str, str], list] = {}

    for item in items:
        if hasattr(item, 'album'):
            album = item.album or "Sin álbum"
            artist = item.artist or "Artista desconocido"
        else:
            album = getattr(item, 'title', '') or "Sin álbum"
            artist = getattr(item, 'subtitle', '').split('·')[0].strip() or "Artista desconocido"
        key = (album, artist)
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    # Sort by album name
    result = [(album, artist, tracks) for (album, artist), tracks in groups.items()]
    result.sort(key=lambda x: x[0].lower())
    return result


# Legacy stub — migrated to CoverBridge
def load_covers_for_albums(items: list, size: int = 260, lazy: bool = False) -> list:
    return []



