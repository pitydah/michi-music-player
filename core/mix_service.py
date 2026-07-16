"""MixService — real mix generation using recommendation and smart mix engines.
Wraps SmartMixService, RecommendationService, and library/smart_mixes.py."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.mix_service")


class MixService:
    def __init__(self, db=None, recommendation_service=None, smart_mix_service=None,
                 library_query_service=None, playlist_service=None, event_bus=None):
        self._db = db
        self._event_bus = event_bus
        self._recommendation = recommendation_service
        self._smart_mix = smart_mix_service
        self._library_query = library_query_service
        self._playlist_service = playlist_service
        self._cancelled = False

    @property
    def available(self) -> bool:
        return self._smart_mix is not None or self._library_query is not None

    def generate(self, strategy: str = "daily", seed: dict | None = None,
                 limit: int = 30) -> dict:
        self._cancelled = False
        if self._smart_mix:
            try:
                mix = self._smart_mix.create_mix(strategy=strategy, seed=seed, limit=limit)
                return self._format_mix(mix)
            except Exception as e:
                logger.error("SmartMix error: %s", e)
        return self._fallback_mix(strategy, limit)

    def _format_mix(self, mix) -> dict:
        tracks = []
        for t in getattr(mix, "tracks", []) or []:
            tracks.append({
                "id": getattr(t, "id", 0),
                "title": getattr(t, "title", ""),
                "artist": getattr(t, "artist", ""),
                "album": getattr(t, "album", ""),
                "score": getattr(t, "score", 0.0),
            })
        return {
            "ok": True,
            "mix_id": getattr(mix, "mix_id", ""),
            "title": getattr(mix, "title", ""),
            "description": getattr(mix, "description", ""),
            "strategy": getattr(mix, "strategy", "unknown"),
            "tracks": tracks,
            "count": len(tracks),
        }

    def _fallback_mix(self, strategy: str, limit: int) -> dict:
        if not self._library_query:
            return {"ok": False, "error": "SERVICE_UNAVAILABLE", "tracks": []}
        try:
            items = self._library_query.recently_played(limit=limit) if strategy == "recent" else []
            return {
                "ok": True,
                "mix_id": f"fallback_{strategy}",
                "title": f"Mix {strategy}",
                "description": f"Mix generado con {strategy}",
                "strategy": strategy,
                "tracks": [{"id": getattr(i, "id", 0), "title": getattr(i, "title", "")} for i in items],
                "count": len(items),
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "tracks": []}

    def cancel(self):
        self._cancelled = True

    def health(self) -> dict:
        return {"available": self.available, "smart_mix": self._smart_mix is not None}

    def shutdown(self):
        self._cancelled = True
