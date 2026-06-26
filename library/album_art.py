"""Album cover art — extraction and album grouping for CoverFlow."""

import os
import sqlite3
from functools import lru_cache
from dataclasses import dataclass
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

from library.library_db import MediaItem
from library.artwork_cache import get_cached, cache_cover


@lru_cache(maxsize=512)
def _find_cover_cached(directory: str) -> str:
    """Cached wrapper for find_cover_in_dir."""
    return find_cover_in_dir(directory)

COVER_FILENAMES = ["cover.jpg", "cover.png", "folder.jpg", "folder.png",
                   "front.jpg", "front.png", "albumart.jpg", "albumart.png",
                   "AlbumArt.jpg", "AlbumArt.png", "album.jpg", "album.png"]


@dataclass
class CoverFlowItem:
    pixmap: QPixmap
    title: str
    subtitle: str
    data: any = None  # album group info


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
    pix.fill(QColor("#e5e5ea"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    # Circle (note head)
    cx, cy = size / 2 - 20, size / 2 + 10
    r = min(size / 8, 20)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#8FB7FF"))
    painter.drawEllipse(QPointF(cx, cy), r, r)

    # Stem
    pen = QPen(QColor("#8FB7FF"), max(2, int(size / 60)))
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(cx + r, cy), QPointF(cx + r, cy - r * 2.5))

    # Flag
    path = QPainterPath()
    path.moveTo(cx + r, cy - r * 2.5)
    path.cubicTo(cx + r + r * 1.2, cy - r * 2.2, cx + r + r * 1.5, cy - r * 1.5,
                 cx + r + r * 0.5, cy - r * 0.8)
    painter.setBrush(QColor("#8FB7FF"))
    painter.setPen(Qt.NoPen)
    painter.drawPath(path)

    if title:
        painter.setPen(QColor("#8e8e93"))
        painter.setFont(QFont("sans-serif", max(8, int(size / 24))))
        painter.drawText(QRectF(12, size - 30, size - 24, 26),
                        Qt.AlignCenter | Qt.TextWordWrap, title[:40])

    painter.end()
    return pix


def _get_embedded_cover(album_name: str, artist: str = "", albumartist: str = "") -> QPixmap | None:
    if not album_name:
        return None
    try:
        from library.album_key import make_album_key
        album_hash = make_album_key(albumartist or "", artist or "", album_name)
    except Exception:
        import hashlib
        album_hash = hashlib.md5(album_name.encode()).hexdigest()
    try:
        from library.library_db import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT mime, data FROM album_art_cache WHERE album_hash=?",
            (album_hash,)).fetchone()
        conn.close()
        if row:
            pix = QPixmap()
            pix.loadFromData(row[1])
            if not pix.isNull():
                return pix
    except Exception:
        import logging
        logging.getLogger("michi").debug("Album art: embedded cover extraction failed")
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
    album_name = _get_album_tag(filepath)
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
            pix = QPixmap()
            if pix.loadFromData(data):
                return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception:
        pass
    return None


def group_by_album(items: list[MediaItem]) -> list[tuple[str, str, list[MediaItem]]]:
    """Group media items by (album, artist). Returns sorted list of groups."""
    groups: dict[tuple[str, str], list[MediaItem]] = {}

    for item in items:
        key = (item.album or "Sin álbum", item.artist or "Artista desconocido")
        if key not in groups:
            groups[key] = []
        groups[key].append(item)

    # Sort by album name
    result = [(album, artist, tracks) for (album, artist), tracks in groups.items()]
    result.sort(key=lambda x: x[0].lower())
    return result


def load_covers_for_albums(items: list[MediaItem],
                            size: int = 260,
                            lazy: bool = False) -> list[CoverFlowItem]:
    """Create CoverFlowItems grouped by album with cover art."""
    groups = group_by_album(items)
    covers = []

    for album, artist, tracks in groups:
        first = tracks[0]
        pix = None if lazy else load_cover_pixmap(
            first.filepath, size,
            album=album, artist=artist,
            albumartist=getattr(first, "albumartist", "") or artist)

        subtitle_parts = [artist]
        year = first.year
        if year:
            subtitle_parts.append(str(year))
        subtitle_parts.append(f"{len(tracks)} ♪")

        covers.append(CoverFlowItem(
            pixmap=pix,
            title=album,
            subtitle=" · ".join(subtitle_parts),
            data={"album": album, "artist": artist, "tracks": tracks},
        ))

    return covers
