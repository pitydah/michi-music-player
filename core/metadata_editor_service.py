"""MetadataEditorService — canonical metadata editing authority (Slice 8).

Single pipeline: build_proposal → preview_proposal → confirm → apply_batch
(atomic per track: DB via LibraryMutationService + physical tags via the
mutagen tag writer, with compensation on phase failure) → readback (per-field
DB + physical verification) → undo (real compensation through UndoService).

Authorization (P0 Fase Metadata): apply_batch/apply_single ONLY execute with
a valid ConfirmationToken issued by ConfirmationService and approved by the
user flow. Self-declared ``confirmed=True`` + ``source=`` intents are NEVER
accepted (TOKEN_REQUIRED). effective_fields = proposal.fields ∩
token.selected_fields — unselected fields are never applied.

Backup policy: physical tag writes snapshot the file into
``{tmpdir}/michi_metadata_undo``; backups are kept for the undo window
(BACKUP_RETENTION_DAYS, default 7) and pruned by ``cleanup_backups()`` on
every apply.

Legacy single-file surface (``preview``/``apply``/``rollback``) is preserved
for existing callers and tests; legacy DB-only ``update_metadata``/``batch_update``
are disabled (LEGACY_OPERATION_DISABLED) — no production consumer exists.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable

from core.confirmation_service import compute_target_hash
from core.models.operation_result import OperationResult
from core.worker_manager import CancelledError

logger = logging.getLogger("michi.metadata_editor")

EVENT_PROPOSAL_BUILT = "metadata.proposal.built"
EVENT_PROPOSAL_PREVIEWED = "metadata.proposal.previewed"
EVENT_PROPOSAL_CONFIRMED = "metadata.proposal.confirmed"
EVENT_BATCH_APPLIED = "metadata.batch.applied"
EVENT_READBACK_COMPLETED = "metadata.readback.completed"

# Readback statuses per field (ADR-005: no nominal ok).
RB_VERIFIED = "VERIFIED"
RB_DB_MISMATCH = "DB_MISMATCH"
RB_TAG_MISMATCH = "TAG_MISMATCH"
RB_READ_ERROR = "READ_ERROR"
RB_UNSUPPORTED_TAG = "UNSUPPORTED_TAG"
RB_FILE_MISSING = "FILE_MISSING"

# Backup retention: backups are kept for the undo window (7 days).
BACKUP_RETENTION_DAYS = 7
_BACKUP_DIR_NAME = "michi_metadata_undo"

# Bridge/editor field name -> media_items column name.
_FIELD_TO_DB = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "album_artist": "albumartist",
    "genre": "genre",
    "year": "year",
    "track_number": "track_number",
    "track_total": "track_total",
    "disc_number": "disc_number",
    "disc_total": "disc_total",
    "composer": "composer",
    "comment": "comment",
    "bpm": "bpm",
}

# DB column name -> TrackTags attribute name (physical tag writer).
_DB_TO_TAG = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "albumartist": "albumartist",
    "genre": "genre",
    "year": "date",
    "track_number": "tracknumber",
    "track_total": "tracktotal",
    "disc_number": "discnumber",
    "disc_total": "disctotal",
    "composer": "composer",
    "comment": "comment",
    "bpm": "bpm",
}

# Default TTL for apply tokens (long enough for durable job execution).
_APPLY_TOKEN_TTL_S = 3600


@dataclass
class MetadataProposal:
    proposal_id: str
    track_refs: list[dict[str, Any]]
    fields: dict[str, Any]
    created_at: float = dc_field(default_factory=time.time)
    state: str = "proposed"
    selected_fields: list[str] = dc_field(default_factory=list)
    command_hash: str = ""


class MetadataEditorService:
    def __init__(self, db=None, mutation_service=None,
                 tag_reader: Callable | None = None,
                 tag_writer: Callable | None = None,
                 event_bus=None, confirmation_service=None,
                 undo_service=None, worker_manager=None):
        self._db = db
        self._mutation = mutation_service
        self._tag_reader = tag_reader
        self._tag_writer = tag_writer
        self._eb = event_bus
        self._cs = confirmation_service
        self._undo = undo_service
        self._wm = worker_manager
        self._proposals: dict[str, MetadataProposal] = {}
        self._undo_ctx: dict[str, dict[str, Any]] = {}

    # ── canonical pipeline ───────────────────────────────────────────────

    def build_proposal(self, track_refs: list, fields: dict | None = None) -> dict:
        """Create a metadata-change proposal for a set of track references.

        ``track_refs`` entries are dicts with ``filepath`` (and optionally
        ``track_id``). When ``fields`` is None the proposal fills detectable
        metadata gaps (title derived from the filename stem).
        """
        if not track_refs:
            return {"ok": False, "code": "EMPTY_TRACK_REFS",
                    "message": "No tracks given"}
        refs = []
        for ref in track_refs:
            if isinstance(ref, str):
                refs.append({"filepath": ref})
            elif isinstance(ref, dict) and (ref.get("filepath")
                                            or ref.get("track_id")):
                refs.append(dict(ref))
        if not refs:
            return {"ok": False, "code": "EMPTY_TRACK_REFS",
                    "message": "No valid track references"}

        proposal_fields: dict[str, Any] = {}
        if fields:
            proposal_fields = {
                k: v for k, v in fields.items()
                if k in _FIELD_TO_DB and v is not None
            }
        else:
            proposal_fields = self._detect_gaps(refs)

        if not proposal_fields:
            return {"ok": False, "code": "NO_FIELDS",
                    "message": "No fields to change"}

        proposal = MetadataProposal(
            proposal_id=f"prop_{uuid.uuid4().hex[:12]}",
            track_refs=refs,
            fields=proposal_fields,
        )
        self._proposals[proposal.proposal_id] = proposal
        self._emit(EVENT_PROPOSAL_BUILT, {
            "proposal_id": proposal.proposal_id,
            "track_count": len(refs),
            "field_count": len(proposal_fields),
            "fields": list(proposal_fields),
        })
        return {
            "ok": True,
            "proposal_id": proposal.proposal_id,
            "track_count": len(refs),
            "field_count": len(proposal_fields),
            "fields": list(proposal_fields),
        }

    def _detect_gaps(self, refs: list[dict]) -> dict[str, Any]:
        """Fill empty fields for the given tracks from existing DB values."""
        fields: dict[str, Any] = {}
        for ref in refs:
            fp = ref.get("filepath", "")
            item = self._get_item_for_ref(ref)
            for column, db_col in _FIELD_TO_DB.items():
                current = str(getattr(item, db_col, "") or "") if item else ""
                if not current:
                    if db_col == "title" and fp:
                        stem = os.path.splitext(os.path.basename(fp))[0]
                        if stem:
                            fields["title"] = stem
                    else:
                        fields[column] = ""
        return {k: v for k, v in fields.items() if v not in (None, "")}

    def preview_proposal(self, proposal_id: str) -> dict:
        """Show current DB values vs proposed values for a proposal."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return {"ok": False, "code": "PROPOSAL_NOT_FOUND",
                    "message": f"Unknown proposal: {proposal_id}"}
        changes = []
        for ref in proposal.track_refs:
            fp = ref.get("filepath", "")
            item = self._get_item_for_ref(ref)
            for field, value in proposal.fields.items():
                db_col = _FIELD_TO_DB[field]
                old = str(getattr(item, db_col, "") or "") if item else ""
                changes.append({
                    "filepath": fp,
                    "track_id": ref.get("track_id"),
                    "field": field,
                    "old_value": old,
                    "new_value": str(value),
                    "conflict": item is None,
                })
        proposal.state = "previewed"
        self._emit(EVENT_PROPOSAL_PREVIEWED, {
            "proposal_id": proposal_id, "change_count": len(changes),
        })
        return {"ok": True, "proposal_id": proposal_id,
                "changes": changes, "count": len(changes)}

    def confirm(self, proposal_id: str, selected_fields: list[str] | None = None,
                command_hash: str = "", ttl: int | None = None) -> dict:
        """Issue a ConfirmationToken for a proposal (user confirmation step).

        The token binds the proposal's command hash, target hash (track
        refs) and selected fields; it must be approved before ``apply_batch``
        accepts it. Without a ConfirmationService no token can be issued and
        the pipeline reports CONFIRMATION_UNAVAILABLE.
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return {"ok": False, "code": "PROPOSAL_NOT_FOUND",
                    "message": f"Unknown proposal: {proposal_id}"}
        if self._cs is None:
            return {"ok": False, "code": "CONFIRMATION_UNAVAILABLE",
                    "message": "No ConfirmationService injected; tokens "
                               "cannot be issued"}
        proposal.selected_fields = list(selected_fields or proposal.fields)
        proposal.command_hash = command_hash or self._default_command_hash(proposal)
        token = self._cs.issue(
            operation_id=proposal_id,
            command_hash=proposal.command_hash,
            target_hash=self._proposal_target_hash(proposal),
            selected_fields=tuple(proposal.selected_fields),
            ttl=ttl or _APPLY_TOKEN_TTL_S,
        )
        proposal.state = "awaiting_confirmation"
        self._emit(EVENT_PROPOSAL_CONFIRMED, {
            "proposal_id": proposal_id, "confirmation_token": token.token_id,
        })
        return {"ok": True, "proposal_id": proposal_id,
                "confirmation_token": token.token_id,
                "requires_confirmation": True}

    def approve(self, token: str) -> dict:
        """Approve a pending confirmation token (UI confirmation step)."""
        if self._cs is None:
            return {"ok": False, "code": "CONFIRMATION_UNAVAILABLE"}
        request = self._cs.approve(token)
        if request is None:
            return {"ok": False, "code": "INVALID_CONFIRMATION_TOKEN"}
        return {"ok": True, "operation_id": request.operation_id}

    def apply_batch(self, confirmations: list[dict], ctx=None) -> dict:
        """Apply confirmed proposals atomically per track.

        Each confirmation entry carries ``proposal_id`` plus an approved
        ``confirmation_token`` issued by ConfirmationService. Self-declared
        ``confirmed=True`` / ``source=`` entries WITHOUT a token are rejected
        with TOKEN_REQUIRED and land in ``missing_confirmations`` (never
        applied).

        Authorization is enforced per entry:

        - command_hash must match the proposal (TOKEN_COMMAND_MISMATCH)
        - target_hash must match the proposal track refs (TOKEN_TARGET_MISMATCH)
        - requested fields must be ⊆ token.selected_fields (TOKEN_FIELD_MISMATCH)
        - token must be approved, unexpired and single-use not consumed.

        effective_fields = proposal.fields ∩ token.selected_fields — fields
        the token did not select are NEVER applied. After each track write the
        DB value and the physical tag are read back per field
        (VERIFIED/DB_MISMATCH/TAG_MISMATCH/READ_ERROR/UNSUPPORTED_TAG/
        FILE_MISSING); ``ok`` is True ONLY when every non-skipped track
        verified. Unverified tracks are compensated (DB restore + backup).

        Returns real counters: requested, applied, failed, skipped,
        conflicts, missing_confirmations, rollback_performed, per_track.
        """
        if not confirmations:
            return self._batch_result(0, 0, 0, 0, 0, 0, False, [],
                                      "COMPLETED")
        self.cleanup_backups()
        requested = 0
        applied = 0
        failed = 0
        skipped = 0
        conflicts = 0
        missing_confirmations = 0
        rollback_performed = False
        per_track: list[dict[str, Any]] = []
        operation_id = ""
        compensated: list[dict[str, Any]] = []
        proposal = None
        rejection_code = ""

        try:
            for entry in confirmations:
                proposal_id = entry.get("proposal_id")
                proposal = self._proposals.get(proposal_id)
                if proposal is None:
                    return {"ok": False, "code": "PROPOSAL_NOT_FOUND",
                            "message": f"Unknown proposal: {proposal_id}"}
                confirmed, reason, token = self._check_confirmation(entry,
                                                                    proposal)
                if not confirmed:
                    missing_confirmations += len(proposal.track_refs)
                    if not rejection_code:
                        rejection_code = reason
                    for ref in proposal.track_refs:
                        per_track.append({
                            "filepath": ref.get("filepath", ""),
                            "track_id": ref.get("track_id"),
                            "status": "missing_confirmation",
                            "reason": reason,
                        })
                    continue

                effective_fields = {
                    k: v for k, v in proposal.fields.items()
                    if not token.selected_fields or k in token.selected_fields
                }
                if not effective_fields:
                    missing_confirmations += len(proposal.track_refs)
                    if not rejection_code:
                        rejection_code = "TOKEN_FIELD_MISMATCH"
                    for ref in proposal.track_refs:
                        per_track.append({
                            "filepath": ref.get("filepath", ""),
                            "track_id": ref.get("track_id"),
                            "status": "missing_confirmation",
                            "reason": "TOKEN_FIELD_MISMATCH",
                        })
                    continue

                operation_id = f"metadata_batch:{proposal_id}"
                entry_succeeded = True
                for ref in proposal.track_refs:
                    requested += 1
                    if ctx is not None:
                        ctx.token.raise_if_cancelled()
                        ctx.report_progress(
                            min(applied + failed, requested) / max(requested, 1),
                            ref.get("filepath", ""),
                        )
                    fp = ref.get("filepath", "")
                    track_id = ref.get("track_id") or self._resolve_track_id(fp)
                    if track_id is None:
                        skipped += 1
                        per_track.append({
                            "filepath": fp, "track_id": None,
                            "status": "skipped",
                            "reason": "TRACK_NOT_IN_DB",
                        })
                        continue
                    result = self._apply_track(proposal, fp, track_id,
                                               effective_fields)
                    per_track.append(result)
                    if result["status"] == "applied":
                        applied += 1
                        compensated.append(result["compensation"])
                    elif result["status"] == "conflict":
                        conflicts += 1
                    elif result["status"] == "failed":
                        failed += 1
                        entry_succeeded = False
                        if result.get("rolled_back"):
                            rollback_performed = True
                if entry_succeeded and token is not None and self._cs is not None:
                    self._cs.consume(token.token_id)

            if applied > 0 and self._undo is not None and proposal is not None:
                self._register_undo(operation_id, proposal, compensated)
        except Exception as error:  # noqa: BLE001
            if isinstance(error, CancelledError):
                return self._batch_result(
                    requested, applied, failed, skipped, conflicts,
                    missing_confirmations, rollback_performed, per_track,
                    "CANCELLED",
                )
            logger.exception("apply_batch failed")
            return self._batch_result(
                requested, applied, failed, skipped, conflicts,
                missing_confirmations, rollback_performed, per_track,
                "FAILED", error=str(error),
            )

        ok = (failed == 0 and conflicts == 0 and applied > 0)
        if applied == 0 and (failed > 0 or conflicts > 0):
            status = "FAILED"
        elif ok:
            status = "COMPLETED"
        else:
            status = "PARTIAL_SUCCESS"
        result = self._batch_result(
            requested, applied, failed, skipped, conflicts,
            missing_confirmations, rollback_performed, per_track, status,
            operation_id=operation_id,
            code=rejection_code if missing_confirmations else "",
        )
        self._emit(EVENT_BATCH_APPLIED, {
            "proposal_id": confirmations[0].get("proposal_id", ""),
            "requested": requested, "applied": applied, "failed": failed,
            "skipped": skipped, "conflicts": conflicts,
            "missing_confirmations": missing_confirmations,
            "rollback_performed": rollback_performed,
            "status": status,
        })
        return result

    @staticmethod
    def _batch_result(requested, applied, failed, skipped, conflicts,
                      missing_confirmations, rollback_performed, per_track,
                      status: str, *, operation_id: str = "",
                      error: str = "", code: str = "") -> dict:
        ok = (failed == 0 and conflicts == 0 and applied > 0
              and status != "CANCELLED")
        return {
            "ok": ok,
            "status": status,
            "requested": requested,
            "applied": applied,
            "failed": failed,
            "skipped": skipped,
            "conflicts": conflicts,
            "missing_confirmations": missing_confirmations,
            "rollback_performed": rollback_performed,
            "per_track": per_track,
            "operation_id": operation_id,
            "error": error,
            "code": code,
        }

    def _check_confirmation(self, entry: dict, proposal: MetadataProposal):
        """Token-only authorization; never accepts self-declared sources."""
        token_id = str(entry.get("confirmation_token") or "")
        if self._cs is None or not token_id:
            return False, "TOKEN_REQUIRED", None
        token = self._cs.get_token(token_id)
        if token is None:
            return False, "TOKEN_REQUIRED", None
        # A proposal that was never confirmed has no command hash of its own:
        # fall back to the canonical default hash so the token cannot be
        # repurposed for an unconfirmed proposal.
        command_hash = proposal.command_hash or self._default_command_hash(proposal)
        requested = tuple(
            entry.get("fields")
            or entry.get("selected_fields")
            or proposal.selected_fields
            or list(proposal.fields)
        )
        ok, code = self._cs.validate(
            token_id,
            command_hash=command_hash,
            target_hash=self._proposal_target_hash(proposal),
            requested_fields=requested,
        )
        if not ok:
            return False, code, None
        return True, "TOKEN_OK", token

    def _apply_track(self, proposal: MetadataProposal, fp: str,
                     track_id: int, effective_fields: dict | None = None) -> dict:
        """Apply one track: DB first, physical tags second, then verify.

        Only ``effective_fields`` (proposal fields authorized by the token)
        are written. After the write each field is read back from the DB and
        the physical tag; an unverified track is compensated (DB restore +
        backup copy) and reported as failed — never as applied.
        """
        db_changes = {
            field: str(value)
            for field, value in (effective_fields or proposal.fields).items()
        }
        old_values = self._read_db_values(track_id, db_changes)

        file_exists = bool(fp) and os.path.isfile(fp)
        if fp and not file_exists:
            return {
                "filepath": fp, "track_id": track_id,
                "status": "conflict", "error": "FILE_NOT_FOUND",
                "rolled_back": False,
            }

        backup_path = ""
        if file_exists:
            backup_path = self._backup_file(fp)

        db_ok = True
        if db_changes:
            result = self._apply_db_fields(track_id, db_changes)
            db_ok = result.get("ok", False)

        tag_ok = True
        if file_exists and db_changes:
            tag_ok = self._apply_physical_tags(fp, db_changes)
            if not tag_ok and backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, fp)

        if not db_ok or not tag_ok:
            if db_ok:
                self._restore_db_values(track_id, old_values)
            return {
                "filepath": fp, "track_id": track_id,
                "status": "failed",
                "error": "PHYSICAL_WRITE_FAILED" if db_ok else "DB_UPDATE_FAILED",
                "rolled_back": bool(backup_path) or db_ok,
            }

        readback = self._verify_track(fp, track_id, db_changes)
        if not readback["ok"]:
            self._restore_db_values(track_id, old_values)
            with suppress(OSError):
                if backup_path and os.path.exists(backup_path):
                    shutil.copy2(backup_path, fp)
                    os.unlink(backup_path)
            return {
                "filepath": fp, "track_id": track_id,
                "status": "failed",
                "error": readback["code"],
                "rolled_back": True,
                "readback": readback,
            }

        compensation = {
            "track_id": track_id,
            "filepath": fp,
            "old_values": old_values,
            "backup_path": backup_path,
        }
        return {"filepath": fp, "track_id": track_id, "status": "applied",
                "fields": list(db_changes), "compensation": compensation,
                "readback": readback}

    def _verify_track(self, fp: str, track_id: int,
                      expected: dict[str, Any]) -> dict:
        """Per-field readback: expected DB value vs actual, expected tag vs actual.

        In memory-only mode (``db=None``) no DB readback is possible: every
        field is reported READ_ERROR and the operation is rolled back — the
        caller must inject a real database for productive use.
        """
        ok = True
        code = ""
        item = None
        if self._db is not None:
            try:
                item = self._db.get_media_item_by_id(track_id)
            except Exception:  # noqa: BLE001
                item = None
        statuses = self._readback_statuses(fp, item, expected)
        for status in statuses.values():
            if not status["ok"]:
                ok = False
                code = code or (
                    status["db"] if status["db"] != RB_VERIFIED
                    else status["tag"])
        return {"ok": ok, "code": code or "VERIFIED", "fields": statuses}

    def _apply_db_fields(self, track_id: int, db_changes: dict) -> dict:
        if self._mutation is not None and hasattr(self._mutation,
                                                  "update_media_fields"):
            result = self._mutation.update_media_fields(track_id, db_changes)
            if isinstance(result, OperationResult):
                return result.to_dict()
            return result if isinstance(result, dict) else {
                "ok": bool(result), "code": "DB_UPDATE_FAILED",
            }
        if self._db is not None and hasattr(self._db, "update_media_item_field"):
            for field, value in db_changes.items():
                if not self._db.update_media_item_field(track_id, field, value):
                    return {"ok": False, "code": "DB_UPDATE_FAILED",
                            "field": field}
            return {"ok": True}
        if self._db is not None and hasattr(self._db, "conn"):
            try:
                with self._db.conn:
                    for field, value in db_changes.items():
                        self._db.conn.execute(
                            f"UPDATE media_items SET {field}=? WHERE id=?",
                            (value, track_id),
                        )
                return {"ok": True}
            except Exception as error:  # noqa: BLE001
                return {"ok": False, "code": "DB_UPDATE_FAILED",
                        "error": str(error)}
        return {"ok": False, "code": "NO_DB"}

    def _apply_physical_tags(self, fp: str, db_changes: dict) -> bool:
        reader = self._tag_reader or self._default_reader()
        writer = self._tag_writer or self._default_writer()
        try:
            tags = reader(fp)
            if tags is None:
                return False
            for field, value in db_changes.items():
                tag_field = _DB_TO_TAG.get(field)
                if tag_field and value is not None:
                    tags.set_field(tag_field, str(value))
            if not tags.dirty:
                return True
            return bool(writer(tags))
        except Exception as error:  # noqa: BLE001
            logger.debug("physical tag write failed for %s: %s", fp, error)
            return False

    def readback(self, proposal_id: str = "", filepaths: list[str] | None = None,
                 expected: dict | None = None) -> dict:
        """Verify DB and physical tags after an apply (readback authority).

        ``expected`` maps filepath -> {field: value} (or a single
        {field: value} applied to every target). When provided, every field
        gets a per-field status: VERIFIED / DB_MISMATCH / TAG_MISMATCH /
        READ_ERROR / UNSUPPORTED_TAG / FILE_MISSING.
        """
        targets: list[str] = []
        if filepaths:
            targets = list(filepaths)
        elif proposal_id and proposal_id in self._proposals:
            targets = [r.get("filepath", "") for r in
                       self._proposals[proposal_id].track_refs]
        expected_per_fp: dict = {}
        if expected:
            for key, value in expected.items():
                if isinstance(value, dict):
                    expected_per_fp[key] = value
                else:
                    expected_per_fp.setdefault("__all__", {})[key] = value
        results = []
        for fp in targets:
            if not fp:
                continue
            item = self._get_item(fp)
            db_values = {}
            if item is not None:
                for field, db_col in _FIELD_TO_DB.items():
                    db_values[field] = str(getattr(item, db_col, "") or "")
            physical = {}
            reader = self._tag_reader or self._default_reader()
            try:
                tags = reader(fp) if fp and os.path.isfile(fp) else None
                if tags is not None:
                    for field in _FIELD_TO_DB:
                        tag_field = _DB_TO_TAG.get(field)
                        if tag_field:
                            physical[field] = str(getattr(tags, tag_field, "") or "")
            except Exception:  # noqa: BLE001
                physical = {}
            entry: dict[str, Any] = {
                "filepath": fp,
                "db": db_values,
                "physical": physical,
            }
            want = dict(expected_per_fp.get("__all__", {}))
            want.update(expected_per_fp.get(fp, {}))
            if want:
                entry["status"] = self._readback_statuses(fp, item, want)
            results.append(entry)
        self._emit(EVENT_READBACK_COMPLETED, {
            "proposal_id": proposal_id, "track_count": len(results),
        })
        return {"ok": True, "results": results}

    def _readback_statuses(self, fp: str, item, expected: dict) -> dict:
        """Per-field readback statuses for one file (used by readback())."""
        statuses: dict[str, str] = {}
        file_exists = bool(fp) and os.path.isfile(fp)
        tags = None
        reader = self._tag_reader or self._default_reader()
        if file_exists:
            try:
                tags = reader(fp)
            except Exception:  # noqa: BLE001
                tags = None
        for field, value in expected.items():
            db_col = _FIELD_TO_DB.get(field, field)
            if item is None:
                db_status = RB_READ_ERROR
            else:
                actual = str(getattr(item, db_col, "") or "")
                db_status = (RB_VERIFIED if str(actual) == str(value)
                             else RB_DB_MISMATCH)
            if not file_exists:
                tag_status = RB_FILE_MISSING
            else:
                tag_field = _DB_TO_TAG.get(field)
                if tag_field is None:
                    tag_status = RB_UNSUPPORTED_TAG
                elif tags is None:
                    tag_status = RB_READ_ERROR
                else:
                    actual = str(getattr(tags, tag_field, "") or "")
                    tag_status = (RB_VERIFIED if str(actual) == str(value)
                                  else RB_TAG_MISMATCH)
            statuses[field] = {
                "db": db_status,
                "tag": tag_status,
                "ok": db_status == RB_VERIFIED and tag_status == RB_VERIFIED,
            }
        return statuses

    def undo(self, operation_id: str) -> dict:
        """Real compensation via UndoService."""
        if self._undo is None:
            return {"ok": False, "code": "UNDO_UNAVAILABLE",
                    "message": "No UndoService injected"}
        result = self._undo.undo(operation_id)
        if not result.ok:
            return {"ok": False, "code": result.code,
                    "message": result.message}
        return {"ok": True, "operation_id": operation_id,
                "status": "UNDONE", "description": result.data.get("description")}

    def apply_single(self, proposal_id: str,
                     confirmation_token: str = "") -> dict:
        """Apply a single-track proposal (bridge confirmSave path).

        Requires an approved ConfirmationToken issued for this proposal —
        self-declared sources are rejected (TOKEN_REQUIRED).
        """
        result = self.apply_batch([{
            "proposal_id": proposal_id,
            "confirmation_token": confirmation_token,
        }])
        return {
            "ok": result["ok"],
            "status": result["status"],
            "applied": result["applied"],
            "failed": result["failed"],
            "conflicts": result["conflicts"],
            "per_track": result["per_track"],
            "operation_id": result["operation_id"],
            "code": result["error"] or result.get("code")
            or ("OK" if result["ok"] else "APPLY_FAILED"),
        }

    # ── helpers ──────────────────────────────────────────────────────────

    def _register_undo(self, operation_id: str, proposal: MetadataProposal,
                       compensated: list[dict]) -> None:
        description = (f"Deshacer edición de metadatos "
                       f"({len(compensated)} pista(s), "
                       f"{', '.join(proposal.fields)})")

        def compensate() -> dict:
            restored = 0
            errors = []
            for track in compensated:
                try:
                    self._restore_db_values(track["track_id"],
                                            track["old_values"])
                    backup = track.get("backup_path")
                    if backup and os.path.exists(backup):
                        shutil.copy2(backup, track["filepath"])
                        os.unlink(backup)
                    restored += 1
                except Exception as error:  # noqa: BLE001
                    errors.append(str(error))
            return {"restored": restored, "errors": errors}

        compensation_data = {
            "kind": "metadata_batch",
            "tracks": [
                {
                    "track_id": track["track_id"],
                    "filepath": track["filepath"],
                    "old_values": dict(track["old_values"]),
                    "backup_path": track.get("backup_path", ""),
                }
                for track in compensated
            ],
        }
        self._undo_ctx[operation_id] = {
            "compensated": compensated,
            "proposal_id": proposal.proposal_id,
        }
        self._undo.register(
            operation_id, description, compensate,
            entity=",".join(r.get("filepath", "") for r in proposal.track_refs),
            kind="metadata_batch",
            metadata={"proposal_id": proposal.proposal_id,
                      "field_count": len(compensated)},
            compensation_data=compensation_data,
        )

    def _restore_db_values(self, track_id: int, old_values: dict) -> None:
        if self._mutation is not None and hasattr(self._mutation,
                                                  "update_media_fields"):
            self._mutation.update_media_fields(track_id, old_values)
        elif self._db is not None and hasattr(self._db, "update_media_item_field"):
            for field, value in old_values.items():
                self._db.update_media_item_field(track_id, field, value)

    def _read_db_values(self, track_id: int, fields: dict) -> dict:
        old = {}
        item = None
        if self._db is not None:
            try:
                item = self._db.get_media_item_by_id(track_id)
            except Exception:  # noqa: BLE001
                item = None
        if item is not None:
            for field in fields:
                db_col = _FIELD_TO_DB.get(field, field)
                old[field] = str(getattr(item, db_col, "") or "")
        return old

    def _resolve_track_id(self, fp: str) -> int | None:
        if not fp or self._db is None:
            return None
        try:
            row = self._db.conn.execute(
                "SELECT id FROM media_items WHERE filepath=? "
                "AND deleted_at IS NULL",
                (fp,),
            ).fetchone()
            return int(row[0]) if row else None
        except Exception:  # noqa: BLE001
            return None

    def read_media_item(self, track_id: int):
        """Public read port: return the media item row for *track_id*.

        Lets consumers (e.g. the library doctor readback) read track state
        without reaching into the editor's private database handle.
        """
        if self._db is None or not track_id:
            return None
        try:
            return self._db.get_media_item_by_id(track_id)
        except Exception:  # noqa: BLE001
            return None

    def _get_item(self, fp: str):
        if not fp or self._db is None:
            return None
        track_id = self._resolve_track_id(fp)
        if track_id is None:
            return None
        try:
            return self._db.get_media_item_by_id(track_id)
        except Exception:  # noqa: BLE001
            return None

    def _get_item_for_ref(self, ref: dict):
        if self._db is None:
            return None
        track_id = ref.get("track_id")
        if not track_id:
            return self._get_item(ref.get("filepath", ""))
        try:
            return self._db.get_media_item_by_id(int(track_id))
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _default_command_hash(proposal: MetadataProposal) -> str:
        payload = {
            "track_refs": proposal.track_refs,
            "fields": proposal.fields,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode(),
        ).hexdigest()[:16]

    @staticmethod
    def _proposal_target_hash(proposal: MetadataProposal) -> str:
        """Stable hash of the proposal's target entities (track refs)."""
        return compute_target_hash(proposal.track_refs)

    @staticmethod
    def _default_reader() -> Callable:
        from metadata.tag_reader import read_tags
        return read_tags

    @staticmethod
    def _default_writer() -> Callable:
        from metadata.tag_writer import write_tags
        return write_tags

    @staticmethod
    def backup_dir() -> str:
        return os.path.join(tempfile.gettempdir(), _BACKUP_DIR_NAME)

    @classmethod
    def cleanup_backups(cls, max_age_days: int = BACKUP_RETENTION_DAYS) -> int:
        """Remove backups older than the retention policy (undo window).

        Policy: a physical-tag backup is kept for ``max_age_days`` (default
        BACKUP_RETENTION_DAYS = 7) — enough for the undo window — and is also
        deleted when the undo compensation consumes it. Called automatically
        at the start of every ``apply_batch``.
        """
        backup_dir = cls.backup_dir()
        if not os.path.isdir(backup_dir):
            return 0
        cutoff = time.time() - max_age_days * 86400
        removed = 0
        try:
            for name in os.listdir(backup_dir):
                path = os.path.join(backup_dir, name)
                try:
                    if not os.path.isfile(path) or not name.endswith(".bak"):
                        continue
                    if os.path.getmtime(path) < cutoff:
                        os.unlink(path)
                        removed += 1
                except OSError:
                    continue
        except OSError:
            return removed
        return removed

    @classmethod
    def _backup_file(cls, fp: str) -> str:
        backup_dir = cls.backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        backup = os.path.join(
            backup_dir,
            f"{os.path.basename(fp)}_{int(time.time() * 1000)}.bak",
        )
        shutil.copy2(fp, backup)
        return backup

    def _emit(self, event: str, data: dict) -> None:
        if self._eb is None or not hasattr(self._eb, "emit"):
            return
        try:
            self._eb.emit(event, data)
        except Exception:  # noqa: BLE001
            logger.debug("metadata editor event emit failed", exc_info=True)

    # ── legacy single-file surface (kept for existing callers/tests) ─────

    def update_metadata(self, track_id: int, data: dict) -> dict:
        """Legacy DB-only API — disabled (LEGACY_OPERATION_DISABLED).

        No production consumer exists; all metadata edits must go through the
        canonical proposal→token→apply pipeline.
        """
        return {"ok": False, "code": "LEGACY_OPERATION_DISABLED",
                "error": "LEGACY_OPERATION_DISABLED",
                "message": "update_metadata is disabled; use the canonical "
                           "proposal→token→apply pipeline"}

    def batch_update(self, updates: list[dict]) -> dict:
        """Legacy DB-only API — disabled (LEGACY_OPERATION_DISABLED)."""
        return {"ok": False, "code": "LEGACY_OPERATION_DISABLED",
                "error": "LEGACY_OPERATION_DISABLED",
                "message": "batch_update is disabled; use the canonical "
                           "proposal→token→apply pipeline"}

    def preview(self, filepath: str, changes: dict) -> dict:
        return {"ok": True, "filepath": filepath, "changes": changes,
                "preview": changes}

    def apply(self, filepath: str, changes: dict) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            track_id = self._resolve_track_id(filepath)
            if track_id is None:
                return {"ok": False, "error": "TRACK_NOT_FOUND"}
            db_changes = {
                field: value for field, value in changes.items()
                if field in _FIELD_TO_DB
            }
            result = self._apply_db_fields(track_id, db_changes)
            if not result.get("ok"):
                return result
            return {"ok": True, "applied": list(db_changes.keys())}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rollback(self, filepath: str, field: str,
                 previous_value: Any) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            track_id = self._resolve_track_id(filepath)
            if track_id is None:
                return {"ok": False, "error": "TRACK_NOT_FOUND"}
            db_col = _FIELD_TO_DB.get(field, field)
            result = self._apply_db_fields(track_id, {db_col: previous_value})
            return result if result.get("ok") else {
                "ok": False, "error": result.get("code", "DB_UPDATE_FAILED"),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def health(self) -> dict:
        return {
            "available": self._db is not None,
            "undo_available": self._undo is not None,
            "confirmation_available": self._cs is not None,
            "proposals_pending": len(self._proposals),
            "backup_retention_days": BACKUP_RETENTION_DAYS,
        }

    def shutdown(self):
        self._proposals.clear()
        self._undo_ctx.clear()
