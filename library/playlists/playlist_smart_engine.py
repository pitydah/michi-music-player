"""Playlist smart engine — rule-based smart playlists."""
from __future__ import annotations

import json
import logging
import time

from library.playlists.playlist_models import PlaylistSmartRule

logger = logging.getLogger("michi.smart_engine")

_OPERATORS = {
    "equals": lambda a, b: a == b,
    "not_equals": lambda a, b: a != b,
    "contains": lambda a, b: b.lower() in (a or "").lower(),
    "not_contains": lambda a, b: b.lower() not in (a or "").lower(),
    "greater_than": lambda a, b: (a or 0) > float(b),
    "less_than": lambda a, b: (a or 0) < float(b),
    "between": lambda a, b: _between(a, b),
    "in": lambda a, b: (a or "") in (b.split(",") if isinstance(b, str) else [b]),
    "not_in": lambda a, b: (a or "") not in (b.split(",") if isinstance(b, str) else [b]),
    "is_empty": lambda a, b: not a,
    "is_not_empty": lambda a, b: bool(a),
    "older_than_days": lambda a, b: _days_ago(a) > int(b),
    "newer_than_days": lambda a, b: _days_ago(a) < int(b),
}


def _between(value, bound_str: str) -> bool:
    try:
        parts = str(bound_str).split(",")
        lo, hi = float(parts[0]), float(parts[1])
        return lo <= (value or 0) <= hi
    except (ValueError, IndexError):
        return False


def _days_ago(value) -> int:
    if not value:
        return 99999
    try:
        return int((time.time() - float(value)) / 86400)
    except (TypeError, ValueError):
        return 99999


def evaluate_rules(rules_json: str, db_conn) -> list[int]:
    """Evaluate smart playlist rules against the media library.

    Returns list of track IDs matching all rules.
    """
    try:
        rules_data = json.loads(rules_json) if isinstance(rules_json, str) else rules_json
    except (json.JSONDecodeError, TypeError):
        return []

    if isinstance(rules_data, dict):
        rules_data = rules_data.get("rules", [])
    if isinstance(rules_data, str):
        try:
            rules_data = json.loads(rules_data)
        except json.JSONDecodeError:
            return []
    if not isinstance(rules_data, list):
        return []

    definitions = []
    for r in rules_data:
        if isinstance(r, dict):
            definitions.append(PlaylistSmartRule(
                field=r.get("field", ""),
                operator=r.get("op", r.get("operator", "equals")),
                value=r.get("value", ""),
            ))

    return _apply_rules(definitions, db_conn)


