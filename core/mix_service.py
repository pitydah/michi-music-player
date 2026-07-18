"""MixService — real mix generation using recommendation and rule engines.
Wraps SmartMixService, RecommendationService, MixRuleEngine and library/smart_mixes.py."""
from __future__ import annotations

import json
import logging
from typing import Any

from core.mix_rules import MixRuleEngine
from core.mix.repository import MixRepository
from core.mix_rules import MixRuleEngine, MixDefinition as MixEngineDef, MixRuleGroup, MixRule
from core.mix.repository import MixDefinition as PersistedMix

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
        self._rule_engine = MixRuleEngine(library_query_service)
        self._repo = MixRepository(db) if db else None
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

    def save_rules(self, mix_id: str, rules_json: str) -> dict:
        try:
            data = json.loads(rules_json)
            from core.mix_rules import MixRuleGroup, MixRule
            definition = type('', (), {})()
            definition.name = data.get("name", mix_id)
            definition.groups = [MixRuleGroup(
                rules=[MixRule(**r) for r in g.get("rules", [])],
                logic=g.get("logic", "AND"))
                for g in data.get("groups", [])]
            definition.limit = data.get("limit", 30)
            definition.sort_by = data.get("sort_by", "random")
            definition.seed = data.get("seed", 0)
            new_id = self._rule_engine.generate_id(definition)

            if self._repo:
                persisted = PersistedMix(
                    mix_id=new_id, name=definition.name, rules_json=rules_json,
                    limit=definition.limit, sort_by=definition.sort_by, seed=definition.seed,
                )
                self._repo.save(persisted)

            return {"ok": True, "mix_id": new_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def load_rules(self, mix_id: str) -> dict:
        if not self._repo:
            return {"ok": False, "error": "REPOSITORY_UNAVAILABLE"}
        definition = self._repo.load(mix_id)
        if not definition:
            return {"ok": False, "error": "NOT_FOUND"}
        return {
            "ok": True, "mix_id": definition.mix_id, "name": definition.name,
            "rules_json": definition.rules_json, "limit": definition.limit,
            "sort_by": definition.sort_by, "seed": definition.seed,
            "created_at": definition.created_at, "updated_at": definition.updated_at,
            "play_count": definition.play_count,
        }

    def list_rules(self) -> dict:
        if not self._repo:
            return {"ok": False, "error": "REPOSITORY_UNAVAILABLE", "mixes": []}
        mixes = self._repo.list_all()
        return {"ok": True, "mixes": [{
            "mix_id": m.mix_id, "name": m.name,
            "updated_at": m.updated_at, "play_count": m.play_count,
        } for m in mixes]}

    def delete_rules(self, mix_id: str) -> dict:
        if not self._repo:
            return {"ok": False, "error": "REPOSITORY_UNAVAILABLE"}
        return self._repo.delete(mix_id)

    def preview_rules(self, rules_json: str, limit: int = 10) -> dict:
        try:
            data = json.loads(rules_json)
            definition = MixEngineDef(
                name=data.get("name", "preview"),
                groups=[MixRuleGroup(rules=[MixRule(**r) for r in g.get("rules", [])],
                                     logic=g.get("logic", "AND"))
                        for g in data.get("groups", [])],
                limit=limit, sort_by=data.get("sort_by", "random"),
                seed=data.get("seed", 0),
            )
            if not self._library_query:
                return {"ok": False, "error": "LIBRARY_UNAVAILABLE", "tracks": []}
            tracks = self._library_query.search("")
            matched = self._rule_engine.filter(tracks, definition)
            return {"ok": True, "matched": len(matched),
                    "tracks": matched[:limit],
                    "total_in_library": len(tracks)}
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
