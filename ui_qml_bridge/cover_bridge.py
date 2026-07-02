"""CoverBridge — QQuickPaintedItem that renders cover art in QML.

Usage in QML:
    import MichiCover 1.0
    CoverBridge { coverKey: "album_xyz"; width: 180; height: 180 }

Caches:
    _FALLBACK_CACHE: max 256 entries, LRU-eviction via clear()
    _COVER_CACHE: max 256 entries, LRU-eviction via clear()

Rules:
    - paint() draws cached pixmap or fallback only — NO heavy work
    - Heavy work (DB read, image decode, scale) happens ONCE in coverKey setter
    - Result is cached in self._pixmap; paint() never touches DB nor decodes
    - Fallback is always available, no crash path
    - DB connection is temporary, closed immediately
"""

from PySide6.QtQuick import QQuickPaintedItem
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QLinearGradient, QPixmap, Qt
from PySide6.QtCore import Property, Signal, QByteArray
from pathlib import Path
import logging

logger = logging.getLogger("michi.cover")

_FALLBACK_CACHE: dict[str, QPixmap] = {}
_COVER_CACHE: dict[str, QImage] = {}
_MAX_CACHE = 256
_DB_PATH = None


def _get_db_path() -> Path:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = Path.home() / ".local" / "share" / "michi-music-player" / "library.db"
    return _DB_PATH


def _trim_cache(cache: dict, max_size: int = _MAX_CACHE):
    if len(cache) > max_size:
        keys = list(cache.keys())
        for k in keys[: len(keys) - max_size]:
            del cache[k]


def _make_fallback_pixmap(seed: str, size: int) -> QPixmap:
    key = f"fallback_{seed}_{size}"
    if key in _FALLBACK_CACHE:
        return _FALLBACK_CACHE[key]

    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(0x0D0F16)

    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor(0x0A, 0x0D, 0x14))
    gradient.setColorAt(1.0, QColor(0x11, 0x13, 0x1C))
    p.fillRect(img.rect(), gradient)
    p.setPen(QColor(0x8F, 0xB7, 0xFF))
    p.setFont(QFont("sans-serif", size // 4, QFont.Bold))
    glyph = seed[:2].upper() if seed else "MM"
    p.drawText(img.rect(), int(Qt.AlignCenter), glyph)
    p.end()

    pm = QPixmap.fromImage(img)
    _FALLBACK_CACHE[key] = pm
    _trim_cache(_FALLBACK_CACHE)
    return pm


def _load_cover_image(album_key: str, size: int) -> QImage | None:
    if album_key in _COVER_CACHE:
        cached = _COVER_CACHE[album_key]
        if cached.width() != size:
            return cached.scaled(size, size,
                                 Qt.KeepAspectRatio,
                                 Qt.SmoothTransformation)
        return cached

    db_path = _get_db_path()
    if not db_path.exists():
        return None

    try:
        from library.library_db import LibraryDB
        db = LibraryDB(str(db_path))
        try:
            row = db.get_album_art_cache(album_key)
            if row:
                _mime, data = row
                img = QImage()
                if img.loadFromData(QByteArray(data)):
                    scaled = img.scaled(size, size,
                                        Qt.KeepAspectRatio,
                                        Qt.SmoothTransformation)
                    _COVER_CACHE[album_key] = scaled
                    _trim_cache(_COVER_CACHE)
                    return scaled
        finally:
            from contextlib import suppress
            with suppress(Exception):
                db.close()
    except Exception:
        logger.debug("Cover load failed for %s", album_key, exc_info=True)

    return None


class CoverBridge(QQuickPaintedItem):
    coverChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cover_key = ""
        self._pixmap = None

    @Property(str, notify=coverChanged)
    def coverKey(self):
        return self._cover_key

    @coverKey.setter
    def coverKey(self, key: str):
        if key == self._cover_key:
            return
        self._cover_key = key
        self._pixmap = None
        size = max(int(self.width()) or 180, int(self.height()) or 180)
        if key:
            img = _load_cover_image(key, size)
            if img:
                self._pixmap = QPixmap.fromImage(img)
        self.coverChanged.emit()
        self.update()

    def paint(self, painter: QPainter):
        w = int(self.width())
        h = int(self.height())
        if w < 1 or h < 1:
            return

        if self._pixmap:
            painter.drawPixmap(0, 0, w, h, self._pixmap)
        else:
            key = self._cover_key or "COVER"
            fallback = _make_fallback_pixmap(key, max(w, h))
            painter.drawPixmap(0, 0, w, h, fallback)
