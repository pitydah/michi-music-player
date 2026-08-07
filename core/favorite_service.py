"""FavoriteService — canonical favorites with entity identity (ADR-002/003).

Canonical identity is the triple ``(entity_type, entity_id, public_ref)``:
entity_type is one of ``track|album|artist|playlist|radio|genre``, entity_id is
a stable id (``track_uid`` for tracks, album_key for albums, artist name for
artists), and public_ref is the UI-facing reference.

Track identity is canonical: ``entity_id`` for a track favorite is ALWAYS the
``track_uid``, never the filepath. A filepath lookup is accepted as a
documented legacy path: the track is resolved and the operation is re-keyed to
its ``track_uid`` (migration-9 provenance marks pre-existing rows as
``migrated_legacy``). A track without a ``track_uid`` is rejected with
NOT_FOUND — there is no silent filepath fallback in canonical operations.
Because identity is the uid, favorites survive path relocation.

The legacy ``track_id`` column is kept as a backward-compatible surface:
track favorites store the filepath there so the historical favorites filter
(``filepath IN (SELECT track_id FROM favorites)``) keeps working.

Group favorites carry inheritance: favoriting an album creates one direct row
(``origin='direct'``) plus one inherited row per track
(``origin='inherited_album'``, ``parent_entity=album_key``). Unfavoriting a
group deletes ONLY its inherited rows plus the direct group row — direct
track favorites inside the group are NEVER removed.

Every mutation commits, performs a readback and emits EventBus events
(ADR-005): ``favorite.set`` / ``favorite.unset`` with the entity payload.
When the readback disagrees with the requested state the mutation returns
``READBACK_MISMATCH`` with details instead of a blind success.
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

ORIGIN_DIRECT = "direct"
ORIGIN_INHERITED_ALBUM = "inherited_album"
ORIGIN_INHERITED_ARTIST = "inherited_artist"
ORIGIN_INHERITED_GENRE = "inherited_genre"
ORIGIN_MIGRATED_LEGACY = "migrated_legacy"

_INHERITED_ORIGINS = (
    ORIGIN_INHERITED_ALBUM,
    ORIGIN_INHERITED_ARTIST,
    ORIGIN_INHERITED_GENRE,
)

_INHERITED_ORIGIN_BY_GROUP = {
    "album": ORIGIN_INHERITED_ALBUM,
    "artist": ORIGIN_INHERITED_ARTIST,
    "genre": ORIGIN_INHERITED_GENRE,
}

_GROUP_WHERE = {
    "album": "COALESCE(NULLIF(album_key, ''), album, '') = ? COLLATE NOCASE",
    "artist": "(artist = ? COLLATE NOCASE OR albumartist = ? COLLATE NOCASE)",
    "genre": "genre = ? COLLATE NOCASE",
}

_BULK_STATUS_APPLIED = "applied"
_BULK_STATUS_ALREADY_SET = "already_set"
_BULK_STATUS_NOT_FOUND = "not_found"
_BULK_STATUS_FAILED = "failed"
_BULK_STATUS_ROLLED_BACK = "rolled_back"

_TRACK_UPSERT = (
    "INSERT INTO favorites "
    "(track_id, entity_type, entity_id, public_ref, source, origin, created_at) "
    "VALUES (?, 'track', ?, ?, ?, 'direct', strftime('%s','now')) "
    "ON CONFLICT(track_id) DO UPDATE SET "
    "entity_type='track', entity_id=excluded.entity_id, "
    "public_ref=excluded.public_ref, source=excluded.source, "
    "origin='direct', parent_entity=NULL"
)


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
        or a filepath (documented legacy path); ``public_ref`` may carry
        ``track_<id>``. The canonical id is ALWAYS the ``track_uid``: filepath
        lookups map to the uid so operations never key on paths. Returns None
        when no active row matches or the row has no ``track_uid``.
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
        _rid, filepath, track_uid = int(row[0]), row[1], row[2] or ""
        return filepath, track_uid

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
        sql = ("SELECT track_id, entity_type, entity_id, public_ref, source, "
               "origin, parent_entity FROM favorites")
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
                 "source": r[4] or "ui", "origin": r[5] or ORIGIN_DIRECT,
                 "parent_entity": r[6] or ""}
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
        """Set the favorite state of one entity with readback.

        Tracks are keyed by ``track_uid`` (canonical). Group entities
        (album/artist/genre) additionally create/remove inherited track rows
        with ``origin=inherited_*`` and ``parent_entity=<group id>``; group
        unfavorite never touches direct track favorites.
        """
        if entity_type not in VALID_ENTITY_TYPES:
            return OperationResult.fail("INVALID_ENTITY_TYPE",
                                        f"Unknown favorite entity type '{entity_type}'")
        if not entity_id:
            return OperationResult.fail("EMPTY_ENTITY_ID",
                                        "Favorite requires a non-empty entity id")
        if not self._can():
            return OperationResult.fail("INFRASTRUCTURE_UNAVAILABLE",
                                        "Favorites database unavailable")

        readback_id = entity_id
        try:
            if entity_type == "track":
                resolved = self._resolve_track(entity_id, public_ref)
                if resolved is None:
                    return OperationResult.fail("NOT_FOUND",
                                                f"Track '{entity_id}' not found in library")
                filepath, canonical_id = resolved
                if not canonical_id:
                    return OperationResult.fail(
                        "NOT_FOUND",
                        f"Track '{entity_id}' has no track_uid; canonical favorite "
                        "identity requires track_uid",
                    )
                readback_id = canonical_id
                ref = public_ref or f"track:{canonical_id}"
                if favorite:
                    self._db.conn.execute(
                        _TRACK_UPSERT,
                        (filepath, canonical_id, ref, source),
                    )
                else:
                    self._db.conn.execute(
                        "DELETE FROM favorites WHERE entity_type = 'track' "
                        "AND (entity_id = ? OR track_id = ?)",
                        (canonical_id, filepath),
                    )
            else:
                inherited_origin = _INHERITED_ORIGIN_BY_GROUP.get(entity_type)
                legacy_key = f"{entity_type}:{entity_id}"
                ref = public_ref or legacy_key
                if favorite:
                    self._db.conn.execute(
                        "INSERT OR IGNORE INTO favorites "
                        "(track_id, entity_type, entity_id, public_ref, source, "
                        "origin, created_at) "
                        "VALUES (?, ?, ?, ?, ?, 'direct', strftime('%s','now'))",
                        (legacy_key, entity_type, entity_id, ref, source),
                    )
                    if inherited_origin:
                        self._db.conn.execute(
                            "INSERT OR IGNORE INTO favorites "
                            "(track_id, entity_type, entity_id, public_ref, source, "
                            "origin, parent_entity, created_at) "
                            "SELECT filepath, 'track', track_uid, "
                            "'track_' || CAST(id AS TEXT), ?, ?, ?, "
                            "strftime('%s','now') "
                            "FROM media_items WHERE deleted_at IS NULL "
                            "AND track_uid != '' AND "
                            + _GROUP_WHERE[entity_type],
                            (source, inherited_origin, entity_id)
                            + (entity_id,) * _GROUP_WHERE[entity_type].count("?"),
                        )
                else:
                    self._db.conn.execute(
                        "DELETE FROM favorites WHERE entity_type = ? AND entity_id = ?",
                        (entity_type, entity_id),
                    )
                    if inherited_origin:
                        self._db.conn.execute(
                            "DELETE FROM favorites WHERE entity_type = 'track' "
                            "AND origin = ? AND parent_entity = ?",
                            (inherited_origin, entity_id),
                        )
            self._db.conn.commit()
        except Exception as error:  # noqa: BLE001
            logger.exception("set_favorite(%s, %s) failed", entity_type, entity_id)
            return OperationResult.fail("FAVORITE_FAILED", str(error))

        readback = self.is_favorite(entity_type, readback_id)
        self._emit(
            EVENT_FAVORITE_SET if readback else EVENT_FAVORITE_UNSET,
            self._payload(entity_type, readback_id, ref, readback),
        )
        payload = self._payload(entity_type, readback_id, ref, readback)
        if readback != favorite:
            payload["details"] = {
                "entity_type": entity_type,
                "entity_id": readback_id,
                "public_ref": ref,
                "requested": favorite,
                "effective": readback,
            }
            return OperationResult(
                ok=False, code="READBACK_MISMATCH",
                message=f"Favorite readback mismatch for {entity_type} "
                        f"'{readback_id}': requested={favorite} effective={readback}",
                data=payload,
            )
        return OperationResult.success(payload)

    def set_album_favorite(self, album_key: str, favorite: bool,
                           source: str = "ui") -> OperationResult:
        """Favorite an album: one direct row + inherited rows per track."""
        return self.set_favorite("album", album_key,
                                 f"album:{album_key}", favorite, source)

    def set_artist_favorite(self, artist_name: str, favorite: bool,
                            source: str = "ui") -> OperationResult:
        """Favorite an artist: one direct row + inherited rows per track."""
        return self.set_favorite("artist", artist_name,
                                 f"artist:{artist_name}", favorite, source)

    def set_genre_favorite(self, genre: str, favorite: bool,
                           source: str = "ui") -> OperationResult:
        """Favorite a genre: one direct row + inherited rows per track."""
        return self.set_favorite("genre", genre,
                                 f"genre:{genre}", favorite, source)

    def toggle_favorite(self, entity_type: str, entity_id: str,
                        public_ref: str = "", source: str = "ui") -> OperationResult:
        return self.set_favorite(entity_type, entity_id, public_ref,
                                 favorite=not self.is_favorite(entity_type, entity_id),
                                 source=source)

    def set_track_favorites_bulk(self, track_ids: list[int],
                                 favorite: bool,
                                 source: str = "ui",
                                 atomic: bool = False) -> OperationResult:
        """Set favorite state for many tracks; per-ID results, never aborts.

        Each id resolves to one of ``applied | already_set | not_found |
        failed``. A missing id (no active row or no ``track_uid``) is reported
        as ``not_found`` and the batch continues — a single bad id never
        aborts the batch. With ``atomic=True`` the first ``not_found``/``failed``
        id rolls the whole batch back (zero applied).
        """
        if not isinstance(track_ids, list) or not track_ids:
            return OperationResult.fail("INVALID_TRACK_IDS",
                                        "Track ids must be a non-empty list")
        if not self._can():
            return OperationResult.fail("INFRASTRUCTURE_UNAVAILABLE",
                                        "Favorites database unavailable")
        try:
            unique_ids = list(dict.fromkeys(int(t) for t in track_ids))
        except (TypeError, ValueError):
            return OperationResult.fail("INVALID_TRACK_IDS",
                                        "Track ids must be integers")
        placeholders = ", ".join("?" for _ in unique_ids)
        try:
            rows = self._db.conn.execute(
                "SELECT id, filepath, track_uid FROM media_items "
                f"WHERE deleted_at IS NULL AND id IN ({placeholders})",
                unique_ids,
            ).fetchall()
        except Exception as error:  # noqa: BLE001
            logger.exception("set_track_favorites_bulk failed")
            return OperationResult.fail("FAVORITE_FAILED", str(error))
        by_id = {int(r[0]): (r[1] or "", r[2] or "") for r in rows}
        results: dict[int, str] = {}
        pending: list[tuple[int, str, str]] = []
        for tid in unique_ids:
            filepath, uid = by_id.get(tid, ("", ""))
            if not filepath or not uid:
                results[tid] = _BULK_STATUS_NOT_FOUND
                continue
            pending.append((tid, filepath, uid))
        try:
            for tid, filepath, uid in pending:
                try:
                    results[tid] = self._apply_bulk_one(
                        tid, filepath, uid, favorite, source)
                except Exception as error:  # noqa: BLE001
                    logger.debug("bulk entry %s failed: %s", tid, error)
                    results[tid] = _BULK_STATUS_FAILED
                    if atomic:
                        self._db.conn.rollback()
                        return self._bulk_result(
                            self._mark_rolled_back(results), favorite, atomic)
            if atomic and any(
                results.get(tid) in (_BULK_STATUS_NOT_FOUND, _BULK_STATUS_FAILED)
                for tid in unique_ids
            ):
                self._db.conn.rollback()
                return self._bulk_result(
                    self._mark_rolled_back(results), favorite, atomic)
            self._db.conn.commit()
        except Exception as error:  # noqa: BLE001
            self._db.conn.rollback()
            logger.exception("set_track_favorites_bulk failed")
            return OperationResult.fail("FAVORITE_FAILED", str(error))

        return self._bulk_result(results, favorite, atomic)

    def _apply_bulk_one(self, tid: int, filepath: str, uid: str,
                        favorite: bool, source: str) -> str:
        """Apply one bulk entry; returns the per-ID status."""
        row = self._db.conn.execute(
            "SELECT origin FROM favorites WHERE entity_type = 'track' "
            "AND (entity_id = ? OR track_id = ?) LIMIT 1",
            (uid, filepath),
        ).fetchone()
        if favorite:
            if row is None:
                self._db.conn.execute(
                    _TRACK_UPSERT,
                    (filepath, uid, f"track_{tid}", source),
                )
                return _BULK_STATUS_APPLIED
            origin = row[0] or ORIGIN_DIRECT
            if origin in _INHERITED_ORIGINS:
                self._db.conn.execute(
                    "UPDATE favorites SET origin = 'direct', parent_entity = NULL "
                    "WHERE entity_type = 'track' AND entity_id = ?",
                    (uid,),
                )
                return _BULK_STATUS_APPLIED
            if origin == ORIGIN_MIGRATED_LEGACY:
                self._db.conn.execute(
                    "UPDATE favorites SET entity_id = ?, origin = 'direct', "
                    "parent_entity = NULL WHERE entity_type = 'track' "
                    "AND track_id = ?",
                    (uid, filepath),
                )
                return _BULK_STATUS_APPLIED
            return _BULK_STATUS_ALREADY_SET
        if row is None:
            return _BULK_STATUS_ALREADY_SET
        self._db.conn.execute(
            "DELETE FROM favorites WHERE entity_type = 'track' "
            "AND (entity_id = ? OR track_id = ?)",
            (uid, filepath),
        )
        return _BULK_STATUS_APPLIED

    @staticmethod
    def _mark_rolled_back(results: dict[int, str]) -> dict[int, str]:
        return {tid: _BULK_STATUS_ROLLED_BACK if status == _BULK_STATUS_APPLIED
                else status for tid, status in results.items()}

    def _bulk_result(self, results: dict[int, str], favorite: bool,
                     atomic: bool) -> OperationResult:
        applied = sum(1 for s in results.values() if s == _BULK_STATUS_APPLIED)
        data = {
            "results": dict(results),
            "applied": applied,
            "already_set": sum(1 for s in results.values()
                               if s == _BULK_STATUS_ALREADY_SET),
            "not_found": sum(1 for s in results.values()
                             if s == _BULK_STATUS_NOT_FOUND),
            "failed": sum(1 for s in results.values() if s == _BULK_STATUS_FAILED),
            "rolled_back": any(s == _BULK_STATUS_ROLLED_BACK
                               for s in results.values()),
            "count": applied,
            "favorite": favorite,
            "atomic": atomic,
        }
        readback = self._bulk_readback(list(results))
        data["total_favorites"] = readback
        self._emit(EVENT_FAVORITE_BULK, {
            "count": applied,
            "favorite": favorite,
            "track_ids": list(results),
            "total_favorites": readback,
        })
        mismatched = self._bulk_mismatches(results, favorite)
        if mismatched:
            data["details"] = {
                "requested": favorite,
                "mismatched_ids": mismatched,
            }
            return OperationResult(
                ok=False, code="READBACK_MISMATCH",
                message=f"Bulk favorite readback mismatch for ids {mismatched}: "
                        f"requested={favorite}",
                data=data,
            )
        return OperationResult.success(data)

    def _bulk_mismatches(self, results: dict[int, str], favorite: bool) -> list[int]:
        if not self._can():
            return []
        mismatched: list[int] = []
        for tid, status in results.items():
            if status not in (_BULK_STATUS_APPLIED, _BULK_STATUS_ALREADY_SET):
                continue
            row = self._db.conn.execute(
                "SELECT 1 FROM favorites WHERE entity_type = 'track' "
                "AND (entity_id = (SELECT track_uid FROM media_items WHERE id = ?) "
                "OR track_id = (SELECT filepath FROM media_items WHERE id = ?)) "
                "LIMIT 1",
                (tid, tid),
            ).fetchone()
            if (row is not None) != bool(favorite):
                mismatched.append(tid)
        return mismatched

    def _bulk_readback(self, track_ids: list[int]) -> int:
        if not self._can() or not track_ids:
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
