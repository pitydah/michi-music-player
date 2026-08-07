"""Favorites keep a single canonical identity (FASE 4, P0).

Tracks are keyed by track_uid — the service never derives identity from
paths or path hashes. Bridges never write favorites SQL. Group unfavorites
delete only inherited rows (origin + parent_entity), never direct favorites.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRIDGES_DIR = PROJECT_ROOT / "ui_qml_bridge"
FAVORITE_SERVICE = PROJECT_ROOT / "core" / "favorite_service.py"


def _bridge_files():
    return sorted(BRIDGES_DIR.glob("*.py"))


def test_no_bridge_writes_favorites_sql() -> None:
    """Bridges never INSERT/DELETE favorites — the service owns that SQL."""
    offenders = []
    for path in _bridge_files():
        source = path.read_text(encoding="utf-8")
        if re.search(r"\bINSERT\s+INTO\s+favorites\b", source, re.IGNORECASE):
            offenders.append(f"{path.name}:INSERT INTO favorites")
        if re.search(r"\bDELETE\s+FROM\s+favorites\b", source, re.IGNORECASE):
            offenders.append(f"{path.name}:DELETE FROM favorites")
    assert offenders == [], f"bridges writing favorites SQL: {offenders}"


def test_favorite_service_has_no_path_hash_identity() -> None:
    """Identity comes from track_uid, never from hashing paths."""
    source = FAVORITE_SERVICE.read_text(encoding="utf-8")
    assert "hashlib" not in source
    assert "hash(" not in source


def test_track_favorites_use_canonical_track_uid() -> None:
    """Track writes key entity_id on track_uid with a single canonical row."""
    source = FAVORITE_SERVICE.read_text(encoding="utf-8")
    assert "track_uid" in source
    assert "ON CONFLICT(track_id)" in source
    assert "has no track_uid; canonical favorite" in source
    assert "migrated_legacy" in source
    assert "READBACK_MISMATCH" in source


def test_group_unfavorite_deletes_only_inherited() -> None:
    """Group cleanup targets origin + parent_entity; no legacy per-track purge."""
    source = FAVORITE_SERVICE.read_text(encoding="utf-8")
    assert "origin = ? AND parent_entity = ?" in source
    for origin in ("inherited_album", "inherited_artist", "inherited_genre"):
        assert origin in source
    assert "track_id IN (" not in source
