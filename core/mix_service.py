"""Mix domain facade for generated, catalog and persisted rule-based mixes.

``MixService`` is the single object exposed to the QML bridge. Recommendation
logic, SQL catalog queries and persistence remain separate collaborators so the
UI never talks directly to SQLite or to a recommendation backend.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from core.mix.repository import MixDefinition as PersistedMix
from core.mix.repository import MixRepository
from core.mix_rules import MixDefinition as MixEngineDef
from core.mix_rules import MixRule, MixRuleEngine, MixRuleGroup

logger = logging.getLogger("michi.mix_service")


class MixService:
    def __init__(
        self,
        db: Any = None,
        recommendation_service: Any = None,
        smart_mix_service: Any = None,
        mix_query_service: Any = None,
        library_query_service: Any = None,
        playlist_service: Any = None,
        event_bus: Any = None,
    ) -> None:
        self._db = db
        self._event_bus = event_bus
        self._recommendation = recommendation_service
        self._smart_mix = smart_mix_service
        self._mix_query = mix_query_service
        self._library_query = library_query_service
        self._playlist_service = playlist_service
        self._rule_engine = MixRuleEngine(library_query_service)
        self._repo = MixRepository(db) if db else None
        self._cancelled = False

    @property
    def available(self) -> bool:
        return any(
            (
                self._mix_query,
                self._smart_mix,
                self._recommendation,
                self._library_query,
            )
        )

    @property
    def query_service(self) -> Any | None:
        return self._mix_query

    def _query(
        self, method: str, *args: Any, **kwargs: Any
    ) -> list[dict[str, Any]]:
        service = self._mix_query
        if service is None:
            logger.warning("Mix query service unavailable for %s", method)
            return []
        operation = getattr(service, method, None)
        if not callable(operation):
            logger.error("Mix query service does not implement %s", method)
            return []
        try:
            result = operation(*args, **kwargs)
        except Exception as exc:
            # Query service logs the concrete SQL failure.
            logger.warning("Mix query '%s' failed: %s", method, exc)
            return []
        return [
            dict(item)
            for item in (result or [])
            if isinstance(item, Mapping)
        ]

    # Category contract consumed by ui_qml_bridge.mix_bridge.MixBridge.
    def favorites(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._query("favorites", limit=limit)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._query("recent", limit=limit)

    def most_played(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._query("most_played", limit=limit)

    def unplayed(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._query("unplayed", limit=limit)

    def rediscovery(
        self, limit: int = 30, older_than_days: int = 180
    ) -> list[dict[str, Any]]:
        return self._query(
            "rediscovery",
            limit=limit,
            older_than_days=older_than_days,
        )

    def genre(
        self, genre: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        return self._query("genre", genre, limit=limit)

    def by_field(
        self, field: str, value: str = "", limit: int = 30
    ) -> list[dict[str, Any]]:
        return self._query("by_field", field, value=value, limit=limit)

    def by_album(
        self, album: str = "", limit: int = 30
    ) -> list[dict[str, Any]]:
        return self._query("by_album", album=album, limit=limit)

    def by_decade(
        self, limit: int = 30, decade: int = 0
    ) -> list[dict[str, Any]]:
        """Return a decade mix.

        ``limit`` intentionally remains the first argument for compatibility
        with the existing QML bridge, which historically called
        ``by_decade(30)`` intending a 30-track limit.
        """
        return self._query("by_decade", decade=decade, limit=limit)

    def by_year(
        self, limit: int = 30, year: int = 0
    ) -> list[dict[str, Any]]:
        """Return a year mix while preserving the bridge contract."""
        return self._query("by_year", year=year, limit=limit)

    def high_quality(
        self,
        limit: int = 30,
        min_bitrate: int = 320,
        *,
        lossless: bool = False,
    ) -> list[dict[str, Any]]:
        """Return high-quality tracks while preserving bridge compatibility."""
        return self._query(
            "high_quality",
            min_bitrate=min_bitrate,
            limit=limit,
            lossless=lossless,
        )

    def custom(
        self,
        filters: Mapping[str, Any] | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        return self._query("custom", filters or {}, limit=limit)

    def generate(
        self,
        strategy: str = "daily",
        seed: dict | None = None,
        limit: int = 30,
    ) -> dict[str, Any]:
        self._cancelled = False
        if self._smart_mix:
            try:
                mix = self._smart_mix.create_mix(
                    strategy=strategy,
                    seed=seed,
                    limit=limit,
                )
                return self._format_mix(mix)
            except Exception as exc:
                logger.error("SmartMix error: %s", exc, exc_info=True)
        return self._fallback_mix(strategy, limit)

    @staticmethod
    def _format_mix(mix: Any) -> dict[str, Any]:
        tracks = []
        for track in getattr(mix, "tracks", []) or []:
            tracks.append(
                {
                    "id": getattr(
                        track,
                        "id",
                        getattr(track, "track_id", 0),
                    ),
                    "track_id": getattr(
                        track,
                        "track_id",
                        getattr(track, "id", 0),
                    ),
                    "filepath": getattr(track, "filepath", ""),
                    "title": getattr(track, "title", ""),
                    "artist": getattr(track, "artist", ""),
                    "album": getattr(track, "album", ""),
                    "score": getattr(track, "score", 0.0),
                }
            )
        return {
            "ok": True,
            "mix_id": getattr(mix, "mix_id", ""),
            "title": getattr(mix, "title", ""),
            "description": getattr(mix, "description", ""),
            "strategy": getattr(mix, "strategy", "unknown"),
            "tracks": tracks,
            "count": len(tracks),
        }

    def _fallback_mix(
        self, strategy: str, limit: int
    ) -> dict[str, Any]:
        loaders = {
            "recent": self.recent,
            "favorites": self.favorites,
            "most_played": self.most_played,
            "unplayed": self.unplayed,
            "rediscovery": self.rediscovery,
        }
        loader = loaders.get(strategy)
        tracks = loader(limit) if loader else []
        return {
            "ok": bool(loader),
            "error": "UNKNOWN_STRATEGY" if loader is None else "",
            "mix_id": f"fallback_{strategy}",
            "title": f"Mix {strategy}",
            "description": f"Mix generado con {strategy}",
            "strategy": strategy,
            "tracks": tracks,
            "count": len(tracks),
        }

    def save_rules(
        self, mix_id: str, rules_json: str
    ) -> dict[str, Any]:
        try:
            data = json.loads(rules_json)
            definition = MixEngineDef(
                name=data.get("name", mix_id),
                groups=[
                    MixRuleGroup(
                        rules=[
                            MixRule(**rule)
                            for rule in group.get("rules", [])
                        ],
                        logic=group.get("logic", "AND"),
                    )
                    for group in data.get("groups", [])
                ],
                limit=int(data.get("limit", 30)),
                sort_by=data.get("sort_by", "random"),
                seed=int(data.get("seed", 0)),
            )
            new_id = self._rule_engine.generate_id(definition)
            if self._repo:
                persisted = PersistedMix(
                    mix_id=new_id,
                    name=definition.name,
                    rules_json=rules_json,
                    limit=definition.limit,
                    sort_by=definition.sort_by,
                    seed=definition.seed,
                )
                self._repo.save(persisted)
            return {"ok": True, "mix_id": new_id}
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": str(exc)}

    def load_rules(self, mix_id: str) -> dict[str, Any]:
        if not self._repo:
            return {
                "ok": False,
                "error": "REPOSITORY_UNAVAILABLE",
            }
        definition = self._repo.load(mix_id)
        if not definition:
            return {"ok": False, "error": "NOT_FOUND"}
        return {
            "ok": True,
            "mix_id": definition.mix_id,
            "name": definition.name,
            "rules_json": definition.rules_json,
            "limit": definition.limit,
            "sort_by": definition.sort_by,
            "seed": definition.seed,
            "created_at": definition.created_at,
            "updated_at": definition.updated_at,
            "play_count": definition.play_count,
        }

    def list_rules(self) -> dict[str, Any]:
        if not self._repo:
            return {
                "ok": False,
                "error": "REPOSITORY_UNAVAILABLE",
                "mixes": [],
            }
        mixes = self._repo.list_all()
        return {
            "ok": True,
            "mixes": [
                {
                    "mix_id": mix.mix_id,
                    "name": mix.name,
                    "updated_at": mix.updated_at,
                    "play_count": mix.play_count,
                }
                for mix in mixes
            ],
        }

    def delete_rules(self, mix_id: str) -> dict[str, Any]:
        if not self._repo:
            return {
                "ok": False,
                "error": "REPOSITORY_UNAVAILABLE",
            }
        return self._repo.delete(mix_id)

    def preview_rules(
        self, rules_json: str, limit: int = 10
    ) -> dict[str, Any]:
        try:
            data = json.loads(rules_json)
            definition = MixEngineDef(
                name=data.get("name", "preview"),
                groups=[
                    MixRuleGroup(
                        rules=[
                            MixRule(**rule)
                            for rule in group.get("rules", [])
                        ],
                        logic=group.get("logic", "AND"),
                    )
                    for group in data.get("groups", [])
                ],
                limit=limit,
                sort_by=data.get("sort_by", "random"),
                seed=data.get("seed", 0),
            )
            if not self._library_query:
                return {
                    "ok": False,
                    "error": "LIBRARY_UNAVAILABLE",
                    "tracks": [],
                }
            tracks = self._library_query.search("")
            matched = self._rule_engine.filter(tracks, definition)
            return {
                "ok": True,
                "matched": len(matched),
                "tracks": matched[:limit],
                "total_in_library": len(tracks),
            }
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"Invalid JSON: {exc}"}
        except (TypeError, ValueError, AttributeError) as exc:
            return {"ok": False, "error": str(exc)}
