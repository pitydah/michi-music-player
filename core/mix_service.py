"""MixService — real mix generation using recommendation and rule engines.
Wraps SmartMixService, RecommendationService, MixRuleEngine and library/smart_mixes.py."""
from __future__ import annotations

import json
import logging
from typing import Any

from core.mix_rules import MixRuleEngine, MixDefinition, MixRuleGroup, MixRule

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

    def save_rules(self, mix_id: str, rules_json: str) -> dict:
        try:
            data = json.loads(rules_json)
            definition = MixDefinition(
                name=data.get("name", mix_id),
                groups=[MixRuleGroup(rules=[MixRule(**r) for r in g.get("rules", [])],
                                     logic=g.get("logic", "AND"))
                        for g in data.get("groups", [])],
                limit=data.get("limit", 30),
                sort_by=data.get("sort_by", "random"),
                seed=data.get("seed", 0),
            )
            new_id = self._rule_engine.generate_id(definition)
            return {"ok": True, "mix_id": new_id, "definition": {
                "name": definition.name, "limit": definition.limit,
                "sort_by": definition.sort_by, "seed": definition.seed,
                "groups": [{"logic": g.logic,
                            "rules": [{"field": r.field, "operator": r.operator,
                                       "value": r.value, "logic": r.logic}
                                      for r in g.rules]}
                           for g in definition.groups],
            }}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def preview_rules(self, rules_json: str, limit: int = 10) -> dict:
        try:
            data = json.loads(rules_json)
            definition = MixDefinition(
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
