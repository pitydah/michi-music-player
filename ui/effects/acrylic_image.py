"""Acrylic pixmap — static blur + tint + noise via Pillow.

Uses Pillow which is already declared in pyproject.toml dependencies.
Cache is mandatory to avoid blocking the UI thread.
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QPixmap, QColor, QPainter, QImage

from ui.effects.texture_cache import texture_cache

logger = logging.getLogger("michi.acrylic")


def make_acrylic_pixmap(
    source: QPixmap,
    blur_radius: int = 8,
    tint_color: str = "#090B11",
    tint_opacity: float = 0.65,
    brightness: float = 0.85,
    width: int = 0,
    height: int = 0,
) -> QPixmap:
    if source.isNull():
        return QPixmap()

    if width <= 0:
        width = source.width()
    if height <= 0:
        height = source.height()

    cache_key = (
        id(source), blur_radius, tint_color, tint_opacity, brightness, width, height
    )
    cached = texture_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from PIL import Image, ImageFilter, ImageEnhance

        img = source.toImage()
        buffer = img.bits().tobytes()
        pil_img = Image.frombytes("RGBA", (img.width(), img.height()), buffer)
        pil_img = pil_img.resize((width, height), Image.LANCZOS)

        if blur_radius > 0:
            pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(brightness)

        tint = QColor(tint_color)
        tint_layer = Image.new("RGBA", pil_img.size, (
            tint.red(), tint.green(), tint.blue(), int(255 * tint_opacity)
        ))
        pil_img = Image.alpha_composite(pil_img, tint_layer)

        mode = pil_img.mode
        data = pil_img.tobytes("raw", mode)
        qimage = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
        result = QPixmap.fromImage(qimage)
    except Exception:
        logger.debug("Pillow acrylic fallback, returning tinted QPixmap")
        result = QPixmap(width, height)
        result.fill(QColor(9, 11, 17))
        p = QPainter(result)
        p.setOpacity(tint_opacity)
        p.drawPixmap(0, 0, source.scaled(width, height))
        p.end()

    texture_cache.put(cache_key, result)
    return result
