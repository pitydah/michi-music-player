#!/usr/bin/python3
"""Normalize sidebar SVGs: crop viewBox to visible content, set to 24x24.

Strategy: render SVG at its original viewBox size, find bounding box of
non-transparent pixels, rewrite viewBox to tightly frame the content.
Then set width/height to 24 (preserving the new tight viewBox).
"""

import sys
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


SRC_DIR = Path("/home/cristian/Descargas/sidebar outpaint")
BACKUP_DIR = SRC_DIR / "backup_v2"
SVG_NS = "http://www.w3.org/2000/svg"


def find_content_bounds(svg_path: str) -> tuple[int, int, int, int] | None:
    """Render SVG and find bounding box of non-transparent pixels."""
    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        return None

    vb = renderer.viewBoxF()
    if vb.isEmpty():
        vb = QRectF(0, 0, 24, 24)

    # Render at original viewBox size for precision
    w = int(vb.width())
    h = int(vb.height())

    # Cap resolution for performance
    max_dim = 800
    if w > max_dim or h > max_dim:
        scale = max_dim / max(w, h)
        w = int(w * scale)
        h = int(h * scale)

    image = QImage(w, h, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()

    # Find non-transparent bounds
    min_x = w
    min_y = h
    max_x = 0
    max_y = 0

    for y in range(h):
        for x in range(w):
            color = QColor.fromRgba(image.pixel(x, y))
            if color.alpha() > 10:  # consider visible
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y

    if min_x > max_x or min_y > max_y:
        return None  # nothing visible

    # Map back to original viewBox coordinates
    scale_x = vb.width() / w
    scale_y = vb.height() / h
    return (
        int(vb.x() + min_x * scale_x),
        int(vb.y() + min_y * scale_y),
        int((max_x - min_x + 1) * scale_x),
        int((max_y - min_y + 1) * scale_y),
    )


def set_viewbox(path: Path, x: int, y: int, w: int, h: int):
    """Rewrite SVG with new viewBox and 24x24 size."""
    text = path.read_text(encoding="utf-8")

    # Preserve the original viewBox XML attribute for replacement
    import re

    text = re.sub(
        r'width="[^"]*"',
        'width="24"',
        text,
    )
    text = re.sub(
        r'height="[^"]*"',
        'height="24"',
        text,
    )
    text = re.sub(
        r'viewBox="[^"]*"',
        f'viewBox="{x} {y} {w} {h}"',
        text,
    )

    path.write_text(text, encoding="utf-8")


def main():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    if not SRC_DIR.exists():
        raise SystemExit(f"No existe: {SRC_DIR}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    svgs = sorted(p for p in SRC_DIR.glob("*.svg") if p.is_file())
    if not svgs:
        raise SystemExit("No SVGs found")

    for svg in svgs:
        backup = BACKUP_DIR / svg.name
        if not backup.exists():
            shutil.copy2(svg, backup)

        try:
            bounds = find_content_bounds(str(svg))
        except Exception as e:
            print(f"  SKIP {svg.name}: render error: {e}")
            continue

        if bounds is None:
            print(f"  SKIP {svg.name}: no visible content found")
            continue

        x, y, w, h = bounds
        print(f"  {svg.name}: viewBox {x} {y} {w} {h} (was: check SVG)")

        set_viewbox(svg, x, y, w, h)

    app.quit()


if __name__ == "__main__":
    main()
