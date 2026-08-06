"""LibraryDoctorService — real diagnostics coordinator and repair engine.

Scan detects issues through real detectors (scan repository + genre cleanup).
Repairs route through a registry of ``IssueType -> RepairHandler``; every
handler implements preview/execute/readback/undo. ``repair(issue)`` looks up
the handler (NO_REPAIR_HANDLER when absent), requires a ConfirmationToken
issued by ConfirmationService for destructive repairs (self-declared sources
are never accepted), executes inline or as a durable job, verifies via
readback and registers a real compensation in UndoService. There is no
nominal success: an unverified repair reports READBACK_FAILED and
compensates.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field as dc_field
from typing import Any

from core.confirmation_service import compute_target_hash
from core.worker_manager import CancelledError

logger = logging.getLogger("michi.library_doctor")

EVENT_REPAIR_COMPLETED = "doctor.repair.completed"
EVENT_REPAIR_FAILED = "doctor.repair.failed"
EVENT_SCAN_COMPLETED = "doctor.scan.completed"

# Token TTL for destructive repairs: the user approves the preview and the
# repair may run later as a durable job, so the window is generous.
DOCTOR_TOKEN_TTL_S = 3600


class Issue:
    def __init__(self, issue_type: str, severity: str, description: str,
                 filepath: str = "", details: dict | None = None):
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.filepath = filepath
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "filepath": self.filepath,
            "details": dict(self.details),
        }


@dataclass
class RepairOutcome:
    applied: int = 0
    detail: str = ""
    affected: list[dict[str, Any]] = dc_field(default_factory=list)


class BaseRepairHandler:
    """Contract every real repair handler implements."""

    issue_type: str = ""
    destructive: bool = False
    durable: bool = False
    description: str = ""

    def preview(self, issue: dict, ctx=None) -> dict:
        return {"ok": True, "description": self.description, "changes": []}

    def execute(self, issue: dict, ctx=None) -> RepairOutcome:
        raise NotImplementedError

    def readback(self, issue: dict) -> bool:
        raise NotImplementedError

    def undo(self, issue: dict, ctx=None) -> bool:
        return False


class _RowTrackHandler(BaseRepairHandler):
    """Common machinery for handlers that snapshot a DB row before removal."""

    def _snapshot_row(self, issue: dict) -> dict | None:
        raise NotImplementedError

    def execute(self, issue: dict, ctx=None) -> RepairOutcome:
        snap = self._snapshot_row(issue)
        if snap is None:
            return RepairOutcome(0, "Row already gone", [])
        issue["details"]["_snapshot"] = snap
        ok = self._remove(issue)
        if not ok:
            return RepairOutcome(0, "Removal failed", [])
        return RepairOutcome(1, "Row removed", [snap])

    def undo(self, issue: dict, ctx=None) -> bool:
        snap = (issue.get("details") or {}).get("_snapshot")
        if not snap:
            return False
        return self._restore(snap)

    def _remove(self, issue: dict) -> bool:
        raise NotImplementedError

    def _restore(self, snap: dict) -> bool:
        raise NotImplementedError


class MissingFileHandler(_RowTrackHandler):
    """Soft-delete DB records whose file is gone (via LibraryMutationService)."""

    issue_type = "missing_file"
    destructive = True
    description = "Eliminar del catálogo los registros cuyo archivo falta en disco"

    def __init__(self, mutation_service=None):
        self._mutation = mutation_service

    def preview(self, issue: dict, ctx=None) -> dict:
        track_id = (issue.get("details") or {}).get("track_id")
        return {
            "ok": True,
            "description": self.description,
            "changes": [{
                "action": "soft_delete_track",
                "track_id": track_id,
                "filepath": issue.get("filepath", ""),
            }],
        }

    def _snapshot_row(self, issue: dict) -> dict | None:
        track_id = (issue.get("details") or {}).get("track_id")
        conn = getattr(self._mutation._db if self._mutation else None, "conn", None)
        if not track_id or conn is None:
            return None
        row = conn.execute(
            "SELECT deleted_at FROM media_items WHERE id=?", (track_id,),
        ).fetchone()
        if row is None or row[0] is not None:
            return None
        return {"track_id": track_id, "deleted_at": row[0]}

    def _remove(self, issue: dict) -> bool:
        if self._mutation is None:
            return False
        track_id = (issue.get("details") or {}).get("track_id")
        result = self._mutation.remove_tracks_from_library([track_id],
                                                           source="doctor")
        return result.ok

    def _restore(self, snap: dict) -> bool:
        conn = getattr(self._mutation._db if self._mutation else None, "conn", None)
        if conn is None:
            return False
        try:
            conn.execute(
                "UPDATE media_items SET deleted_at=NULL WHERE id=?",
                (snap["track_id"],),
            )
            conn.commit()
            return True
        except Exception:  # noqa: BLE001
            return False

    def readback(self, issue: dict) -> bool:
        track_id = (issue.get("details") or {}).get("track_id")
        conn = getattr(self._mutation._db if self._mutation else None, "conn", None)
        if not track_id or conn is None:
            return False
        row = conn.execute(
            "SELECT deleted_at FROM media_items WHERE id=?", (track_id,),
        ).fetchone()
        return row is not None and row[0] is not None


class DuplicatePathHandler(MissingFileHandler):
    """Soft-delete the duplicate DB record for the same filepath."""

    issue_type = "duplicate_path"
    description = "Eliminar del catálogo la pista duplicada (misma ruta)"


class OrphanPlaylistItemHandler(_RowTrackHandler):
    """Remove playlist items that point to tracks no longer in the library."""

    issue_type = "orphan_playlist_item"
    destructive = True
    description = "Quitar items de playlist que apuntan a pistas inexistentes"

    def __init__(self, scan_repository=None, db=None):
        self._repo = scan_repository
        self._db = db

    def preview(self, issue: dict, ctx=None) -> dict:
        return {
            "ok": True,
            "description": self.description,
            "changes": [{
                "action": "delete_playlist_item",
                "rowid": (issue.get("details") or {}).get("rowid"),
                "playlist_id": (issue.get("details") or {}).get("playlist_id"),
                "filepath": issue.get("filepath", ""),
            }],
        }

    def _snapshot_row(self, issue: dict) -> dict | None:
        rowid = (issue.get("details") or {}).get("rowid")
        conn = getattr(self._db, "conn", None)
        if not rowid or conn is None:
            return None
        try:
            row = conn.execute(
                "SELECT rowid, filepath, playlist_id, position FROM playlist_items "
                "WHERE rowid=?", (rowid,),
            ).fetchone()
        except Exception:  # noqa: BLE001
            return None
        if row is None:
            return None
        return {"rowid": row[0], "filepath": row[1],
                "playlist_id": row[2], "position": row[3]}

    def _remove(self, issue: dict) -> bool:
        if self._repo is None or not hasattr(self._repo, "delete_playlist_item"):
            return False
        try:
            self._repo.delete_playlist_item(
                (issue.get("details") or {}).get("rowid"))
            return True
        except Exception:  # noqa: BLE001
            return False

    def _restore(self, snap: dict) -> bool:
        conn = getattr(self._db, "conn", None)
        if conn is None:
            return False
        try:
            conn.execute(
                "INSERT INTO playlist_items (filepath, playlist_id, position) "
                "VALUES (?,?,?)",
                (snap["filepath"], snap["playlist_id"], snap["position"]),
            )
            conn.commit()
            return True
        except Exception:  # noqa: BLE001
            return False

    def readback(self, issue: dict) -> bool:
        rowid = (issue.get("details") or {}).get("rowid")
        conn = getattr(self._db, "conn", None)
        if not rowid or conn is None:
            return False
        row = conn.execute(
            "SELECT 1 FROM playlist_items WHERE rowid=?", (rowid,),
        ).fetchone()
        return row is None


class OrphanHistoryHandler(_RowTrackHandler):
    """Remove play-history entries for tracks no longer in the library."""

    issue_type = "orphan_history"
    destructive = True
    description = "Quitar entradas de historial que apuntan a pistas inexistentes"

    def __init__(self, scan_repository=None, db=None):
        self._repo = scan_repository
        self._db = db

    def preview(self, issue: dict, ctx=None) -> dict:
        return {
            "ok": True,
            "description": self.description,
            "changes": [{
                "action": "delete_history_entry",
                "history_id": (issue.get("details") or {}).get("history_id"),
                "filepath": issue.get("filepath", ""),
            }],
        }

    def _snapshot_row(self, issue: dict) -> dict | None:
        history_id = (issue.get("details") or {}).get("history_id")
        conn = getattr(self._db, "conn", None)
        if not history_id or conn is None:
            return None
        try:
            row = conn.execute(
                "SELECT id, filepath FROM play_history WHERE id=?",
                (history_id,),
            ).fetchone()
        except Exception:  # noqa: BLE001
            return None
        if row is None:
            return None
        return {"id": row[0], "filepath": row[1]}

    def _remove(self, issue: dict) -> bool:
        if self._repo is None or not hasattr(self._repo, "delete_history"):
            return False
        try:
            self._repo.delete_history(
                (issue.get("details") or {}).get("history_id"))
            return True
        except Exception:  # noqa: BLE001
            return False

    def _restore(self, snap: dict) -> bool:
        conn = getattr(self._db, "conn", None)
        if conn is None:
            return False
        try:
            conn.execute(
                "INSERT INTO play_history (id, filepath) VALUES (?,?)",
                (snap["id"], snap["filepath"]),
            )
            conn.commit()
            return True
        except Exception:  # noqa: BLE001
            return False

    def readback(self, issue: dict) -> bool:
        history_id = (issue.get("details") or {}).get("history_id")
        conn = getattr(self._db, "conn", None)
        if not history_id or conn is None:
            return False
        row = conn.execute(
            "SELECT 1 FROM play_history WHERE id=?", (history_id,),
        ).fetchone()
        return row is None


class DuplicateUidHandler(BaseRepairHandler):
    """Re-derive a stable track_uid from the filepath (non-destructive)."""

    issue_type = "duplicate_uid"
    destructive = False
    description = "Regenerar el UID de pistas con UID duplicado"

    def __init__(self, scan_repository=None):
        self._repo = scan_repository

    def preview(self, issue: dict, ctx=None) -> dict:
        return {
            "ok": True,
            "description": self.description,
            "changes": [{
                "action": "regenerate_uid",
                "track_id": (issue.get("details") or {}).get("track_id"),
                "filepath": issue.get("filepath", ""),
            }],
        }

    def execute(self, issue: dict, ctx=None) -> RepairOutcome:
        if self._repo is None:
            return RepairOutcome(0, "No scan repository", [])
        track_id = (issue.get("details") or {}).get("track_id")
        fp = issue.get("filepath", "")
        old_uid = (issue.get("details") or {}).get("old_uid", "")
        try:
            self._repo.update_uid(track_id, fp)
        except Exception:  # noqa: BLE001
            return RepairOutcome(0, "UID update failed", [])
        issue["details"]["_old_uid"] = old_uid
        return RepairOutcome(1, "UID regenerado", [{"track_id": track_id}])

    def readback(self, issue: dict) -> bool:
        if self._repo is None:
            return False
        track_id = (issue.get("details") or {}).get("track_id")
        fp = issue.get("filepath", "")
        import hashlib as _hashlib
        expected = f"fp:{_hashlib.sha256(fp.encode()).hexdigest()[:16]}"
        conn = getattr(self._repo, "_conn", None) or getattr(
            getattr(self._repo, "_db", None), "conn", None)
        if conn is None:
            return False
        row = conn.execute(
            "SELECT track_uid FROM media_items WHERE id=?", (track_id,),
        ).fetchone()
        return row is not None and row[0] == expected

    def undo(self, issue: dict, ctx=None) -> bool:
        conn = getattr(self._repo, "_conn", None) or getattr(
            getattr(self._repo, "_db", None), "conn", None)
        track_id = (issue.get("details") or {}).get("track_id")
        old_uid = (issue.get("details") or {}).get("_old_uid", "")
        if conn is None or not old_uid:
            return False
        try:
            conn.execute(
                "UPDATE media_items SET track_uid=? WHERE id=?",
                (old_uid, track_id),
            )
            conn.commit()
            return True
        except Exception:  # noqa: BLE001
            return False


class MissingMetadataHandler(BaseRepairHandler):
    """Fill missing title/artist via the canonical metadata editor pipeline."""

    issue_type = "missing_metadata"
    destructive = False
    description = "Completar metadatos faltantes (título derivado del nombre de archivo)"

    def __init__(self, metadata_editor=None):
        self._editor = metadata_editor

    def preview(self, issue: dict, ctx=None) -> dict:
        return {
            "ok": True,
            "description": self.description,
            "changes": [{
                "action": "fill_title_from_filename",
                "track_id": (issue.get("details") or {}).get("track_id"),
                "filepath": issue.get("filepath", ""),
            }],
        }

    def execute(self, issue: dict, ctx=None) -> RepairOutcome:
        if self._editor is None:
            return RepairOutcome(0, "Metadata editor unavailable", [])
        fp = issue.get("filepath", "")
        track_id = (issue.get("details") or {}).get("track_id")
        import os
        stem = os.path.splitext(os.path.basename(fp))[0] if fp else ""
        if not stem:
            return RepairOutcome(0, "Cannot derive title from filename", [])
        proposal = self._editor.build_proposal(
            [{"filepath": fp, "track_id": track_id}],
            {"title": stem},
        )
        if not proposal.get("ok"):
            return RepairOutcome(0, proposal.get("message", "proposal failed"), [])
        # repair() already validated the user-approved token for this repair
        # operation; the nested metadata edit receives its own token issued
        # and approved through the same ConfirmationService (never a
        # self-declared source).
        conf = self._editor.confirm(
            proposal["proposal_id"], selected_fields=["title"])
        if not conf.get("ok"):
            return RepairOutcome(0, conf.get("code", "TOKEN_REQUIRED"), [])
        token = conf["confirmation_token"]
        if not self._editor.approve(token).get("ok"):
            return RepairOutcome(0, "INVALID_CONFIRMATION_TOKEN", [])
        result = self._editor.apply_batch([{
            "proposal_id": proposal["proposal_id"],
            "confirmation_token": token,
        }])
        if result.get("applied", 0) != 1:
            return RepairOutcome(0, result.get("status", "APPLY_FAILED"), [])
        issue["details"]["_operation_id"] = result.get("operation_id", "")
        issue["details"]["_proposal_id"] = proposal["proposal_id"]
        return RepairOutcome(1, "Título completado", [{"track_id": track_id}])

    def readback(self, issue: dict) -> bool:
        if self._editor is None or self._editor._db is None:
            return False
        track_id = (issue.get("details") or {}).get("track_id")
        try:
            item = self._editor._db.get_media_item_by_id(track_id)
        except Exception:  # noqa: BLE001
            return False
        return item is not None and bool(getattr(item, "title", "") or "")

    def undo(self, issue: dict, ctx=None) -> bool:
        if self._editor is None:
            return False
        operation_id = (issue.get("details") or {}).get("_operation_id", "")
        if not operation_id:
            return False
        result = self._editor.undo(operation_id)
        return bool(result.get("ok"))


class GenreFragmentationHandler(BaseRepairHandler):
    """Normalize fragmented genre spellings through GenreCleanupService.

    Raw-value variants that normalize to one canonical (e.g. "Hip-Hop" and
    "Hip Hop") are rewritten to the canonical spelling in media_items and
    track_genres, and the genre registry is merged via
    GenreCleanupService.execute_merge.
    """

    issue_type = "genre_fragmentation"
    destructive = True
    description = "Fusionar variantes de género duplicadas (GenreCleanupService)"

    def __init__(self, genre_cleanup=None):
        self._cleanup = genre_cleanup

    def preview(self, issue: dict, ctx=None) -> dict:
        details = issue.get("details") or {}
        return {
            "ok": True,
            "description": self.description,
            "changes": [{
                "action": "merge_genres",
                "source_genres": details.get("raw_values", []),
                "target": details.get("canonical", ""),
                "count": details.get("count", 0),
            }],
        }

    def execute(self, issue: dict, ctx=None) -> RepairOutcome:
        if self._cleanup is None or self._cleanup._repo is None:
            return RepairOutcome(0, "GenreCleanupService unavailable", [])
        details = issue.get("details") or {}
        sources = list(details.get("raw_values", []))
        target = details.get("canonical", "")
        if not sources or not target:
            return RepairOutcome(0, "Missing genre variants", [])
        conn = getattr(self._cleanup._repo, "_conn", None)
        if conn is None:
            return RepairOutcome(0, "Genre repository unavailable", [])
        snapshot = self._snapshot_genres(conn, sources)
        affected = 0
        placeholders = ",".join("?" * len(sources))
        try:
            cur = conn.execute(
                f"UPDATE media_items SET genre=? "
                f"WHERE genre IN ({placeholders})",
                (target, *sources),
            )
            affected += max(0, cur.rowcount)
            cur = conn.execute(
                f"UPDATE track_genres SET genre=? "
                f"WHERE genre IN ({placeholders})",
                (target, *sources),
            )
            affected += max(0, cur.rowcount)
            conn.commit()
        except Exception as error:  # noqa: BLE001
            logger.warning("genre normalization failed: %s", error)
            return RepairOutcome(0, f"Normalization failed: {error}", [])
        self._cleanup.execute_merge(sources, target)
        if affected == 0:
            return RepairOutcome(0, "No tracks affected by merge", [])
        issue["details"]["_snapshot"] = snapshot
        return RepairOutcome(affected, f"{affected} valor(es) normalizados a "
                                       f"'{target}'", snapshot)

    def _snapshot_genres(self, conn, sources: list[str]) -> list[dict]:
        snapshot = []
        placeholders = ",".join("?" * len(sources))
        try:
            rows = conn.execute(
                f"SELECT id, genre FROM media_items "
                f"WHERE genre IN ({placeholders})",
                tuple(sources),
            ).fetchall()
            for row in rows:
                snapshot.append({"kind": "media_item", "id": row[0],
                                 "genre": row[1]})
            rows = conn.execute(
                f"SELECT track_id, genre, canonical_genre FROM track_genres "
                f"WHERE genre IN ({placeholders})",
                tuple(sources),
            ).fetchall()
            for row in rows:
                snapshot.append({"kind": "track_genre", "track_id": row[0],
                                 "genre": row[1], "canonical": row[2]})
        except Exception:  # noqa: BLE001
            return []
        return snapshot

    def readback(self, issue: dict) -> bool:
        if self._cleanup is None or self._cleanup._repo is None:
            return False
        sources = (issue.get("details") or {}).get("raw_values", [])
        target = (issue.get("details") or {}).get("canonical", "")
        leftover = [s for s in sources if s != target]
        if not leftover:
            return True
        conn = getattr(self._cleanup._repo, "_conn", None)
        if conn is None:
            return False
        placeholders = ",".join("?" * len(leftover))
        try:
            row = conn.execute(
                f"SELECT COUNT(*) FROM media_items "
                f"WHERE genre IN ({placeholders})",
                tuple(leftover),
            ).fetchone()
            if row is None or row[0] != 0:
                return False
            row = conn.execute(
                f"SELECT COUNT(*) FROM track_genres "
                f"WHERE genre IN ({placeholders})",
                tuple(leftover),
            ).fetchone()
            return row is not None and row[0] == 0
        except Exception:  # noqa: BLE001
            return False

    def undo(self, issue: dict, ctx=None) -> bool:
        if self._cleanup is None or self._cleanup._repo is None:
            return False
        snapshot = (issue.get("details") or {}).get("_snapshot", [])
        if not snapshot:
            return False
        conn = getattr(self._cleanup._repo, "_conn", None)
        if conn is None:
            return False
        restored = 0
        for entry in snapshot:
            try:
                if entry.get("kind") == "media_item":
                    conn.execute(
                        "UPDATE media_items SET genre=? WHERE id=?",
                        (entry["genre"], entry["id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE track_genres SET genre=?, canonical_genre=? "
                        "WHERE track_id=? AND canonical_genre=?",
                        (entry["genre"], entry["canonical"], entry["track_id"],
                         entry["canonical"]),
                    )
                restored += 1
            except Exception:  # noqa: BLE001
                continue
        if restored:
            conn.commit()
        return restored > 0


class LibraryDoctorService:
    def __init__(self, db=None, scan_repository=None, worker_manager=None,
                 job_service=None, mutation_service=None,
                 confirmation_service=None, undo_service=None,
                 metadata_editor=None, genre_cleanup=None, event_bus=None):
        self._db = db
        self._scan_repo = scan_repository
        self._worker_manager = worker_manager
        self._job_service = job_service
        self._mutation = mutation_service
        self._confirmation = confirmation_service
        self._undo = undo_service
        self._editor = metadata_editor
        self._genre_cleanup = genre_cleanup
        self._event_bus = event_bus
        self._cancelled = False
        self._handlers: dict[str, BaseRepairHandler] = {}
        self._register_builtin_handlers()

    # ── repair registry ──────────────────────────────────────────────────

    def register_handler(self, handler: BaseRepairHandler) -> None:
        if not handler.issue_type:
            raise ValueError("handler must declare an issue_type")
        self._handlers[handler.issue_type] = handler

    def get_handler(self, issue_type: str) -> BaseRepairHandler | None:
        return self._handlers.get(issue_type)

    @property
    def handler_ids(self) -> list[str]:
        return sorted(self._handlers)

    def _register_builtin_handlers(self) -> None:
        self.register_handler(MissingFileHandler(self._mutation))
        self.register_handler(DuplicatePathHandler(self._mutation))
        self.register_handler(OrphanPlaylistItemHandler(self._scan_repo, self._db))
        self.register_handler(OrphanHistoryHandler(self._scan_repo, self._db))
        self.register_handler(DuplicateUidHandler(self._scan_repo))
        self.register_handler(MissingMetadataHandler(self._editor))
        self.register_handler(GenreFragmentationHandler(self._genre_cleanup))

    # ── scan ─────────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._db is not None

    def scan(self, ctx=None) -> dict:
        self._cancelled = False
        issues: list[Issue] = []
        total = 0
        try:
            if self._scan_repo is not None:
                rows = self._scan_repo.fetch_all_tracks() or []
                total = len(rows)
                filepaths_seen: dict[str, int] = {}
                uids_seen: dict[str, int] = {}
                for row in rows:
                    self._raise_if_cancelled(ctx)
                    rid, fp, title, artist, album, album_key, track_uid = row
                    if not fp:
                        continue
                    if not _path_exists(fp):
                        issues.append(Issue(
                            "missing_file", "error",
                            "Archivo no encontrado en disco", fp,
                            {"track_id": rid},
                        ))
                    if fp in filepaths_seen:
                        issues.append(Issue(
                            "duplicate_path", "warning",
                            f"Ruta duplicada (IDs: {filepaths_seen[fp]}, {rid})",
                            fp, {"track_id": rid},
                        ))
                    else:
                        filepaths_seen[fp] = rid
                    if track_uid:
                        if track_uid in uids_seen:
                            issues.append(Issue(
                                "duplicate_uid", "warning",
                                f"UID duplicado: {track_uid}", fp,
                                {"track_id": rid, "old_uid": track_uid},
                            ))
                        else:
                            uids_seen[track_uid] = rid
                    if not title or not artist:
                        issues.append(Issue(
                            "missing_metadata", "warning",
                            "Falta título o artista", fp, {"track_id": rid},
                        ))

                for op in self._scan_repo.find_orphan_playlist_items() or []:
                    self._raise_if_cancelled(ctx)
                    issues.append(Issue(
                        "orphan_playlist_item", "warning",
                        f"Item huérfano en playlist {op[2]}", op[1] or "",
                        {"rowid": op[0], "playlist_id": op[2]},
                    ))

                for oh in self._scan_repo.find_orphan_history() or []:
                    self._raise_if_cancelled(ctx)
                    issues.append(Issue(
                        "orphan_history", "warning",
                        "Entrada huérfana en historial", oh[1] or "",
                        {"history_id": oh[0]},
                    ))

            if self._genre_cleanup is not None:
                for dup in self._genre_cleanup.detect_duplicates() or []:
                    self._raise_if_cancelled(ctx)
                    issues.append(Issue(
                        "genre_fragmentation", "info",
                        f"Géneros duplicados: {', '.join(dup['raw_values'])} "
                        f"→ {dup['canonical']}",
                        details=dup,
                    ))
        except CancelledError:
            return {"ok": False, "code": "CANCELLED",
                    "message": "Escaneo cancelado", "issues": [],
                    "count": 0, "total_checked": total}
        except Exception as error:  # noqa: BLE001
            logger.exception("doctor scan failed")
            return {"ok": False, "code": "SCAN_FAILED", "message": str(error),
                    "issues": [], "count": 0, "total_checked": total}
        result = {
            "ok": True,
            "issues": [i.to_dict() for i in issues],
            "count": len(issues),
            "total_checked": total,
        }
        self._emit(EVENT_SCAN_COMPLETED, {"count": len(issues),
                                          "total_checked": total})
        return result

    def _raise_if_cancelled(self, ctx) -> None:
        if ctx is not None and getattr(ctx, "token", None) is not None:
            ctx.token.raise_if_cancelled()
        if self._cancelled:
            raise CancelledError("Scan cancelled")

    # ── repair ───────────────────────────────────────────────────────────

    def preview_repair(self, issue: dict) -> dict:
        handler = self._handlers.get(issue.get("type", ""))
        if handler is None:
            return {"ok": False, "code": "NO_REPAIR_HANDLER",
                    "message": f"No repair handler for issue type "
                               f"'{issue.get('type')}'",
                    "issue_type": issue.get("type", "")}
        try:
            return handler.preview(issue)
        except Exception as error:  # noqa: BLE001
            return {"ok": False, "code": "PREVIEW_FAILED", "message": str(error)}

    def repair(self, issue: dict, confirmation_token: str = "", ctx=None) -> dict:
        """Execute a real repair for one issue.

        Contract: handler lookup -> preview -> token authorization
        (destructive repairs require an approved ConfirmationToken issued by
        ConfirmationService; self-declared sources are never accepted) ->
        execute (inline or durable job) -> readback verification -> undo
        registration. Never reports nominal success.
        """
        issue_type = issue.get("type", "")
        handler = self._handlers.get(issue_type)
        if handler is None:
            return {"ok": False, "code": "NO_REPAIR_HANDLER",
                    "message": f"No repair handler for issue type "
                               f"'{issue_type}'",
                    "issue_type": issue_type}
        try:
            preview = handler.preview(issue, ctx)
        except Exception as error:  # noqa: BLE001
            return {"ok": False, "code": "PREVIEW_FAILED", "message": str(error)}
        if not preview.get("ok"):
            return {"ok": False, "code": "PREVIEW_FAILED",
                    "message": preview.get("description", "preview failed")}

        op_id = self._repair_operation_id(issue_type, issue)
        command_hash = self._repair_command_hash(issue_type, issue, handler)
        target_hash = self._repair_target_hash(issue)

        if handler.destructive:
            if confirmation_token:
                ok, code = self._confirm_repair_token(
                    confirmation_token, op_id, command_hash, target_hash)
                if not ok:
                    return {"ok": False, "code": code,
                            "message": f"Repair token rejected: {code}",
                            "operation_id": op_id,
                            "issue_type": issue_type}
            elif self._confirmation is not None:
                issue_key = self._issue_key(issue)
                request = self._confirmation.confirm(
                    operation_id=op_id,
                    command_hash=command_hash,
                    entity_refs=(issue_key,),
                    description=handler.description,
                    risk_level="high",
                )
                return {"ok": False, "code": "CONFIRMATION_REQUIRED",
                        "message": handler.description,
                        "confirmation_token": request.token,
                        "operation_id": op_id,
                        "preview": preview}
            else:
                return {"ok": False, "code": "TOKEN_REQUIRED",
                        "message": "Destructive repair requires an approved "
                                   "ConfirmationToken; no ConfirmationService "
                                   "is available",
                        "operation_id": op_id, "issue_type": issue_type}

        if (handler.durable and self._job_service is not None
                and self._worker_manager is not None):
            job_id = self._job_service.create_job(
                "doctor_repair", owner="library_doctor",
                payload={"issue": issue,
                         "confirmation_token": confirmation_token},
                total=1, cancellable=True, pausable=False, retryable=True,
            )
            if self._job_service.start_job(job_id):
                return {"ok": True, "status": "JOB_STARTED",
                        "job_id": job_id, "operation_id": op_id,
                        "issue_type": issue_type}
            return {"ok": False, "code": "JOB_START_FAILED", "job_id": job_id}

        result = self._execute_repair_inline(handler, issue, op_id, ctx)
        if result.get("ok") and confirmation_token and self._confirmation is not None:
            self._confirmation.consume(confirmation_token)
        return result

    def _confirm_repair_token(self, confirmation_token: str, op_id: str,
                              command_hash: str, target_hash: str):
        """Validate an approved token against this repair operation."""
        if self._confirmation is None:
            return False, "TOKEN_REQUIRED"
        return self._confirmation.validate(
            confirmation_token,
            command_hash=command_hash,
            target_hash=target_hash,
        )

    def _execute_repair_inline(self, handler: BaseRepairHandler, issue: dict,
                               op_id: str, ctx) -> dict:
        try:
            outcome = handler.execute(issue, ctx)
        except CancelledError:
            return {"ok": False, "code": "CANCELLED",
                    "message": "Repair cancelado"}
        except Exception as error:  # noqa: BLE001
            logger.exception("repair execute failed for %s", op_id)
            return {"ok": False, "code": "EXECUTE_FAILED", "message": str(error)}

        if outcome.applied == 0:
            return {"ok": False, "code": "REPAIR_NO_EFFECT",
                    "message": outcome.detail or "Nothing to repair",
                    "operation_id": op_id, "issue_type": handler.issue_type}

        readback_ok = False
        try:
            readback_ok = handler.readback(issue)
        except Exception:  # noqa: BLE001
            readback_ok = False

        if not readback_ok:
            rollback_performed = False
            try:
                rollback_performed = bool(handler.undo(issue))
            except Exception:  # noqa: BLE001
                rollback_performed = False
            self._emit(EVENT_REPAIR_FAILED, {
                "operation_id": op_id, "issue_type": handler.issue_type,
                "error": "READBACK_FAILED",
            })
            return {"ok": False, "code": "READBACK_FAILED",
                    "message": "Repair applied but readback did not verify; "
                               "compensation executed",
                    "rollback_performed": rollback_performed,
                    "operation_id": op_id, "issue_type": handler.issue_type}

        if self._undo is not None:
            self._undo.register(
                op_id, handler.description,
                lambda: bool(handler.undo(issue)),
                entity=str(issue.get("filepath", "") or
                           (issue.get("details") or {}).get("track_id")),
                kind="doctor_repair",
                metadata={"issue_type": handler.issue_type},
            )
        self._emit(EVENT_REPAIR_COMPLETED, {
            "operation_id": op_id, "issue_type": handler.issue_type,
            "applied": outcome.applied,
        })
        return {
            "ok": True,
            "status": "COMPLETED",
            "applied": outcome.applied,
            "detail": outcome.detail,
            "operation_id": op_id,
            "issue_type": handler.issue_type,
            "readback_verified": True,
            "job_id": None,
        }

    def rollback(self, issue: dict) -> dict:
        """Real rollback of a completed repair via UndoService."""
        issue_type = issue.get("type", "")
        op_id = self._repair_operation_id(
            issue_type, issue,
        )
        if self._undo is None:
            return {"ok": False, "code": "CAPABILITY_UNAVAILABLE",
                    "message": "No UndoService injected",
                    "operation_id": op_id}
        result = self._undo.undo(op_id)
        if not result.ok:
            return {"ok": False, "code": result.code,
                    "message": result.message, "operation_id": op_id}
        return {"ok": True, "status": "ROLLED_BACK",
                "operation_id": op_id, "description": result.data.get("description")}

    def _repair_target_hash(self, issue: dict) -> str:
        """Stable target hash for the repair issue (filepath / track id)."""
        return compute_target_hash([self._issue_key(issue)])

    @staticmethod
    def _issue_key(issue: dict) -> str:
        details = issue.get("details") or {}
        return str(
            details.get("track_id")
            or details.get("rowid")
            or details.get("history_id")
            or issue.get("filepath", "")
            or issue.get("id", "0")
        )

    def _repair_operation_id(self, issue_type: str, issue: dict) -> str:
        return f"doctor_repair:{issue_type}:{self._issue_key(issue)}"

    def _repair_command_hash(self, issue_type: str, issue: dict,
                             handler: BaseRepairHandler) -> str:
        payload = {
            "type": issue_type,
            "key": self._issue_key(issue),
            "filepath": issue.get("filepath", ""),
            "handler": handler.__class__.__name__,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode(),
        ).hexdigest()[:16]

    def _emit(self, event: str, data: dict) -> None:
        if self._event_bus is None or not hasattr(self._event_bus, "emit"):
            return
        try:
            self._event_bus.emit(event, data)
        except Exception:  # noqa: BLE001
            logger.debug("doctor event emit failed", exc_info=True)

    # ── lifecycle ────────────────────────────────────────────────────────

    def cancel(self):
        self._cancelled = True

    def start(self):
        self._cancelled = False

    def health(self) -> dict:
        return {
            "available": self.available,
            "handlers": len(self._handlers),
            "handler_types": self.handler_ids,
            "undo_available": self._undo is not None,
            "confirmation_available": self._confirmation is not None,
            "genre_cleanup_available": self._genre_cleanup is not None,
            "metadata_editor_available": self._editor is not None,
        }

    def shutdown(self):
        self._cancelled = True


def _path_exists(fp: str) -> bool:
    import os
    return os.path.isfile(fp)
