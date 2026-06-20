"""Artwork Cache — disk-based scaled cover art cache.

Sizes: thumb (96), medium (260), large (512).
Key: SHA256(filepath + mtime + size).
Cache dir: ~/.cache/astra/covers/
"""

import hashlib
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


CACHE_DIR = os.path.expanduser("~/.cache/astra/covers")
SIZES = {"thumb": 96, "medium": 260, "large": 512}


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(filepath: str) -> str:
    try:
        st = os.stat(filepath)
        raw = f"{filepath}|{st.st_mtime}|{st.st_size}".encode()
    except OSError:
        raw = filepath.encode()
    return hashlib.sha256(raw).hexdigest()[:32]


def _cache_path(filepath: str, size_name: str) -> str:
    key = _cache_key(filepath)
    return os.path.join(CACHE_DIR, f"{key}_{size_name}.png")


def get_cached(filepath: str, size_name: str = "medium") -> QPixmap | None:
    """Return cached scaled pixmap, or None if not found."""
    if size_name not in SIZES:
        return None
    path = _cache_path(filepath, size_name)
    if os.path.exists(path):
        pix = QPixmap(path)
        if not pix.isNull():
            return pix
    return None


def cache_cover(filepath: str, pix: QPixmap, size_name: str = "medium"):
    """Scale and cache a cover pixmap."""
    if size_name not in SIZES:
        return
    target = SIZES[size_name]
    scaled = pix.scaled(
        target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    path = _cache_path(filepath, size_name)
    _ensure_cache_dir()
    scaled.save(path, "PNG")


def cache_origin(filepath: str, pix: QPixmap):
    """Cache original-size cover as large (for expanded view)."""
    cache_cover(filepath, pix, "large")


def invalidate(filepath: str):
    """Remove all cached versions for a filepath."""
    key = _cache_key(filepath)
    for size_name in SIZES:
        path = os.path.join(CACHE_DIR, f"{key}_{size_name}.png")
        if os.path.exists(path):
            os.remove(path)


