"""Playlist cover service — mosaic generation, custom covers, fallback."""
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QLinearGradient

COVER_DIR = os.path.expanduser("~/.local/share/astra-music-player/playlist-covers/")


def _ensure_dir():
    os.makedirs(COVER_DIR, exist_ok=True)


def get_playlist_cover(playlist: dict, tracks: list) -> QPixmap | None:
    """Get the best available cover for a playlist."""
    cover_path = playlist.get("cover_path", "")
    cover_type = playlist.get("cover_type", "mosaic")

    if cover_type == "custom" and cover_path and os.path.isfile(cover_path):
        pix = QPixmap(cover_path)
        if not pix.isNull():
            return pix

    if cover_type in ("mosaic", "none", "") and tracks:
        return generate_mosaic(tracks, 180)

    return generate_fallback_cover(playlist.get("name", "Playlist"), 180)


def copy_custom_cover(playlist_id: int, image_path: str) -> str:
    """Copy an image to the playlist covers directory. Returns the new path."""
    _ensure_dir()
    ext = os.path.splitext(image_path)[1].lower() or ".png"
    dest = os.path.join(COVER_DIR, f"playlist_{playlist_id}{ext}")
    if os.path.isfile(image_path):
        with open(image_path, "rb") as f:
            data = f.read()
        with open(dest, "wb") as f:
            f.write(data)
    return dest


def remove_custom_cover(playlist_id: int):
    """Remove the custom cover for a playlist. Only deletes inside COVER_DIR."""
    import logging
    for ext in (".png", ".jpg", ".jpeg"):
        path = os.path.realpath(os.path.join(COVER_DIR, f"playlist_{playlist_id}{ext}"))
        cover_real = os.path.realpath(COVER_DIR)
        if os.path.isfile(path) and os.path.commonpath([path, cover_real]) == cover_real:
            os.remove(path)
        elif os.path.isfile(path):
            logging.getLogger("astra").warning("remove_custom_cover: path outside COVER_DIR — skipped %s", path)


def generate_mosaic(tracks: list, size: int = 180) -> QPixmap | None:
    """Generate a 2x2 mosaic from up to 4 track covers."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    cell = size // 2 - 3
    covers = []
    for t in tracks[:4]:
        fp = getattr(t, 'filepath', '') if not isinstance(t, str) else t
        if fp:
            from library.album_art import find_cover_in_dir
            cover = find_cover_in_dir(os.path.dirname(fp))
            if cover:
                covers.append(cover)

    for i in range(4):
        x = (i % 2) * (cell + 4) + 2
        y = (i // 2) * (cell + 4) + 2
        if i < len(covers):
            c = QPixmap(covers[i]).scaled(cell, cell, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap(x, y, cell, cell, c)
        else:
            p.fillRect(x, y, cell, cell, QColor(255, 255, 255, 10))
        p.setPen(QPen(QColor(255, 255, 255, 15), 1))
        p.drawRoundedRect(x, y, cell, cell, 8, 8)

    p.end()
    return pix


def generate_fallback_cover(name: str, size: int = 180) -> QPixmap:
    """Generate a gradient cover with playlist name."""
    pix = QPixmap(size, size)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor(45, 42, 60))
    grad.setColorAt(0.5, QColor(35, 32, 48))
    grad.setColorAt(1, QColor(28, 25, 40))
    p.fillRect(0, 0, size, size, grad)

    p.setPen(QPen(QColor(255, 255, 255, 18), 1))
    p.drawRoundedRect(2, 2, size - 4, size - 4, 16, 16)

    font = QFont("sans-serif", max(11, size // 14), 600)
    p.setFont(font)
    p.setPen(QColor(255, 255, 255, 80))
    display = name[:14] + "…" if len(name) > 14 else name
    p.drawText(8, 8, size - 16, size - 16, Qt.AlignCenter | Qt.TextWordWrap, display)

    p.end()
    return pix
