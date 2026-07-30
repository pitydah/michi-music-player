"""Smart Collections service — create, edit, persist, query."""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from core import settings_manager

logger = logging.getLogger("michi.collections")

SETTINGS_KEY = "library/smart_collections"
_FIELDS = {"artist", "album", "genre", "year", "format", "plays", "rating", "title"}
_OPERATORS = {"eq", "neq", "contains", "gt", "lt", "gte", "lte", "between"}
_NUMERIC_FIELDS = {"year", "plays", "rating"}
_TRACK_FIELDS = {"plays": "play_count", "format": "ext"}
_FETCH_BATCH_SIZE = 500

# SQL compilation map for paginated collection queries.
# Maps a rule field to (kind, column) where kind is text/format/numeric.
_SQL_FIELD: dict[str, tuple[str, str]] = {
    "artist": ("text", "m.artist"),
    "album": ("text", "m.album"),
    "genre": ("text", "m.genre"),
    "title": ("text", "m.title"),
    "format": ("format", "LOWER(LTRIM(COALESCE(m.ext, ''), '.'))"),
    "year": ("numeric", "m.year"),
    "plays": ("numeric", "m.play_count"),
    "rating": ("numeric", "m.rating"),
}
_SQL_SORT_COLUMN: dict[str, str] = {
    "title": "LOWER(COALESCE(m.title, ''))",
    "artist": "LOWER(COALESCE(m.artist, ''))",
    "album": "LOWER(COALESCE(m.album, ''))",
    "genre": "LOWER(COALESCE(m.genre, ''))",
    "format": "LOWER(LTRIM(COALESCE(m.ext, ''), '.'))",
    "year": "COALESCE(m.year, 0)",
    "plays": "COALESCE(m.play_count, 0)",
    "rating": "COALESCE(m.rating, 0)",
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(slots=True)
class CollectionRule:
    """One predicate in a smart collection."""

    field: str
    operator: str
    value: Any


@dataclass(slots=True)
class SmartCollection:
    """Persisted smart collection definition."""

    id: str
    name: str
    rules: list[CollectionRule] = field(default_factory=list)
    logic: str = "AND"
    sort_by: str = "title"
    sort_order: str = "asc"
    icon: str = "playlists"
    created: float = 0.0
    updated: float = 0.0


class CollectionService:
    """Manage smart collection definitions and execute their rules."""

    def __init__(self, db: Any | None = None, query_service: Any | None = None) -> None:
        self._db = db
        self._qs = query_service
        self._collections: list[SmartCollection] = []
        self._load()

    def _load(self) -> None:
        raw = settings_manager.get(SETTINGS_KEY)
        if not raw:
            return
        try:
            entries = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            logger.warning("Ignoring invalid smart collections settings")
            return
        if not isinstance(entries, list):
            return
        for entry in entries:
            try:
                collection = self._from_dict(entry)
            except (TypeError, ValueError):
                logger.warning("Ignoring invalid smart collection record")
                continue
            self._collections.append(collection)

    def _save(self) -> None:
        settings_manager.set_(SETTINGS_KEY, json.dumps(self.list(), ensure_ascii=False))

    def list(self) -> list[dict[str, Any]]:
        """Return all collection definitions in creation order."""
        return [asdict(collection) for collection in self._collections]

    def create(
        self,
        name: str,
        rules: list[dict[str, Any] | CollectionRule],
        logic: str = "AND",
    ) -> dict[str, Any]:
        """Create and persist a smart collection."""
        normalized_name = str(name or "").strip()
        if not normalized_name:
            return {"ok": False, "error": "INVALID_NAME"}
        try:
            normalized_rules = self._normalize_rules(rules)
            normalized_logic = self._normalize_logic(logic)
        except (TypeError, ValueError) as error:
            return {"ok": False, "error": str(error)}
        if not normalized_rules:
            return {"ok": False, "error": "INVALID_RULES"}
        now = time.time()
        collection = SmartCollection(
            id=f"collection-{uuid.uuid4().hex}",
            name=normalized_name,
            rules=normalized_rules,
            logic=normalized_logic,
            created=now,
            updated=now,
        )
        self._collections.append(collection)
        self._save()
        return {"ok": True, "collection": asdict(collection)}

    def update(self, collection_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update mutable fields on an existing collection."""
        collection = self._find(collection_id)
        if collection is None:
            return {"ok": False, "error": "NOT_FOUND"}
        try:
            if "name" in kwargs:
                name = str(kwargs["name"] or "").strip()
                if not name:
                    return {"ok": False, "error": "INVALID_NAME"}
                collection.name = name
            if "rules" in kwargs:
                rules = self._normalize_rules(kwargs["rules"])
                if not rules:
                    return {"ok": False, "error": "INVALID_RULES"}
                collection.rules = rules
            if "logic" in kwargs:
                collection.logic = self._normalize_logic(kwargs["logic"])
            if "sort_by" in kwargs:
                collection.sort_by = self._normalize_sort_by(kwargs["sort_by"])
            if "sort_order" in kwargs:
                collection.sort_order = self._normalize_sort_order(kwargs["sort_order"])
            if "icon" in kwargs:
                collection.icon = str(kwargs["icon"] or "playlists")
        except (TypeError, ValueError) as error:
            return {"ok": False, "error": str(error)}
        collection.updated = time.time()
        self._save()
        return {"ok": True, "collection": asdict(collection)}

    def delete(self, collection_id: str) -> dict[str, Any]:
        """Delete a collection by identifier."""
        for index, collection in enumerate(self._collections):
            if collection.id == collection_id:
                self._collections.pop(index)
                self._save()
                return {"ok": True, "id": collection_id}
        return {"ok": False, "error": "NOT_FOUND"}

    def query(
        self,
        collection_id: str,
        limit: int = 250,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Execute collection rules against the query service."""
        collection = self._find(collection_id)
        if collection is None:
            return {"ok": False, "error": "NOT_FOUND", "items": [], "total": 0}
        # Prefer the paginated SQL path when a database is wired so we never
        # load the whole catalogue into memory. The in-memory fallback below
        # remains for environments that only inject a query service (tests).
        if self._db is not None and getattr(self._db, "conn", None) is not None:
            return self.query_collection_page(collection_id, offset, limit)
        if self._qs is None:
            return {"ok": False, "error": "QUERY_SERVICE_UNAVAILABLE", "items": [], "total": 0}
        safe_limit = max(1, min(1000, int(limit)))
        safe_offset = max(0, int(offset))
        try:
            tracks = self._fetch_all_tracks()
            matches = [track for track in tracks if self._matches(track, collection)]
            matches.sort(
                key=lambda track: self._sort_value(track, collection.sort_by),
                reverse=collection.sort_order == "desc",
            )
        except (AttributeError, TypeError, ValueError) as error:
            logger.warning("Smart collection query failed: %s", error)
            return {"ok": False, "error": str(error), "items": [], "total": 0}
        return {
            "ok": True,
            "items": matches[safe_offset:safe_offset + safe_limit],
            "total": len(matches),
            "limit": safe_limit,
            "offset": safe_offset,
            "collection": asdict(collection),
        }

    def query_collection_page(
        self,
        collection_id: str,
        offset: int = 0,
        limit: int = 250,
    ) -> dict[str, Any]:
        """Compile collection rules to SQL and return one paginated page.

        Runs a COUNT plus a single LIMIT/OFFSET page against ``media_items`` so
        large collections no longer load every track into memory. The returned
        ``items`` mirror the minimal track shape consumed by the QML detail page.
        """
        collection = self._find(collection_id)
        if collection is None:
            return {"ok": False, "error": "NOT_FOUND", "items": [], "total": 0}
        if self._db is None or getattr(self._db, "conn", None) is None:
            return {"ok": False, "error": "DATABASE_UNAVAILABLE", "items": [], "total": 0}
        safe_limit = max(1, min(1000, int(limit)))
        safe_offset = max(0, int(offset))
        try:
            where_sql, params = self._compile_rules(collection)
        except (TypeError, ValueError) as error:
            return {"ok": False, "error": str(error), "items": [], "total": 0}
        conn = self._db.conn
        try:
            total_row = conn.execute(
                f"SELECT COUNT(*) FROM media_items m "
                f"WHERE m.deleted_at IS NULL AND ({where_sql})",
                params,
            ).fetchone()
            total = int(total_row[0]) if total_row else 0
            sort_column = _SQL_SORT_COLUMN.get(collection.sort_by, _SQL_SORT_COLUMN["title"])
            order = "ASC" if collection.sort_order == "asc" else "DESC"
            page_sql = (
                "SELECT m.id, m.filepath, m.title, m.artist, m.album, m.album_key, "
                "m.duration, m.ext, m.year, m.genre "
                "FROM media_items m "
                f"WHERE m.deleted_at IS NULL AND ({where_sql}) "
                f"ORDER BY {sort_column} {order}, m.id ASC "
                "LIMIT ? OFFSET ?"
            )
            rows = conn.execute(page_sql, [*params, safe_limit, safe_offset]).fetchall()
        except Exception as error:
            logger.warning("Smart collection SQL page failed: %s", error)
            return {"ok": False, "error": str(error), "items": [], "total": 0}
        items = [self._row_to_collection_item(row) for row in rows]
        return {
            "ok": True,
            "items": items,
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
            "collection": asdict(collection),
        }

    @staticmethod
    def _row_to_collection_item(row: Any) -> dict[str, Any]:
        """Map a paginated collection row to the minimal QML track shape."""
        album_key = row[5] or ""
        return {
            "track_id": row[0],
            "filepath": row[1] or "",
            "title": row[2] or "",
            "artist": row[3] or "",
            "album": row[4] or "",
            "album_key": album_key,
            "cover_key": album_key,
            "duration": float(row[6] or 0),
            "format": str(row[7] or "").lstrip("."),
            "year": int(row[8] or 0),
            "genre": row[9] or "",
        }

    def _compile_rules(self, collection: SmartCollection) -> tuple[str, list[Any]]:
        """Compile a collection's rules into a SQL predicate and bound params."""
        fragments: list[str] = []
        params: list[Any] = []
        for rule in collection.rules:
            fragment, rule_params = self._compile_rule(rule)
            fragments.append(fragment)
            params.extend(rule_params)
        if not fragments:
            return "1=1", []
        joiner = " AND " if collection.logic == "AND" else " OR "
        return joiner.join(f"({fragment})" for fragment in fragments), params

    @classmethod
    def _compile_rule(cls, rule: CollectionRule) -> tuple[str, list[Any]]:
        kind, column = _SQL_FIELD[rule.field]
        if kind == "numeric":
            return cls._compile_numeric_rule(column, rule.operator, rule.value)
        return cls._compile_text_rule(column, rule.operator, rule.value, is_format=kind == "format")

    @classmethod
    def _compile_text_rule(
        cls, column: str, operator: str, value: Any, *, is_format: bool
    ) -> tuple[str, list[Any]]:
        text_value = str(value)
        target = column if is_format else f"LOWER(COALESCE({column}, ''))"
        if operator == "eq":
            return f"{target} = LOWER(?)", [text_value]
        if operator == "neq":
            return f"{target} != LOWER(?)", [text_value]
        if operator == "contains":
            pattern = f"%{_escape_like(text_value.lower())}%"
            return f"{target} LIKE ? ESCAPE '\\'", [pattern]
        return "1=0", []

    @classmethod
    def _compile_numeric_rule(
        cls, column: str, operator: str, value: Any
    ) -> tuple[str, list[Any]]:
        base = f"CAST(COALESCE({column}, 0) AS REAL)"
        if operator == "between":
            bounds = cls._normalize_between_bounds(value)
            if bounds is None:
                return "1=0", []
            return f"{base} BETWEEN ? AND ?", [bounds[0], bounds[1]]
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "1=0", []
        symbols = {"eq": "=", "neq": "!=", "gt": ">", "lt": "<", "gte": ">=", "lte": "<="}
        symbol = symbols.get(operator)
        if symbol is None:
            return "1=0", []
        return f"{base} {symbol} ?", [number]

    @staticmethod
    def _normalize_between_bounds(value: Any) -> tuple[float, float] | None:
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",", 1)]
        elif isinstance(value, (list, tuple)):
            parts = list(value)
        else:
            return None
        if len(parts) != 2:
            return None
        try:
            return float(parts[0]), float(parts[1])
        except (TypeError, ValueError):
            return None

    def _fetch_all_tracks(self) -> list[dict[str, Any]]:
        total = max(0, int(self._qs.count_tracks()))
        tracks: list[dict[str, Any]] = []
        for offset in range(0, total, _FETCH_BATCH_SIZE):
            page = self._qs.fetch_tracks(offset=offset, limit=min(_FETCH_BATCH_SIZE, total - offset))
            tracks.extend(item for item in page if isinstance(item, dict))
            if len(page) < min(_FETCH_BATCH_SIZE, total - offset):
                break
        return tracks

    def _find(self, collection_id: str) -> SmartCollection | None:
        return next(
            (collection for collection in self._collections if collection.id == collection_id),
            None,
        )

    @classmethod
    def _from_dict(cls, entry: Any) -> SmartCollection:
        if not isinstance(entry, dict):
            raise TypeError("Collection record must be a mapping")
        collection_id = str(entry.get("id") or "").strip()
        name = str(entry.get("name") or "").strip()
        rules = cls._normalize_rules(entry.get("rules", []))
        if not collection_id or not name or not rules:
            raise ValueError("Collection record is incomplete")
        return SmartCollection(
            id=collection_id,
            name=name,
            rules=rules,
            logic=cls._normalize_logic(entry.get("logic", "AND")),
            sort_by=cls._normalize_sort_by(entry.get("sort_by", "title")),
            sort_order=cls._normalize_sort_order(entry.get("sort_order", "asc")),
            icon=str(entry.get("icon") or "playlists"),
            created=float(entry.get("created") or 0.0),
            updated=float(entry.get("updated") or 0.0),
        )

    @staticmethod
    def _normalize_rules(rules: Any) -> list[CollectionRule]:
        if not isinstance(rules, list):
            raise TypeError("INVALID_RULES")
        normalized: list[CollectionRule] = []
        for rule in rules:
            if isinstance(rule, CollectionRule):
                candidate = rule
            elif isinstance(rule, dict):
                candidate = CollectionRule(
                    field=str(rule.get("field") or "").lower(),
                    operator=str(rule.get("operator") or "").lower(),
                    value=rule.get("value"),
                )
            else:
                raise TypeError("INVALID_RULE")
            if candidate.field not in _FIELDS or candidate.operator not in _OPERATORS:
                raise ValueError("INVALID_RULE")
            if candidate.value in (None, ""):
                raise ValueError("INVALID_RULE")
            normalized.append(candidate)
        return normalized

    @staticmethod
    def _normalize_logic(logic: Any) -> str:
        normalized = str(logic or "AND").upper()
        if normalized not in {"AND", "OR"}:
            raise ValueError("INVALID_LOGIC")
        return normalized

    @staticmethod
    def _normalize_sort_by(value: Any) -> str:
        normalized = str(value or "title").lower()
        if normalized not in _FIELDS:
            raise ValueError("INVALID_SORT_FIELD")
        return normalized

    @staticmethod
    def _normalize_sort_order(value: Any) -> str:
        normalized = str(value or "asc").lower()
        if normalized not in {"asc", "desc"}:
            raise ValueError("INVALID_SORT_ORDER")
        return normalized

    @classmethod
    def _matches(cls, track: dict[str, Any], collection: SmartCollection) -> bool:
        results = [cls._matches_rule(track, rule) for rule in collection.rules]
        return all(results) if collection.logic == "AND" else any(results)

    @staticmethod
    def _matches_rule(track: dict[str, Any], rule: CollectionRule) -> bool:
        raw_value = track.get(_TRACK_FIELDS.get(rule.field, rule.field))
        if rule.field == "format":
            raw_value = str(raw_value or "").lstrip(".")
        if rule.field in _NUMERIC_FIELDS:
            try:
                actual = float(raw_value or 0)
            except (TypeError, ValueError):
                return False
            if rule.operator == "between":
                bounds = rule.value
                if isinstance(bounds, str):
                    bounds = [part.strip() for part in bounds.split(",", 1)]
                if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                    return False
                try:
                    return float(bounds[0]) <= actual <= float(bounds[1])
                except (TypeError, ValueError):
                    return False
            try:
                expected = float(rule.value)
            except (TypeError, ValueError):
                return False
            comparisons = {
                "eq": actual == expected,
                "neq": actual != expected,
                "gt": actual > expected,
                "lt": actual < expected,
                "gte": actual >= expected,
                "lte": actual <= expected,
            }
            return comparisons.get(rule.operator, False)

        actual_text = str(raw_value or "").casefold()
        expected_text = str(rule.value).casefold()
        if rule.operator == "contains":
            return expected_text in actual_text
        if rule.operator == "eq":
            return actual_text == expected_text
        if rule.operator == "neq":
            return actual_text != expected_text
        return False

    @staticmethod
    def _sort_value(track: dict[str, Any], field_name: str) -> tuple[int, Any]:
        value = track.get(_TRACK_FIELDS.get(field_name, field_name))
        if field_name in _NUMERIC_FIELDS:
            try:
                return 0, float(value or 0)
            except (TypeError, ValueError):
                return 1, 0.0
        return (0, str(value or "").casefold())
