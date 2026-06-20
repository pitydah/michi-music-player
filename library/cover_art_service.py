"""Cover art service — unified cover art finding and quality labeling."""
import os

from library.album_art import find_cover_in_dir
from audio.audio_chain import get_quality_label


class CoverArtService:
    @staticmethod
    def find_cover(filepath: str) -> str:
        """Find cover art for a given filepath. Returns path or empty string."""
        if not filepath:
            return ""
        try:
            d = os.path.dirname(filepath)
            cover = find_cover_in_dir(d)
            return cover or ""
        except Exception:
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
