"""SongsStatusService — calculates visual status badges per song.

Reuses Audio Lab diagnostics_service for quality badges.
No UI dependency.
"""

from __future__ import annotations

from library.media_item import MediaItem


class SongsStatusService:
    """Computes quality badges and status flags for each song.

    Badges are lightweight (no heavy analysis).
    """

    def __init__(self, db=None):
        self._db = db
        self._fav_ids: set[int] = set()
        self._quality_cache: dict[int, dict] = {}

    def set_favorites(self, fav_ids: set[int]):
        self._fav_ids = set(fav_ids)

    def refresh_favorites(self):
        """Sync favorite set from DB."""
        if not self._db:
            return
        try:
            favs = self._db.get_favorites()
            self._fav_ids = set(getattr(f, 'id', 0) for f in favs)
        except Exception:
            self._fav_ids = set()

    def compute_status(self, item: MediaItem) -> dict:
        """Return a dict with status info for a single item.

        Returns:
            {
                "quality_label": str,  # e.g. "Hi-Res 96kHz", "Lossless FLAC"
                "badges": list[str],   # e.g. ["♥", "Hi-Res", "Metadata"]
                "is_favorite": bool,
                "quality_category": str,  # "hires", "lossless", "lossy", "dsd", "unknown"
            }
        """
        item_id = getattr(item, 'id', 0)
        cached = self._quality_cache.get(item_id)
        if cached:
            result = dict(cached)
            result["is_favorite"] = item_id in self._fav_ids
            return result

        badges = []
        quality_label = ""
        quality_category = "unknown"

        # Check favorite
        is_fav = item_id in self._fav_ids

        # Determine quality from metadata
        sr = item.sample_rate or 0
        bd = item.bit_depth or 0
        ext = (item.ext or "").lower()

        lossless_exts = {"flac", "alac", "wav", "aiff", "ape", "wv"}
        lossy_exts = {"mp3", "aac", "ogg", "wma", "opus", "m4a"}
        dsd_exts = {"dsf", "dff", "dsd"}

        if ext in dsd_exts:
            quality_category = "dsd"
            quality_label = "DSD"
            badges.append("DSD")
        elif ext in lossless_exts:
            if sr >= 96000 and bd >= 24:
                quality_category = "hires"
                quality_label = f"Hi-Res {sr // 1000}kHz"
                badges.append("Hi-Res")
            else:
                quality_category = "lossless"
                quality_label = "Lossless"
                badges.append("Lossless")
        elif ext in lossy_exts:
            quality_category = "lossy"
            br = item.bitrate or 0
            quality_label = f"{br // 1000}k" if br else "Lossy"
            badges.append("Lossy")
        else:
            quality_category = "unknown"
            quality_label = ext.upper() if ext else "?"

        # Metadata completeness
        missing = []
        if not item.title:
            missing.append("título")
        if not item.artist:
            missing.append("artista")
        if not item.album:
            missing.append("álbum")
        if not item.genre:
            missing.append("género")
        if missing:
            badges.append(f"Sin {', '.join(missing)}")

        # Audio Lab diagnostic enrichment
        if item.filepath:
            diag_badge = self._get_diag_badge(item.filepath)
            if diag_badge:
                d_label = diag_badge.get("label", "")
                d_kind = diag_badge.get("kind", "")
                if d_kind in ("hires", "lossless", "dsd") and d_label:
                    quality_label = d_label
                    quality_category = d_kind
                if d_kind == "warning":
                    badges.append(d_label)

        # Cover check
        if not self._has_cover(item):
            badges.append("Sin carátula")

        result = {
            "quality_label": quality_label,
            "quality_category": quality_category,
            "badges": badges,
            "is_favorite": is_fav,
        }
        self._quality_cache[item_id] = result
        return result

    def compute_batch(self, items: list[MediaItem]) -> dict[int, dict]:
        """Compute status for a batch of items, returning {item_id: status_dict}."""
        result = {}
        for item in items:
            st = self.compute_status(item)
            iid = getattr(item, 'id', 0)
            result[iid] = st
        return result

    @staticmethod
    def _get_diag_badge(filepath: str) -> dict | None:
        try:
            from ui.audio_lab.diagnostics_service import get_badge_for_file
            return get_badge_for_file(filepath)
        except Exception:
            return None

    @staticmethod
    def _has_cover(item: MediaItem) -> bool:
        if not item.filepath:
            return False
        try:
            from library.cover_art_service import CoverArtService
            return CoverArtService.find_cover(item.filepath) is not None
        except Exception:
            return False
