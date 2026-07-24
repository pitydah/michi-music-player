"""MixRuleEngine — rule-based mix generation with AND/OR operators, include/exclude, seed reproducibility."""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any



@dataclass
class MixRule:
    field: str          # artist, album, genre, year, duration, play_count, etc.
    operator: str       # is, is_not, contains, not_contains, gt, lt, gte, lte, between, before, after
    value: Any
    logic: str = "AND"  # AND or OR group


@dataclass
class MixRuleGroup:
    rules: list[MixRule] = field(default_factory=list)
    logic: str = "AND"  # AND / OR


@dataclass
class MixDefinition:
    name: str = ""
    groups: list[MixRuleGroup] = field(default_factory=list)
    limit: int = 30
    sort_by: str = "random"   # random, title, artist, album, year, play_count, duration, date_added
    seed: int = 0
    exclude_fields: list[str] = field(default_factory=list)


class MixRuleEngine:
    OPERATORS = {
        "is": lambda v, q: str(v).lower() == str(q).lower(),
        "is_not": lambda v, q: str(v).lower() != str(q).lower(),
        "contains": lambda v, q: str(q).lower() in str(v).lower(),
        "not_contains": lambda v, q: str(q).lower() not in str(v).lower(),
        "gt": lambda v, q: float(v) > float(q),
        "lt": lambda v, q: float(v) < float(q),
        "gte": lambda v, q: float(v) >= float(q),
        "lte": lambda v, q: float(v) <= float(q),
        "between": lambda v, q: isinstance(q, (list, tuple)) and len(q) == 2 and float(q[0]) <= float(v) <= float(q[1]),
        "before": lambda v, q: int(v) < int(q),
        "after": lambda v, q: int(v) > int(q),
    }

    def __init__(self, library_query_service=None):
        self._lqs = library_query_service

    def evaluate(self, track: dict, group: MixRuleGroup) -> bool:
        results = []
        for rule in group.rules:
            field_value = track.get(rule.field, "")
            op_fn = self.OPERATORS.get(rule.operator)
            if op_fn is None:
                results.append(False)
                continue
            results.append(op_fn(field_value, rule.value))
        if group.logic == "AND":
            return all(results)
        return any(results)

    def matches(self, track: dict, definition: MixDefinition) -> bool:
        return all(self.evaluate(track, group) for group in definition.groups)

    def filter(self, tracks: list[dict], definition: MixDefinition) -> list[dict]:
        result = [t for t in tracks if self.matches(t, definition)]
        if definition.sort_by == "random":
            seed = definition.seed or 42
            rng = random.Random(seed)
            rng.shuffle(result)
        elif definition.sort_by == "title":
            result.sort(key=lambda t: str(t.get("title", "")))
        elif definition.sort_by == "artist":
            result.sort(key=lambda t: str(t.get("artist", "")))
        elif definition.sort_by == "year":
            result.sort(key=lambda t: int(t.get("year", 0)), reverse=True)
        elif definition.sort_by == "play_count":
            result.sort(key=lambda t: int(t.get("play_count", 0)), reverse=True)
        elif definition.sort_by == "duration":
            result.sort(key=lambda t: float(t.get("duration", 0)))
        return result[:definition.limit]

    def preview(self, tracks: list[dict], definition: MixDefinition) -> dict:
        matched = self.filter(tracks, definition)
        return {
            "ok": True,
            "total_tracks": len(tracks),
            "matched": len(matched),
            "limit": definition.limit,
            "tracks": matched[:10],  # preview limited
            "sorted_by": definition.sort_by,
            "seed": definition.seed,
        }

    def generate_id(self, definition: MixDefinition) -> str:
        raw = f"{definition.name}:{definition.seed}:{definition.sort_by}:{definition.limit}"
        for g in definition.groups:
            for r in g.rules:
                raw += f"|{r.field}:{r.operator}:{r.value}:{r.logic}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
