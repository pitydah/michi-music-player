"""Recommendation service — orchestrates similarity, profile, mixes, and explanations."""

from __future__ import annotations

import logging
from typing import Any

from recommendation.schemas import (
    RecommendationResult,
    SmartMix,
    SeedCriteria,
    ListeningProfile,
    generate_recommendation_id,
)
from recommendation.similarity_engine import (
    metadata_similarity,
    discovery,
    seed_radio,
    acoustic_similarity,
    hybrid_score,
)
from recommendation.recommendation_explainer import explain
from recommendation.recommendation_repository import RecommendationRepository
from recommendation.listening_profile import build_profile
from recommendation.smart_mix_service import SmartMixService

logger = logging.getLogger("michi.recommendation.service")


def _sanitize_results(results: list[RecommendationResult]) -> list[dict]:
    return [
        {
            "track_id": r.track_id, "title": r.title, "artist": r.artist,
            "album": r.album, "year": r.year, "genre": r.genre,
            "duration": r.duration, "format": r.format,
            "score": r.score, "reasons": r.reasons, "strategy": r.strategy,
        }
        for r in results
    ]


class RecommendationService:
    def __init__(self, db: Any, profile: ListeningProfile | None = None,
                 use_favorites: bool = True, use_history: bool = False,
                 cache_days: int = 7):
        self._db = db
        self._profile = profile or build_profile(db, use_favorites=use_favorites)
        self._repo = RecommendationRepository()
        self._mix_svc = SmartMixService(db, self._profile)
        self._use_history = use_history
        self._cache_days = cache_days

    def _items(self) -> list:
        return self._db.get_all() if hasattr(self._db, "get_all") else []

    def _find_seed(self, text: str):
        items = self._items()
        text_lower = text.lower().strip()
        for item in items:
            artist = str(getattr(item, "artist", "") or "").lower()
            album = str(getattr(item, "album", "") or "").lower()
            title = str(getattr(item, "title", "") or "").lower()
            genre = str(getattr(item, "genre", "") or "").lower()
            if text_lower in artist:
                return item
            if text_lower in album:
                return item
            if text_lower in title:
                return item
            if text_lower in genre:
                return item
        return None

    def recommend_from_text(self, description: str,
                            limit: int = 30) -> dict[str, Any]:
        rec_id = generate_recommendation_id()
        items = self._items()
        seed = self._find_seed(description)
        results: list[RecommendationResult] = []

        if seed:
            results = seed_radio(items, seed, limit=limit)
            strategy = "seed_radio"
        elif self._profile and self._profile.top_artists:
            criteria = SeedCriteria(
                artist=self._profile.top_artists[0],
                genre=self._profile.top_genres[0] if self._profile.top_genres else "",
                year=self._profile.preferred_years[0] if self._profile.preferred_years else 0,
                ext=self._profile.preferred_formats[0] if self._profile.preferred_formats else "",
            )
            results = metadata_similarity(items, criteria, limit=limit)
            strategy = "metadata_similarity"
        else:
            results = discovery(items, limit=limit)
            strategy = "discovery"

        explanations = [explain(r) for r in results]
        self._repo.cache_recommendation(rec_id, "text", description,
                                         strategy, results, explanations, self._cache_days)

        return {
            "recommendation_id": rec_id,
            "seed": {"type": "text", "value": description},
            "strategy": strategy,
            "results": _sanitize_results(results),
            "total": len(results),
        }

    def recommend_from_track(self, track_id: int,
                             limit: int = 30) -> dict[str, Any]:
        rec_id = generate_recommendation_id()
        items = self._items()
        seed = next((i for i in items if getattr(i, "id", 0) == track_id), None)
        if not seed:
            return {"recommendation_id": rec_id, "error": "Track no encontrado.", "results": []}

        results = seed_radio(items, seed, limit=limit, exclude_id=track_id)
        explanations = [explain(r) for r in results]
        self._repo.cache_recommendation(rec_id, "track", str(track_id),
                                         "seed_radio", results, explanations, self._cache_days)

        return {
            "recommendation_id": rec_id,
            "seed": {"type": "track", "value": str(track_id),
                     "title": getattr(seed, "title", ""), "artist": getattr(seed, "artist", "")},
            "strategy": "seed_radio",
            "results": _sanitize_results(results),
            "total": len(results),
        }

    def recommend_from_artist(self, artist_name: str,
                              limit: int = 30) -> dict[str, Any]:
        rec_id = generate_recommendation_id()
        items = self._items()
        criteria = SeedCriteria(artist=artist_name)
        results = metadata_similarity(items, criteria, limit=limit)
        explanations = [explain(r) for r in results]
        self._repo.cache_recommendation(rec_id, "artist", artist_name,
                                         "metadata_similarity", results, explanations, self._cache_days)
        return {
            "recommendation_id": rec_id,
            "seed": {"type": "artist", "value": artist_name},
            "strategy": "metadata_similarity",
            "results": _sanitize_results(results),
            "total": len(results),
        }

    def recommend_from_album(self, album_title: str, artist_name: str = "",
                             limit: int = 30) -> dict[str, Any]:
        rec_id = generate_recommendation_id()
        items = self._items()
        criteria = SeedCriteria(artist=artist_name, album=album_title)
        results = metadata_similarity(items, criteria, limit=limit)
        explanations = [explain(r) for r in results]
        self._repo.cache_recommendation(rec_id, "album", album_title,
                                         "metadata_similarity", results, explanations, self._cache_days)
        return {
            "recommendation_id": rec_id,
            "seed": {"type": "album", "value": album_title, "artist": artist_name},
            "strategy": "metadata_similarity",
            "results": _sanitize_results(results),
            "total": len(results),
        }

    def recommend_from_genre(self, genre: str, limit: int = 30) -> dict[str, Any]:
        rec_id = generate_recommendation_id()
        items = self._items()
        criteria = SeedCriteria(genre=genre)
        results = metadata_similarity(items, criteria, limit=limit)
        explanations = [explain(r) for r in results]
        self._repo.cache_recommendation(rec_id, "genre", genre,
                                         "metadata_similarity", results, explanations, self._cache_days)
        return {
            "recommendation_id": rec_id,
            "seed": {"type": "genre", "value": genre},
            "strategy": "metadata_similarity",
            "results": _sanitize_results(results),
            "total": len(results),
        }

    def create_smart_mix(self, strategy: str, seed: dict | None = None,
                         limit: int = 30) -> dict[str, Any]:
        mix: SmartMix = self._mix_svc.create_mix(strategy, seed, limit)
        return {
            "mix_id": mix.mix_id,
            "title": mix.title,
            "description": mix.description,
            "strategy": mix.strategy,
            "seed_type": mix.seed_type,
            "seed_value": mix.seed_value,
            "results": _sanitize_results(mix.tracks),
            "explanation": mix.explanation,
            "total": len(mix.tracks),
        }

    def explain_recommendation(self, recommendation_id: str,
                               track_id: int = 0) -> dict[str, Any]:
        cached = self._repo.get_cached(recommendation_id)
        if cached and cached.get("explanations"):
            for e in cached["explanations"]:
                if e.get("track_id") == track_id:
                    return {
                        "track_id": track_id,
                        "explanation": {
                            "reason_summary": e.get("reason_summary", ""),
                            "detailed_reasons": e.get("detailed_reasons", []),
                        },
                    }
        return {
            "track_id": track_id,
            "explanation": {
                "reason_summary": "Recomendacion basada en tu biblioteca local.",
                "detailed_reasons": ["Coincidencia por metadata musical"],
            },
        }

    def record_feedback(self, recommendation_id: str, track_id: int,
                        feedback: str) -> dict[str, Any]:
        self._repo.record_feedback(recommendation_id, str(track_id), feedback)
        return {"status": "recorded", "recommendation_id": recommendation_id,
                "track_id": track_id, "feedback": feedback}

    def get_profile_summary(self) -> dict[str, Any]:
        return {
            "top_artists": self._profile.top_artists[:10],
            "top_genres": self._profile.top_genres[:10],
            "top_albums": self._profile.top_albums[:10],
            "preferred_years": self._profile.preferred_years[:5],
            "preferred_formats": self._profile.preferred_formats[:3],
            "unplayed_count": self._profile.unplayed_count,
            "favorite_count": self._profile.favorite_count,
            "total_plays": self._profile.total_plays,
        }

    def rebuild_profile(self) -> dict[str, Any]:
        self._profile = build_profile(self._db, use_favorites=True)
        return self.get_profile_summary()

    def recommend_by_sound(self, track_id: int,
                           limit: int = 30) -> dict[str, Any]:
        from core.settings_manager import get_bool
        if not get_bool("recommendation/use_acoustic_similarity"):
            return {"error": "Similitud acustica desactivada.", "results": []}

        from audio_analysis.analysis_service import AnalysisService
        analysis = AnalysisService(self._db)
        if not analysis.available:
            return {"error": "Analisis acustico no disponible.", "results": []}

        rec_id = generate_recommendation_id()
        items = self._items()
        seed = next((i for i in items if getattr(i, "id", 0) == track_id), None)
        if not seed:
            return {"recommendation_id": rec_id, "error": "Track no encontrado.", "results": []}

        results = acoustic_similarity(items, seed, analysis_svc=analysis, limit=limit)
        safe = _sanitize_results(results)
        self._repo.cache_recommendation(rec_id, "sound", str(track_id),
                                         "acoustic_similarity", results,
                                         [explain(r) for r in results], self._cache_days)

        return {
            "recommendation_id": rec_id,
            "seed": {"type": "sound", "value": str(track_id),
                     "title": getattr(seed, "title", ""), "artist": getattr(seed, "artist", "")},
            "strategy": "acoustic_similarity",
            "results": safe,
            "total": len(safe),
        }

    def recommend_hybrid(self, description: str,
                          limit: int = 30) -> dict[str, Any]:
        from core.settings_manager import get_bool
        use_acoustic = get_bool("recommendation/use_acoustic_similarity")

        from audio_analysis.analysis_service import AnalysisService
        analysis = AnalysisService(self._db) if use_acoustic else None

        rec_id = generate_recommendation_id()
        items = self._items()
        seed = self._find_seed(description)
        results: list[RecommendationResult] = []

        if seed:
            for item in items:
                if getattr(item, "id", 0) == getattr(seed, "id", 0):
                    continue
                score, reasons = hybrid_score(
                    item, seed, self._profile,
                    acoustic_weight=0.25 if use_acoustic else 0.0,
                    analysis_svc=analysis,
                )
                if score > 0.05:
                    results.append(RecommendationResult(
                        track_id=getattr(item, "id", 0),
                        title=str(getattr(item, "title", "") or ""),
                        artist=str(getattr(item, "artist", "") or ""),
                        album=str(getattr(item, "album", "") or ""),
                        score=score, reasons=reasons, strategy="hybrid",
                    ))

            results.sort(key=lambda x: x.score, reverse=True)
        else:
            results = discovery(items, limit=limit)

        results = results[:limit]
        self._repo.cache_recommendation(rec_id, "hybrid", description,
                                         "hybrid", results,
                                         [explain(r) for r in results], self._cache_days)

        return {
            "recommendation_id": rec_id,
            "seed": {"type": "hybrid", "value": description},
            "strategy": "hybrid",
            "results": _sanitize_results(results),
            "total": len(results),
        }
