"""Simple palette extraction from cover art using Pillow.

Fallback accent: #8FB7FF (Michi accent blue).
"""

from __future__ import annotations

import functools
import logging

from PySide6.QtGui import QPixmap, QColor

logger = logging.getLogger("michi.palette")


@functools.lru_cache(maxsize=32)
def extract_accent(pixmap: QPixmap) -> QColor:
    if pixmap.isNull():
        return QColor("#8FB7FF")
    try:
        from PIL import Image

        img = pixmap.toImage()
        buffer = img.bits().tobytes()
        pil = Image.frombytes("RGBA", (img.width(), img.height()), buffer)
        small = pil.resize((48, 48), Image.LANCZOS)
        colors = small.getcolors(maxcolors=2304)
        if not colors:
            return QColor("#8FB7FF")
        dominant = max(colors, key=lambda c: c[0])[1]
        r, g, b = dominant[:3]
        return QColor(r, g, b)
    except Exception:
        logger.debug("Palette extraction fallback to accent blue")
        return QColor("#8FB7FF")
