"""Cover art service — unified cover art finding and quality labeling."""
from __future__ import annotations

import os
import hashlib

from library.album_art import find_cover_in_dir
from audio.audio_chain import get_quality_label

CACHE_DIR = os.path.expanduser("~/.cache/astra/covers")


class CoverArtService:
    @staticmethod
    def get_cover_pixmap(filepath: str, size: int = 64):
        """Resolve cover art for a given audio file, returning a QPixmap or None."""
        if not filepath:
            return None
        try:
            # Use the full load_cover_pixmap which tries: DB cache → external → mutagen
            from library.album_art import load_cover_pixmap
            pix = load_cover_pixmap(filepath, size)
            if pix and not pix.isNull():
                return pix
        except Exception:
            pass
        return None

    @staticmethod
    def find_cover(filepath: str) -> str:
        """Find cover art for a given filepath. Returns path or empty string."""
        if not filepath:
            return ""
        try:
            d = os.path.dirname(filepath)
            cover = find_cover_in_dir(d)
            if cover:
                return cover

            # Fallback: extract embedded cover from the audio file
            from library.album_art import _extract_embedded_cover_from_file
            pix = _extract_embedded_cover_from_file(filepath, 512)
            if pix and not pix.isNull():
                os.makedirs(CACHE_DIR, exist_ok=True)
                key = hashlib.sha256(filepath.encode()).hexdigest()[:32]
                cache_path = os.path.join(CACHE_DIR, f"{key}_embedded.png")
                pix.save(cache_path, "PNG")
                return cache_path
            return ""
        except Exception:
            import logging
            logging.getLogger("astra").debug(
                "find_cover failed for %s", filepath, exc_info=True)
            return ""

    @staticmethod
    def quality_label(filepath: str) -> tuple[str, str]:
        """Get quality label for a filepath. Returns (label, label_with_detail)."""
        if not filepath:
            return "", ""
        try:
            return get_quality_label(filepath)
        except Exception:
            return "", ""
