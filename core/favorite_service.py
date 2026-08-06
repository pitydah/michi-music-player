"""FavoriteService — canonical favorites with entity identity (ADR-002/003).

Canonical identity is the triple ``(entity_type, entity_id, public_ref)``:
entity_type is one of ``track|album|artist|playlist|radio|genre``, entity_id is
a stable id (``track_uid`` for tracks where available, album_key for albums,
artist name for artists), and public_ref is the UI-facing reference.

The legacy ``track_id`` column is kept as a backward-compatible surface:
track favorites store the filepath there so the historical favorites filter
(``filepath IN (SELECT track_id FROM favorites)``) keeps working, and rows
created before the S3 migration are read back through their filepath.
Group favorites (album/artist/playlist/radio) store one canonical row with
``track_id = "<type>:<id>"``; unsetting them also cleans the legacy
per-track rows of the group so old data does not linger.

Every mutation commits, performs a readback and emits EventBus events
(ADR-005): ``favorite.set`` / ``favorite.unset`` with the entity payload.
"""
from __future__ import annotations

import logging
from typing import Any

from core.models.operation_result import OperationResult

logger = logging.getLogger("michi.favorites")

VALID_ENTITY_TYPES = ("track", "album", "artist", "playlist", "radio", "genre")

EVENT_FAVORITE_SET = "favorite.set"
EVENT_FAVORITE_UNSET = "favorite.unset"
EVENT_FAVORITE_BULK = "favorite.bulk"


