"""Smart mix service — extends existing smart_mixes.py with new strategies.

Strategies live in a static registry (``_strategies``) of real methods, never
dynamic ``type(...)`` classes.  An empty library produces a mix WITHOUT
tracks, title or description (no fabricated empty mix presented as a
generated result); the facade (MixService) decides the honest outcome status.
Partial results are reported through ``SmartMix.warnings``.
"""
from __future__ import annotations

import time
from typing import Any

from recommendation.schemas import SeedCriteria, SmartMix, generate_mix_id
from recommendation.similarity_engine import (
    discovery,
    favorites_like,
    seed_radio,
    balanced_mix,
    quality_mix,
    metadata_similarity,
)


class SmartMixService:
    def __init__(self, db: Any, profile: Any = None):
        self._db = db
        self._profile = profile
        self._strategies = {
            "genre_journey": self._genre_journey,
            "decade_mix": self._decade_mix,
            "lossless_showcase": self._lossless_showcase,
            "favorites_neighbors": self._favorites_neighbors,
            "recently_missed": self._recently_missed,
            "deep_cuts": self._deep_cuts,
            "similar_to_artist": self._similar_to_artist,
            "similar_to_album": self._similar_to_album,
            "balanced": self._balanced_mix,
            "daily": self._balanced_mix,
        }

    def supported_strategies(self) -> set[str]:
        return set(self._strategies)

    def _all_items(self) -> list:
        return self._db.get_all() if hasattr(self._db, "get_all") else []

    def _favorite_ids(self) -> set[int]:
        """Return the numeric ids of favorited tracks.

        The favorites table stores ``track_id`` as the filepath; map those
        filepaths back to ``media_items.id`` so similarity engines can match.
        """
        if not hasattr(self._db, "get_favorites"):
            return set()
        fav_paths = set(self._db.get_favorites() or [])
        if not fav_paths:
            return set()
        ids = {
            getattr(i, "id", 0)
            for i in self._all_items()
            if getattr(i, "filepath", "") in fav_paths
        }
        return {i for i in ids if i}

    def create_mix(self, strategy: str, seed: dict | None = None,
                   limit: int = 30) -> SmartMix:
        items = self._all_items()
        if not items:
            return SmartMix(mix_id=generate_mix_id(), strategy=strategy)

        seed_item = None
        if seed and seed.get("track_id"):
            for item in items:
                if getattr(item, "id", 0) == seed["track_id"]:
                    seed_item = item
                    break

        handler = self._strategies.get(strategy, self._balanced_mix)
        tracks, title, desc, warnings = handler(items, seed, seed_item, limit)

        return SmartMix(
            mix_id=generate_mix_id(),
            title=title, description=desc,
            strategy=strategy,
            seed_type=seed.get("type", "") if seed else "",
            seed_value=seed.get("value", "") if seed else "",
            tracks=tracks, explanation=desc,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            is_saved=False,
            warnings=warnings,
        )

    def _genre_journey(self, items, seed, seed_item, limit):
        genre = seed.get("genre", "") if seed else ""
        if not genre and self._profile:
            genre = (self._profile.top_genres or [""])[0]
        criteria = SeedCriteria(genre=genre)
        tracks = metadata_similarity(items, criteria, limit=limit)
        title = f"Viaje por {genre}" if genre else "Viaje musical"
        desc = f"Canciones del genero {genre}" if genre else "Exploracion musical por generos"
        return tracks, title, desc, []

    def _decade_mix(self, items, seed, seed_item, limit):
        year_str = seed.get("year", "1990") if seed else "1990"
        try:
            decade = int(int(year_str) / 10) * 10
        except (ValueError, TypeError):
            decade = 1990
        decade_items = [
            i for i in items
            if getattr(i, "year", 0) and decade <= int(getattr(i, "year", 0)) < decade + 10
        ]
        from recommendation.similarity_engine import _build_result, _quality_bonus
        tracks = [
            _build_result(
                item, _quality_bonus(item) * 0.5 + 0.5,
                [f"Decada de los {decade % 100}"], "decade_mix",
            )
            for item in decade_items[:limit]
        ]
        return tracks, f"Decada de los {decade % 100}", f"Canciones de los años {decade}", []

    def _lossless_showcase(self, items, seed, seed_item, limit):
        return quality_mix(items, limit=limit), "Muestra lossless", "Canciones en formato sin perdida", []

    def _favorites_neighbors(self, items, seed, seed_item, limit):
        fav_ids = self._favorite_ids()
        warnings = []
        tracks = []
        if fav_ids:
            tracks = favorites_like(items, fav_ids, limit=limit)
            if not tracks:
                warnings.append("Sin coincidencias con favoritos; se uso descubrimiento")
                tracks = discovery(items, limit=limit)
        else:
            warnings.append("Sin favoritos en la biblioteca; se uso descubrimiento")
            tracks = discovery(items, limit=limit)
        return tracks, "Vecinos de favoritos", "Canciones similares a tus favoritas", warnings

    def _recently_missed(self, items, seed, seed_item, limit):
        played = set()
        for i in items:
            if getattr(i, "play_count", 0) > 0 and getattr(i, "last_played", 0):
                lp = getattr(i, "last_played", 0)
                if lp > time.time() - 86400 * 30:
                    played.add(getattr(i, "id", 0))
        tracks = discovery(items, played_ids=played, limit=limit)
        return tracks, "Te las perdiste", "Canciones que no escuchas hace mas de 30 dias", []

    def _deep_cuts(self, items, seed, seed_item, limit):
        fav_ids = self._favorite_ids()
        warnings = []
        tracks = []
        if fav_ids:
            from recommendation.similarity_engine import _build_result, _genre_overlap
            favs = [i for i in items if getattr(i, "id", 0) in fav_ids]
            scores = []
            for item in items:
                if getattr(item, "id", 0) in fav_ids:
                    continue
                score = 0.0
                for fav in favs:
                    score += _genre_overlap(item, fav) * 0.5
                    years = abs(int(getattr(item, "year", 0) or 0) - int(getattr(fav, "year", 0) or 0))
                    score += 1.0 / (1 + years * 0.3) * 0.3
                    if getattr(item, "artist", "").lower() == getattr(fav, "artist", "").lower():
                        score += 0.2
                score /= max(len(favs), 1)
                if score > 0.1:
                    scores.append((score, item))
            scores.sort(key=lambda x: x[0], reverse=True)
            tracks = [_build_result(item, s, ["Corte profundo", "Similar a tus favoritos"], "deep_cuts")
                      for s, item in scores[:limit]]
            if not tracks:
                warnings.append("Sin cortes profundos suficientes para tus favoritos")
        else:
            warnings.append("Sin favoritos en la biblioteca")
        return tracks, "Cortes profundos", "Canciones ocultas que podrian gustarte", warnings

    def _similar_to_artist(self, items, seed, seed_item, limit):
        artist = seed.get("artist", "") if seed else ""
        warnings = []
        tracks = []
        if seed_item is not None:
            tracks = seed_radio(items, seed_item, limit=limit)
        elif artist:
            warnings.append("Track semilla no encontrado; se uso el artista")
            criteria = SeedCriteria(artist=artist)
            tracks = metadata_similarity(items, criteria, limit=limit)
        else:
            warnings.append("Sin artista ni track semilla")
        title = f"Similar a {artist}" if artist else "Mix por artista"
        desc = f"Canciones similares a {artist}" if artist else "Recomendaciones por artista"
        return tracks, title, desc, warnings

    def _similar_to_album(self, items, seed, seed_item, limit):
        album = seed.get("album", "") if seed else ""
        artist = seed.get("artist", "") if seed else ""
        warnings = []
        tracks = []
        if seed_item is not None:
            tracks = seed_radio(items, seed_item, limit=limit)
        elif album:
            warnings.append("Track semilla no encontrado; se uso el album")
            criteria = SeedCriteria(artist=artist, album=album)
            tracks = metadata_similarity(items, criteria, limit=limit)
        else:
            warnings.append("Sin album ni track semilla")
        title = f"Como {album}" if album else "Mix por album"
        desc = f"Mezcla basada en el album {album}" if album else "Recomendaciones por album"
        return tracks, title, desc, warnings

    def _balanced_mix(self, items, seed, seed_item, limit):
        tracks = balanced_mix(items, SeedCriteria(), limit=limit)
        return tracks, "Mix balanceado", "Mezcla entre canciones familiares y por descubrir", []