def _apply_rules(rules: list[PlaylistSmartRule], db_conn) -> list[int]:
    """Apply rules by building SQL queries incrementally."""
    if not rules:
        return []

    field_map = {
        "title": "m.title", "artist": "m.artist", "album": "m.album",
        "albumartist": "m.albumartist", "genre": "m.genre",
        "year": "m.year", "ext": "m.ext", "bit_depth": "m.bit_depth",
        "sample_rate": "m.sample_rate", "bitrate": "m.bitrate",
        "duration": "m.duration", "bpm": "m.bpm", "key": "m.key",
        "replaygain": "m.replaygain_track",
        "favorite": "f.track_id",
        "play_count": "COALESCE(h.cnt, 0)",
        "last_played": "MAX(h.played_at)",
        "track_uid": "m.track_uid",
        "content_hash": "m.content_hash",
    }

    joins = []
    wheres = []
    params = []

    for rule in rules:
        col = field_map.get(rule.field)
        if not col:
            logger.warning("Unknown smart rule field: %s", rule.field)
            continue

        op_fn = _OPERATORS.get(rule.operator)
        if not op_fn:
            continue

        if rule.field == "favorite":
            joins.append("LEFT JOIN favorites f ON f.track_id = CAST(m.id AS TEXT)")
            if rule.operator == "is_not_empty":
                wheres.append("f.track_id IS NOT NULL")
            else:
                wheres.append("f.track_id IS NULL")
            continue

        if rule.field in ("play_count", "last_played"):
            joins.append(
                "LEFT JOIN (SELECT track_id, COUNT(*) as cnt, MAX(played_at) as played_at "
                "FROM play_history GROUP BY track_id) h ON h.track_id = CAST(m.id AS TEXT)")

        if rule.operator in ("equals",):
            wheres.append(f"{col} = ?")
            params.append(rule.value)
        elif rule.operator == "contains":
            wheres.append(f"{col} LIKE ?")
            params.append(f"%{rule.value}%")
        elif rule.operator == "not_contains":
            wheres.append(f"{col} NOT LIKE ?")
            params.append(f"%{rule.value}%")
        elif rule.operator == "greater_than":
            wheres.append(f"{col} > ?")
            params.append(float(rule.value))
        elif rule.operator == "less_than":
            wheres.append(f"{col} < ?")
            params.append(float(rule.value))
        elif rule.operator in ("is_empty",):
            wheres.append(f"({col} IS NULL OR {col} = '')")
        elif rule.operator in ("is_not_empty",):
            wheres.append(f"({col} IS NOT NULL AND {col} != '')")

    if not wheres:
        all_query = "SELECT DISTINCT m.id FROM media_items m"
        for j in joins:
            all_query += f" {j}"
        return [r["id"] for r in db_conn.execute(all_query).fetchall()]

    sql = "SELECT DISTINCT m.id FROM media_items m"
    for j in joins:
        sql += f" {j}"
    sql += " WHERE " + " AND ".join(wheres)
    sql += " ORDER BY m.title COLLATE NOCASE"

    try:
        rows = db_conn.execute(sql, params).fetchall()
        return [r["id"] for r in rows]
    except Exception as e:
        logger.error("Smart rule SQL error: %s\nSQL: %s\nParams: %s", e, sql, params)
        return []


def preview_smart_playlist(rules_json: str, db_conn) -> list[int]:
    return evaluate_rules(rules_json, db_conn)


def create_smart_playlist(store, name: str, rules_json: str, description: str = ""):
    pid = store.create_playlist(name, description=description, is_smart=True, rules_json=rules_json)
    return pid


def refresh_smart_playlist(store, pid: int, db_conn) -> int:
    """Recalculate a smart playlist's tracks. Returns count of tracks."""
    pl = store.get_playlist(pid)
    if not pl or not pl.get("is_smart"):
        return 0
    rules_json = pl.get("rules_json", "")
    track_ids = evaluate_rules(rules_json, db_conn)
    store.clear_playlist(pid)
    for tid in track_ids:
        row = db_conn.execute(
            "SELECT filepath FROM media_items WHERE id=?", (tid,)
        ).fetchone()
        if row:
            store.add_track(pid, filepath=row["filepath"], track_id=tid, source="smart")
    return len(track_ids)


_CONVERSION_MAP = {
    "mix_popular": {"field": "play_count", "operator": "greater_than", "value": "10"},
    "mix_unplayed": {"field": "play_count", "operator": "equals", "value": "0"},
    "mix_favorites": {"field": "favorite", "operator": "is_not_empty", "value": ""},
    "mix_daily": {"field": "year", "operator": "greater_than", "value": "2000"},
    "flac_only": {"field": "ext", "operator": "equals", "value": "flac"},
    "hires": {"field": "sample_rate", "operator": "greater_than", "value": "48000"},
    "no_cover": {"field": "has_cover", "operator": "is_empty", "value": ""},
}


def convert_mix_to_playlist(store, db_conn, mix_key: str, name: str | None = None):
    """Convert a predefined mix rule into a saved smart playlist."""
    rule = _CONVERSION_MAP.get(mix_key)
    if not rule:
        return None
    rules_json = json.dumps({"rules": [rule]})
    pl_name = name or mix_key.replace("_", " ").title()
    pid = create_smart_playlist(store, pl_name, rules_json)
    count = refresh_smart_playlist(store, pid, db_conn)
    return {"pid": pid, "name": pl_name, "count": count}
