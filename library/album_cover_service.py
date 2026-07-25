"""AlbumCoverService — unified cover art resolution for albums.

Order of resolution:
  1. External file in album folder (cover.jpg, folder.jpg, etc.)
  2. Embedded extraction via cover_art_service
  3. Michi fallback (make_default_cover)
All keys use make_album_key from library.album_key for consistency with grid, detail, CoverFlow, and API.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPixmap, QColor, QPainter, QFont, QPen, QPainterPath

logger = logging.getLogger("michi.album_cover")

COVER_FILENAMES = [
    "cover.jpg", "cover.png", "folder.jpg", "folder.png",
    "front.jpg", "front.png", "albumart.jpg", "albumart.png",
    "AlbumArt.jpg", "AlbumArt.png", "album.jpg", "album.png",
]


@dataclass
class AlbumCoverResult:
    pixmap: Any = None
    path: str = ""
    source: str = "fallback"
    missing: bool = False
    error: str = ""


def _find_local_cover(dirpath: str) -> str | None:
    if not dirpath or not os.path.isdir(dirpath):
        return None
    for name in COVER_FILENAMES:
        path = os.path.join(dirpath, name)
        if os.path.isfile(path):
            return path
    for f in sorted(os.listdir(dirpath)):
        low = f.lower()
        if low.endswith((".jpg", ".jpeg", ".png")) and any(
            x in low for x in ("cover", "folder", "front", "album", "art", "portada")):
            return os.path.join(dirpath, f)
    return None


def make_default_cover(title: str = "", size: int = 280) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(QColor("#090B11"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    pen_border = QPen(QColor(255, 255, 255, 30), 1)
    painter.setPen(pen_border)
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 14, 14)

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


def group_by_album(items: list) -> list[tuple[str, str, list]]:
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
    result = [(album, artist, tracks) for (album, artist), tracks in groups.items()]
    result.sort(key=lambda x: x[0].lower())
    return result


class AlbumCoverService:
    def resolve_cover(self, tracks: list, size: int = 280) -> AlbumCoverResult:
        # 1. External file in first track's folder
        for t in tracks:
            fp = str(getattr(t, "filepath", "") or "")
            if fp:
                cover_path = _find_local_cover(os.path.dirname(fp))
                if cover_path:
                    pix = QPixmap(cover_path)
                    if not pix.isNull():
                        return AlbumCoverResult(
                            pixmap=pix, path=cover_path, source="external_file",
                        )

        # 2. Embedded from first valid file
        for t in tracks:
            fp = str(getattr(t, "filepath", "") or "")
            if fp and os.path.isfile(fp):
                try:
                    from library.cover_art_service import _extract_embedded_cover_from_file
                    pix = _extract_embedded_cover_from_file(fp)
                    if pix and not pix.isNull():
                        return AlbumCoverResult(pixmap=pix, source="embedded_file")
                except Exception:
                    continue

        # 3. Fallback
        fallback = make_default_cover(
            str(getattr(tracks[0], "album", "") if tracks else ""), size)
        return AlbumCoverResult(pixmap=fallback, source="fallback")

    def make_fallback_cover(self, title: str = "", artist: str = "",
                            size: int = 280):
        return make_default_cover(title, size)
