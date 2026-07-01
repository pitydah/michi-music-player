"""GenreStatsService — aggregated statistics and health for genres.

Computes and caches genre-level stats, health metrics, and related genres.
Does NOT depend on Qt.
"""
from __future__ import annotations

import logging
import time
from typing import Any


_log = logging.getLogger("michi.genre_stats")

TTL_STATS = 300


class GenreStatsService:
    def __init__(self, db, genre_repo):
        self._db = db
        self._repo = genre_repo
        self._cached_stats: dict[str, Any] | None = None
        self._last_computed: float = 0.0

    def invalidate(self):
        self._cached_stats = None
        self._last_computed = 0.0
        self._repo.invalidate_stats()

    def get_stats(self, force: bool = False) -> dict[str, Any]:
        now = time.time()
        if force or self._cached_stats is None or (now - self._last_computed) > TTL_STATS:
            try:
                self._cached_stats = self._repo.compute_stats(force=True)
                self._last_computed = now
            except Exception as e:
                _log.warning("get_stats failed: %s", e)
                self._cached_stats = self._repo.get_cached_stats() or {}
        return self._cached_stats or {}

    def get_genres_overview(self) -> list[dict]:
        stats = self.get_stats()
        overview = []
        for genre, s in stats.items():
            overview.append({
                "genre": genre,
                "canonical": genre,
                "track_count": s.get("track_count", 0),
                "album_count": s.get("album_count", 0),
                "artist_count": s.get("artist_count", 0),
                "duration_total": s.get("duration_total", 0.0),
                "dominant_format": s.get("dominant_format", ""),
                "dominant_quality": s.get("dominant_quality", ""),
                "lossless_count": s.get("lossless_count", 0),
                "lossy_count": s.get("lossy_count", 0),
                "hires_count": s.get("hires_count", 0),
                "missing_metadata_count": s.get("missing_metadata_count", 0),
                "play_count": s.get("play_count", 0),
                "health": s.get("health", "ok"),
            })
        return sorted(overview, key=lambda g: (-g["track_count"], g["genre"]))

    def get_genre_detail(self, genre: str) -> dict:
        stats = self.get_stats()
        return stats.get(genre, {})

    def get_health_summary(self) -> dict:
        stats = self.get_stats()
        total_tracks = sum(s.get("track_count", 0) for s in stats.values())
        missing = sum(s.get("missing_metadata_count", 0) for s in stats.values())
        ok_count = sum(1 for s in stats.values() if s.get("health") == "ok")
        warning_count = sum(1 for s in stats.values() if s.get("health") != "ok")
        total_genres = len(stats)
        health_pct = int((ok_count / max(total_genres, 1)) * 100)
        return {
            "total_genres": total_genres,
            "total_tracks": total_tracks,
            "missing_metadata": missing,
            "healthy_count": ok_count,
            "warning_count": warning_count,
            "health_pct": health_pct,
        }

    def get_tracks_without_genre(self) -> list:
        try:
            all_items = self._db.get_all()
            return [item for item in all_items if not (getattr(item, 'genre', '') or '').strip()]
        except Exception as e:
            _log.warning("get_tracks_without_genre failed: %s", e)
            return []

    def get_tracks_for_genre(self, canonical: str) -> list:
        track_ids = self._repo.get_tracks_for_genre(canonical)
        items = []
        for tid in track_ids:
            item = self._db.get_media_item_by_id(tid)
            if item:
                items.append(item)
        return items