class FavoriteService:
    """Owns all favorite state with canonical entity identity."""

    def __init__(self, db: Any | None = None, event_bus: Any | None = None):
        self._db = db
        self._eb = event_bus

    # ── internal helpers ────────────────────────────────────────────────

    def _can(self) -> bool:
        return self._db is not None and hasattr(self._db, "conn")

    def _emit(self, event: str, payload: dict) -> None:
        if self._eb is None or not hasattr(self._eb, "emit"):
            return
        try:
            self._eb.emit(event, payload)
        except Exception as error:  # noqa: BLE001 — events never break mutations
            logger.debug("FavoriteService event %s failed: %s", event, error)

    def _payload(self, entity_type: str, entity_id: str,
                 public_ref: str, favorite: bool) -> dict:
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "public_ref": public_ref or "",
            "favorite": favorite,
        }

    def _resolve_track(self, entity_id: str, public_ref: str) -> tuple[str, str] | None:
        """Resolve ``(filepath, canonical_id)`` for a track entity.

        ``entity_id`` may be a track_uid, a numeric media_items id (as string)
        or a filepath; ``public_ref`` may carry ``track_<id>``.
        """
        if not self._can():
            return None
        sql = (
            "SELECT id, filepath, track_uid FROM media_items "
            "WHERE deleted_at IS NULL AND "
            "(track_uid = ? OR filepath = ? OR CAST(id AS TEXT) = ?) LIMIT 1"
        )
        params = [entity_id or "", entity_id or "", entity_id or ""]
        if public_ref and public_ref.startswith("track_"):
            ref_id = public_ref[len("track_"):]
            if ref_id.isdigit():
                params.append(ref_id)
                sql = (
                    "SELECT id, filepath, track_uid FROM media_items "
                    "WHERE deleted_at IS NULL AND "
                    "(track_uid = ? OR filepath = ? OR CAST(id AS TEXT) = ? "
                    "OR CAST(id AS TEXT) = ?) LIMIT 1"
                )
        row = self._db.conn.execute(sql, params).fetchone()
        if not row or not row[1]:
            return None
        rid, filepath, track_uid = int(row[0]), row[1], row[2] or ""
        canonical = track_uid or str(rid)
        return filepath, canonical

    def _legacy_group_filepaths(self, entity_type: str, entity_id: str) -> list[str]:
        """Filepaths of the group tracks for legacy per-track cleanup."""
        if not self._can():
            return []
        if entity_type == "album":
            where = "COALESCE(NULLIF(album_key, ''), album, '') = ? COLLATE NOCASE"
            params: tuple[Any, ...] = (entity_id,)
        elif entity_type == "artist":
            where = "(artist = ? COLLATE NOCASE OR albumartist = ? COLLATE NOCASE)"
            params = (entity_id, entity_id)
        elif entity_type == "genre":
            where = "genre = ? COLLATE NOCASE"
            params = (entity_id,)
        else:
            return []
        try:
            rows = self._db.conn.execute(
                f"SELECT filepath FROM media_items "
                f"WHERE deleted_at IS NULL AND {where}",
                params,
            ).fetchall()
            return [r[0] for r in rows if r[0]]
        except Exception as error:  # noqa: BLE001
            logger.debug("legacy group filepaths failed: %s", error)
            return []

    # ── reads ────────────────────────────────────────────────────────────

    def is_favorite(self, entity_type: str, entity_id: str) -> bool:
        """True when the entity is favorited (canonical or legacy identity)."""
        if entity_type not in VALID_ENTITY_TYPES or not entity_id:
            return False
        if not self._can():
            return False
        if entity_type == "track":
            row = self._db.conn.execute(
                "SELECT 1 FROM favorites WHERE entity_type = 'track' "
                "AND (entity_id = ? OR track_id = ?) LIMIT 1",
                (entity_id, entity_id),
            ).fetchone()
            return row is not None
        row = self._db.conn.execute(
            "SELECT 1 FROM favorites WHERE entity_type = ? AND entity_id = ? LIMIT 1",
            (entity_type, entity_id),
        ).fetchone()
        return row is not None

    def list_favorites(self, entity_type: str | None = None) -> list[dict]:
        if not self._can():
            return []
        sql = ("SELECT track_id, entity_type, entity_id, public_ref, source "
               "FROM favorites")
        params: tuple[Any, ...] = ()
        if entity_type in VALID_ENTITY_TYPES:
            sql += " WHERE entity_type = ?"
            params = (entity_type,)
        try:
            rows = self._db.conn.execute(sql + " ORDER BY created_at DESC",
                                         params).fetchall()
            return [
                {"track_id": r[0] or "", "entity_type": r[1] or "track",
                 "entity_id": r[2] or "", "public_ref": r[3] or "",
                 "source": r[4] or "ui"}
                for r in rows
            ]
        except Exception as error:  # noqa: BLE001
            logger.debug("list_favorites failed: %s", error)
            return []

    def counts(self) -> dict:
        counts: dict[str, int] = {}
        if not self._can():
            return {"total": 0}
        try:
            for row in self._db.conn.execute(
                "SELECT entity_type, COUNT(*) FROM favorites GROUP BY entity_type"
            ):
                counts[str(row[0])] = int(row[1])
        except Exception as error:  # noqa: BLE001
            logger.debug("favorite counts failed: %s", error)
        return {"total": sum(counts.values()), **counts}

    # ── writes ───────────────────────────────────────────────────────────

    def set_favorite(self, entity_type: str, entity_id: str,
                     public_ref: str = "", favorite: bool = True,
                     source: str = "ui") -> OperationResult:
        """Set the favorite state of one entity with readback."""
        if entity_type not in VALID_ENTITY_TYPES:
            return OperationResult.fail("INVALID_ENTITY_TYPE",
                                        f"Unknown favorite entity type '{entity_type}'")
        if not entity_id:
            return OperationResult.fail("EMPTY_ENTITY_ID",
                                        "Favorite requires a non-empty entity id")
        if not self._can():
            return OperationResult.fail("INFRASTRUCTURE_UNAVAILABLE",
                                        "Favorites database unavailable")

        try:
            if entity_type == "track":
                resolved = self._resolve_track(entity_id, public_ref)
                if resolved is None:
                    return OperationResult.fail("NOT_FOUND",
                                                f"Track '{entity_id}' not found in library")
                filepath, canonical_id = resolved
                legacy_key = filepath
                ref = public_ref or f"track:{canonical_id}"
                if favorite:
                    self._db.conn.execute(
                        "INSERT OR IGNORE INTO favorites "
                        "(track_id, entity_type, entity_id, public_ref, source) "
                        "VALUES (?, 'track', ?, ?, ?)",
                        (legacy_key, canonical_id, ref, source),
                    )
                else:
                    self._db.conn.execute(
                        "DELETE FROM favorites WHERE entity_type = 'track' "
                        "AND (entity_id = ? OR track_id = ?)",
                        (canonical_id, legacy_key),
                    )
            else:
                legacy_key = f"{entity_type}:{entity_id}"
                ref = public_ref or legacy_key
                if favorite:
                    self._db.conn.execute(
                        "INSERT OR IGNORE INTO favorites "
                        "(track_id, entity_type, entity_id, public_ref, source) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (legacy_key, entity_type, entity_id, ref, source),
                    )
                else:
                    self._db.conn.execute(
                        "DELETE FROM favorites WHERE entity_type = ? AND entity_id = ?",
                        (entity_type, entity_id),
                    )
                    legacy_paths = self._legacy_group_filepaths(entity_type, entity_id)
                    if legacy_paths:
                        placeholders = ", ".join("?" for _ in legacy_paths)
                        self._db.conn.execute(
                            f"DELETE FROM favorites WHERE entity_type = 'track' "
                            f"AND track_id IN ({placeholders})",
                            legacy_paths,
                        )
            self._db.conn.commit()
        except Exception as error:  # noqa: BLE001
            logger.exception("set_favorite(%s, %s) failed", entity_type, entity_id)
            return OperationResult.fail("FAVORITE_FAILED", str(error))

        readback = self.is_favorite(entity_type, entity_id)
        self._emit(
            EVENT_FAVORITE_SET if readback else EVENT_FAVORITE_UNSET,
            self._payload(entity_type, entity_id, public_ref or "", readback),
        )
        return OperationResult.success({
            **self._payload(entity_type, entity_id, public_ref or "", readback),
        })

    def toggle_favorite(self, entity_type: str, entity_id: str,
                        public_ref: str = "", source: str = "ui") -> OperationResult:
        return self.set_favorite(entity_type, entity_id, public_ref,
                                 favorite=not self.is_favorite(entity_type, entity_id),
                                 source=source)

    def set_track_favorites_bulk(self, track_ids: list[int],
                                 favorite: bool,
                                 source: str = "ui") -> OperationResult:
        """Set favorite state for many tracks in one transaction."""
        if not isinstance(track_ids, list) or not track_ids:
            return OperationResult.fail("INVALID_TRACK_IDS",
                                        "Track ids must be a non-empty list")
        if not self._can():
            return OperationResult.fail("INFRASTRUCTURE_UNAVAILABLE",
                                        "Favorites database unavailable")
        unique_ids = list(dict.fromkeys(int(t) for t in track_ids))
        placeholders = ", ".join("?" for _ in unique_ids)
        try:
            rows = self._db.conn.execute(
                "SELECT id, filepath, track_uid FROM media_items "
                f"WHERE deleted_at IS NULL AND id IN ({placeholders})",
                unique_ids,
            ).fetchall()
            by_id = {int(r[0]): (r[1] or "", r[2] or "") for r in rows}
            entries = [
                (filepath, uid or str(tid), f"track_{tid}")
                for tid in unique_ids
                for (filepath, uid) in [by_id[tid]]
                if tid in by_id and filepath
            ]
            if not entries:
                return OperationResult.fail("NOT_FOUND",
                                            "No matching tracks in library")
            if favorite:
                self._db.conn.executemany(
                    "INSERT OR IGNORE INTO favorites "
                    "(track_id, entity_type, entity_id, public_ref, source) "
                    "VALUES (?, 'track', ?, ?, ?)",
                    [(fp, uid, ref, source) for fp, uid, ref in entries],
                )
            else:
                filepaths = [fp for fp, _uid, _ref in entries]
                uids = [uid for _fp, uid, _ref in entries]
                fp_placeholders = ", ".join("?" for _ in filepaths)
                uid_placeholders = ", ".join("?" for _ in uids)
                self._db.conn.execute(
                    f"DELETE FROM favorites WHERE entity_type = 'track' AND ("
                    f"track_id IN ({fp_placeholders})"
                    f" OR entity_id IN ({uid_placeholders}))",
                    filepaths + uids,
                )
            self._db.conn.commit()
        except Exception as error:  # noqa: BLE001
            logger.exception("set_track_favorites_bulk failed")
            return OperationResult.fail("FAVORITE_FAILED", str(error))

        readback = self._bulk_readback(unique_ids)
        self._emit(EVENT_FAVORITE_BULK, {
            "count": len(entries),
            "favorite": favorite,
            "track_ids": unique_ids,
            "total_favorites": readback,
        })
        return OperationResult.success({
            "count": len(entries),
            "favorite": favorite,
            "total_favorites": readback,
        })

    def _bulk_readback(self, track_ids: list[int]) -> int:
        if not self._can():
            return 0
        placeholders = ", ".join("?" for _ in track_ids)
        try:
            row = self._db.conn.execute(
                "SELECT COUNT(*) FROM favorites WHERE entity_type = 'track' "
                f"AND entity_id IN (SELECT COALESCE(NULLIF(track_uid, ''), "
                f"CAST(id AS TEXT)) FROM media_items WHERE id IN ({placeholders}))",
                track_ids,
            ).fetchone()
            return int(row[0]) if row else 0
        except Exception as error:  # noqa: BLE001
            logger.debug("favorite bulk readback failed: %s", error)
            return 0

    # ── lifecycle ────────────────────────────────────────────────────────

    def health(self) -> dict:
        return {
            "available": self._can(),
            "counts": self.counts() if self._can() else {"total": 0},
        }

    def shutdown(self) -> None:
        self._db = None
        self._eb = None
