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
        self._fav_track_ids: set[str] = set()
        self._quality_cache: dict[int, dict] = {}
        self._cover_cache: dict[str, bool] = {}
        self._path_to_id: dict[str, int] = {}

    def favorite_track_ids(self) -> set[str]:
        return set(self._fav_track_ids)

    def status_cache(self) -> dict[int, dict]:
        return dict(self._quality_cache)

    def refresh_favorites(self):
        """Sync favorite set from DB. get_favorites() returns list of track_id strings."""
        if not self._db:
            return
        import contextlib
        with contextlib.suppress(Exception):
            favs = self._db.get_favorites()
            self._fav_track_ids = set(str(f) for f in favs)

    def invalidate_cache(self):
        self._quality_cache.clear()
        self._cover_cache.clear()

    def invalidate_cache_for_paths(self, paths: list[str] | None = None):
        """Invalidate quality + cover caches for given paths, or all if None."""
        if paths is None:
            self._quality_cache.clear()
            self._cover_cache.clear()
            self._path_to_id.clear()
            return
        for fp in paths:
            self._cover_cache.pop(fp, None)
            iid = self._path_to_id.pop(fp, None)
            if iid is not None:
                self._quality_cache.pop(iid, None)

    def compute_status(self, item: MediaItem, diag_badge: dict | None = None) -> dict:
        item_id = getattr(item, 'id', 0)
        if item.filepath:
            self._path_to_id[item.filepath] = item_id
        cached = self._quality_cache.get(item_id)
        if cached:
            result = dict(cached)
            result["is_favorite"] = item.filepath in self._fav_track_ids
            return result

        badges = []
        quality_label = ""
        quality_category = "unknown"
        is_fav = item.filepath in self._fav_track_ids
        sr = item.sample_rate or 0
        bd = item.bit_depth or 0
        ext = (item.ext or "").lower().lstrip(".")

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
            d_badge = diag_badge if diag_badge is not None else self._get_diag_badge(item.filepath)
            if d_badge:
                d_label = d_badge.get("label", "")
                d_kind = d_badge.get("kind", "")
                if d_kind in ("hires", "lossless", "dsd") and d_label:
                    quality_label = d_label
                    quality_category = d_kind
                if d_kind == "warning":
                    badges.append(d_label)
                    quality_category = "warning"

        # Spectral warning from media_items column
        spec_verdict = getattr(item, 'spectral_verdict', '') or ''
        if spec_verdict in ("SUSPICIOUS_UPSAMPLING", "POSSIBLE_LOSSY_SOURCE") and "Espectro sospechoso" not in badges:
            badges.append("Espectro sospechoso")
            quality_category = "warning" if quality_category not in ("error",) else quality_category

        # Cover check
        if not self._has_cover(item):
            badges.append("Sin carátula")

        result = {
            "quality_label": quality_label,
            "quality_category": quality_category,
            "badges": badges,
            "is_favorite": is_fav,
            "missing_metadata": len(missing) > 0,
            "has_audio_lab_warning": quality_category == "warning" or spec_verdict in (
                "SUSPICIOUS_UPSAMPLING", "POSSIBLE_LOSSY_SOURCE",
            ),
        }
        self._quality_cache[item_id] = result
        return result

    def compute_batch(self, items: list[MediaItem]) -> dict[int, dict]:
        result = {}
        paths = [i.filepath for i in items if i.filepath]
        badges_by_path = {}
        if paths:
            try:
                from library.audio_lab_badges import get_audio_lab_badges_for_paths
                badges_by_path = get_audio_lab_badges_for_paths(paths)
            except Exception:
                pass
        for item in items:
            st = self.compute_status(item, diag_badge=badges_by_path.get(item.filepath))
            iid = getattr(item, 'id', 0)
            result[iid] = st
        return result

    @staticmethod
    def _get_diag_badge(filepath: str) -> dict | None:
        try:
            from library.audio_lab_badges import get_audio_lab_badge_for_path as get_badge_for_file
            return get_badge_for_file(filepath)
        except Exception:
            return None

    def _has_cover(self, item: MediaItem) -> bool:
        if not item.filepath:
            return False
        if item.filepath in self._cover_cache:
            return self._cover_cache[item.filepath]
        try:
            from library.cover_art_service import CoverArtService
            result = CoverArtService.find_cover(item.filepath) is not None
            self._cover_cache[item.filepath] = result
            return result
        except Exception:
            return False
