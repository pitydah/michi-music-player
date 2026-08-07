"""LibraryMutationService — canonical library mutation authority (ADR-002).

Owns ALL library mutations: metadata field edits (legacy dict surface kept for
MetadataService/editor consumers), favorites (delegated to FavoriteService with
canonical entity identity), and track removal from the library. Every mutation
commits, performs a readback and emits EventBus events (ADR-005).
"""
from __future__ import annotations

import logging
import time
from typing import Any

from core.models.operation_result import OperationResult

logger = logging.getLogger("michi.library_mutation")

EVENT_METADATA_UPDATED = "library.metadata.updated"
EVENT_TRACKS_REMOVED = "library.tracks.removed"


class LibraryMutationService:
    def __init__(self, db: Any | None = None, event_bus: Any | None = None,
                 favorite_service: Any | None = None,
                 query_service: Any | None = None):
        self._db = db
        self._eb = event_bus
        self._fav = favorite_service
        self._qs = query_service

    # ── favorites ────────────────────────────────────────────────────────

    def _favorite_service(self) -> Any:
        # P0 FASE 10: no lazy construction — the canonical FavoriteService is
        # injected by composition; callers handle None explicitly.
        return self._fav

    def set_favorite(self, entity_type: str, entity_id: str,
                     public_ref: str = "", favorite: bool = True,
                     source: str = "ui") -> OperationResult:
        """Set favorite state for a canonical entity (track/album/artist/...)."""
        if self._fav is None:
            return OperationResult.fail("FAVORITE_SERVICE_UNAVAILABLE",
                                        "FavoriteService not injected")
        return self._fav.set_favorite(
            entity_type, entity_id, public_ref, favorite, source)

    def toggle_favorite(self, entity_type: str, entity_id: str,
                        public_ref: str = "", source: str = "ui") -> OperationResult:
        if self._fav is None:
            return OperationResult.fail("FAVORITE_SERVICE_UNAVAILABLE",
                                        "FavoriteService not injected")
        return self._fav.toggle_favorite(
            entity_type, entity_id, public_ref, source)

    def set_track_favorites_bulk(self, track_ids: list[int],
                                 favorite: bool,
                                 source: str = "ui",
                                 atomic: bool = False) -> OperationResult:
        if self._fav is None:
            return OperationResult.fail("FAVORITE_SERVICE_UNAVAILABLE",
                                        "FavoriteService not injected")
        return self._fav.set_track_favorites_bulk(
            track_ids, favorite, source, atomic)

    # ── metadata edits (legacy dict surface, kept for editor consumers) ──

    def update_metadata(self, track_id: int, data: dict) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            fields = []
            values = []
            for k, v in data.items():
                if k in ("title", "artist", "album", "genre", "year", "track", "disc"):
                    fields.append(f"{k}=?")
                    values.append(v)
            if not fields:
                return {"ok": False, "error": "NO_FIELDS"}
            values.append(track_id)
            with self._db.conn:
                self._db.conn.execute(
                    f"UPDATE media_items SET {','.join(fields)} WHERE id=?",
                    values,
                )
            self._emit_metadata(track_id, fields, values)
            return {"ok": True, "updated": 1}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _emit_metadata(self, track_id: int, fields: list[str],
                       values: list[Any]) -> None:
        if self._eb is None or not hasattr(self._eb, "emit"):
            return
        try:
            self._eb.emit(EVENT_METADATA_UPDATED, {
                "track_id": track_id,
                "fields": [f.rstrip("=?") for f in fields],
            })
        except Exception as error:  # noqa: BLE001
            logger.debug("metadata event emit failed: %s", error)

    def batch_update(self, updates: list[dict]) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        ok = 0
        fail = 0
        for item in updates:
            result = self.update_metadata(item.get("track_id"), item.get("data", {}))
            if result.get("ok"):
                ok += 1
            else:
                fail += 1
        return {"ok": fail == 0, "updated": ok, "failed": fail}

    def update_media_fields(self, track_id: int, data: dict) -> OperationResult:
        """Canonical multi-field metadata update with readback verification.

        Supports every editable ``media_items`` column; each field update is
        committed and then read back to confirm the side effect before the
        result reports success (ADR-005). Used by the metadata editor.
        """
        if not isinstance(data, dict) or not data:
            return OperationResult.fail("NO_FIELDS", "No fields to update")
        if not self._db:
            return OperationResult.fail("INFRASTRUCTURE_UNAVAILABLE",
                                        "Library database unavailable")
        if not track_id:
            return OperationResult.fail("INVALID_TRACK_ID",
                                        "track_id must be provided")
        editable = getattr(self._db, "_EDITABLE_FIELDS", frozenset())
        updates = {k: v for k, v in data.items() if k in editable}
        if not updates:
            return OperationResult.fail("NO_FIELDS",
                                        "None of the requested fields are editable")
        try:
            with self._db.conn:
                for field, value in updates.items():
                    self._db.conn.execute(
                        f"UPDATE media_items SET {field}=? WHERE id=?",
                        (value, track_id),
                    )
        except Exception as error:  # noqa: BLE001
            logger.exception("update_media_fields failed")
            return OperationResult.fail("DB_UPDATE_FAILED", str(error))

        applied = []
        for field, value in updates.items():
            try:
                row = self._db.conn.execute(
                    f"SELECT {field} FROM media_items WHERE id=?",
                    (track_id,),
                ).fetchone()
            except Exception:  # noqa: BLE001
                row = None
            actual = str(row[0]) if row and row[0] is not None else ""
            if str(actual) == str(value):
                applied.append(field)
            else:
                logger.warning(
                    "readback mismatch for track %d field %s: expected %r, got %r",
                    track_id, field, value, actual,
                )

        self._emit_metadata(track_id, [f"{f}=" for f in updates],
                            list(updates.values()))
        if len(applied) != len(updates):
            return OperationResult.fail(
                "READBACK_MISMATCH",
                f"{len(updates) - len(applied)} field(s) did not verify after write",
                recoverable=True,
            )
        return OperationResult.success({
            "track_id": track_id,
            "updated": len(applied),
            "fields": applied,
            "readback_verified": True,
        })

    # ── track removal ────────────────────────────────────────────────────

    def remove_tracks_from_library(self, track_ids: list[int],
                                   source: str = "ui") -> OperationResult:
        """Soft-delete tracks from the library (keeps history/playlists)."""
        if not isinstance(track_ids, list) or not track_ids:
            return OperationResult.fail("INVALID_TRACK_IDS",
                                        "Track ids must be a non-empty list")
        if not self._db:
            return OperationResult.fail("INFRASTRUCTURE_UNAVAILABLE",
                                        "Library database unavailable")
        unique_ids = list(dict.fromkeys(int(t) for t in track_ids))
        placeholders = ", ".join("?" for _ in unique_ids)
        try:
            with self._db.conn:
                cursor = self._db.conn.execute(
                    f"UPDATE media_items SET deleted_at = ? "
                    f"WHERE deleted_at IS NULL AND id IN ({placeholders})",
                    [time.time()] + unique_ids,
                )
            removed = max(0, cursor.rowcount)
        except Exception as error:  # noqa: BLE001
            logger.exception("remove_tracks_from_library failed")
            return OperationResult.fail("REMOVE_FAILED", str(error))

        remaining = 0
        try:
            row = self._db.conn.execute(
                f"SELECT COUNT(*) FROM media_items "
                f"WHERE deleted_at IS NULL AND id IN ({placeholders})",
                unique_ids,
            ).fetchone()
            remaining = int(row[0]) if row else 0
        except Exception:  # noqa: BLE001
            remaining = 0

        if self._eb is not None and hasattr(self._eb, "emit"):
            try:
                self._eb.emit(EVENT_TRACKS_REMOVED, {
                    "track_ids": unique_ids,
                    "removed": removed,
                    "source": source,
                })
            except Exception as error:  # noqa: BLE001
                logger.debug("tracks-removed event failed: %s", error)

        if removed == 0:
            return OperationResult.fail("NOT_FOUND", "No active tracks removed")
        return OperationResult.success({
            "count": removed,
            "track_ids": unique_ids,
            "remaining_active": remaining,
        })

    # ── lifecycle ────────────────────────────────────────────────────────

    def health(self) -> dict:
        fav = self._favorite_service()
        return {
            "available": self._db is not None,
            "favorites": fav.health() if fav is not None else {"available": False},
        }

    def shutdown(self) -> None:
        # favorite_service lifecycle is owned by the container (MANAGED); never
        # cascade shutdown here or the container shuts it down twice.
        self._db = None
        self._eb = None
        self._fav = None
