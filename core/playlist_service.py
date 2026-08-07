"""PlaylistService — business logic for playlist CRUD, import/export, transactions.

Debt D1 (atomic playlist import): batch additions and file imports honour an
explicit policy (ATOMIC_ROLLBACK / PARTIAL_COMMIT / SKIP_INVALID) that is
returned in every result. Cancellation is cooperative through ``ctx`` and
``cancel_import`` routes to the real DurableJobService — never nominal.
"""
from __future__ import annotations

import logging
import json
import os
from pathlib import Path
from typing import Any

from core.worker_manager import CancelledError


logger = logging.getLogger("michi.playlist_service")

# Batch/import policies (debt D1).
ATOMIC_ROLLBACK = "ATOMIC_ROLLBACK"
PARTIAL_COMMIT = "PARTIAL_COMMIT"
SKIP_INVALID = "SKIP_INVALID"
POLICIES = {ATOMIC_ROLLBACK, PARTIAL_COMMIT, SKIP_INVALID}

# Cancellation is checked every N tracks during batch/import loops (debt D1).
CANCEL_CHECK_EVERY = 25

# Terminal job states that make a job no longer cancellable (debt D1).
_TERMINAL_JOB_STATES = {
    "SUCCEEDED", "PARTIAL_SUCCESS", "FAILED", "CANCELLED", "INTERRUPTED",
}


class PlaylistTransaction:
    """Real SQLite transaction over ``db.conn`` (debt D1).

    ``begin`` issues an explicit ``BEGIN`` so the caller's mutations are a
    single unit; ``commit``/``rollback`` finalize it on the same connection.
    Without a connection the methods are honest no-ops — never a fake
    success returned for an operation that cannot be performed.
    """

    def __init__(self, db: Any | None = None) -> None:
        self._db = db
        self._active = False

    def begin(self) -> None:
        if self._active:
            return
        if self._db is None or not hasattr(self._db, "conn"):
            return
        self._db.conn.execute("BEGIN")
        self._active = True

    def commit(self) -> None:
        if not self._active:
            return
        self._db.conn.commit()
        self._active = False

    def rollback(self) -> None:
        if not self._active:
            return
        self._db.conn.rollback()
        self._active = False


class PlaylistService:
    """Own playlist persistence and ordered track membership."""

    def __init__(self, db: Any | None = None,
                 job_service: Any | None = None) -> None:
        self._db = db
        self._job_service = job_service
        self._txn = PlaylistTransaction(db) if db else None

    def _can(self) -> bool:
        return self._db is not None and hasattr(self._db, 'get_playlists')

    def _error(self, code: str, message: str = "") -> dict[str, Any]:
        return {"ok": False, "error_code": code, "message": message}

    def _ok(self, **kw: Any) -> dict[str, Any]:
        result = {"ok": True}
        result.update(kw)
        return result

    def begin(self) -> dict:
        if self._txn:
            self._txn.begin()
        return self._ok()

    def commit(self) -> dict:
        if self._txn:
            self._txn.commit()
        return self._ok()

    def rollback(self) -> dict:
        if self._txn:
            self._txn.rollback()
        return self._ok()

    def list(self) -> list[dict]:
        if not self._can():
            return []
        try:
            plists = self._db.get_playlists()
            return [
                {
                    "id": p.get("id", 0) if isinstance(p, dict) else getattr(p, 'id', 0),
                    "name": p.get("name", "") if isinstance(p, dict) else getattr(p, 'name', ''),
                    "track_count": p.get("track_count", 0) if isinstance(p, dict) else getattr(p, 'track_count', 0),
                }
                for p in plists
            ]
        except Exception:
            return []

    def create_playlist(self, name: str) -> dict:
        return self.create(name)

    def rename_playlist(self, pid: int, name: str) -> dict:
        return self.rename(pid, name)

    def delete_playlist(self, pid: int) -> dict:
        return self.delete(pid)

    def add_to_playlist(self, pid: int, filepath: str) -> dict:
        return self.add_track(pid, filepath)

    def import_m3u(self, path: str) -> dict:
        """Legacy alias: import an M3U file with SKIP_INVALID semantics."""
        return self.import_playlist_file(path, policy=SKIP_INVALID)

    def import_playlist_file(self, path: str,
                             target_name: str | None = None,
                             policy: str = SKIP_INVALID,
                             ctx: Any | None = None) -> dict:
        """Import a playlist file honouring *policy* (debt D1).

        Parses via ``core.playlist_io``, creates the playlist (inside the
        same transaction when policy is ATOMIC_ROLLBACK) and adds every
        entry through the policy-aware batch path. The result always
        carries the policy plus requested/added/skipped/failed/duplicates/
        missing/rollback_performed counters.
        """
        if not self._can():
            return self._error("NO_DB")
        if policy not in POLICIES:
            return self._error("INVALID_POLICY", f"Unknown policy {policy!r}")
        p = Path(path)
        if not p.is_file():
            return self._error("FILE_NOT_FOUND")
        # Warm the lazy FTS index BEFORE any transaction (debt D1).
        _ = self._db.conn
        try:
            from core.playlist_io import parse_playlist_entries
            entries = parse_playlist_entries(path)
        except Exception as e:
            return self._error("PARSE_FAILED", str(e))
        # Remote streams can never be imported as local tracks; they are
        # reported as missing (unavailable locally) by the batch path.
        refs = [e.resolved_path for e in entries if not e.is_remote]
        if not refs or not any(os.path.exists(fp) for fp in refs):
            return self._error("NO_VALID_TRACKS", "No existing tracks in playlist file")
        name = (target_name or p.stem)[:80] or "Imported"
        if policy == ATOMIC_ROLLBACK:
            return self._import_file_atomic(name, refs, ctx)
        created = self.create(name)
        if not created.get("ok"):
            return created
        pid = created["id"]
        added = self.add_tracks(pid, refs, policy=policy, ctx=ctx)
        result = {
            "ok": added.get("ok", False),
            "status": added.get("status"),
            "policy": policy,
            "playlist_id": pid,
            "id": pid,
            "name": name,
            "count": added.get("added", 0),
            "requested": added.get("requested", 0),
            "added": added.get("added", 0),
            "skipped": added.get("skipped", 0),
            "failed": added.get("failed", 0),
            "duplicates": added.get("duplicates", 0),
            "missing": added.get("missing", []),
            "rollback_performed": added.get("rollback_performed", False),
        }
        if not added.get("ok"):
            result["error"] = added.get("error", "IMPORT_FAILED")
            result["error_code"] = added.get("error_code", "IMPORT_FAILED")
        return result

    def _import_file_atomic(self, name: str, refs: list[str],
                            ctx: Any | None = None) -> dict:
        """ATOMIC_ROLLBACK import: playlist row + membership, one transaction."""
        result = self._batch_base(ATOMIC_ROLLBACK)
        result["requested"] = len(refs)
        try:
            self._txn.begin()
            cur = self._db.conn.execute(
                "INSERT INTO playlists (name) VALUES (?)", (name.strip(),))
            pid = int(cur.lastrowid)
            outcome = self._atomic_loop(pid, refs, ctx, result)
            if not outcome.get("ok"):
                self._txn.rollback()
                outcome["rollback_performed"] = True
                outcome["added"] = 0
                return outcome
            self._txn.commit()
            outcome["playlist_id"] = pid
            outcome["id"] = pid
            outcome["name"] = name
            return outcome
        except CancelledError:
            self._rollback_txn()
            return self._cancelled_result(ATOMIC_ROLLBACK, rollback_performed=True)
        except Exception as e:
            self._rollback_txn()
            result["error"] = str(e)
            result["error_code"] = "IMPORT_ROLLED_BACK"
            result["failed"] = max(result.get("failed", 0), 1)
            result["rollback_performed"] = True
            result["ok"] = False
            result["status"] = "FAILED"
            return result

    def export_m3u(self, pid: int, output_path: str = "") -> dict:
        from core.playlist_io import export_m3u
        items = self.items(pid) if hasattr(self, 'items') else []
        if not items:
            return {"ok": False, "error": "EMPTY_PLAYLIST"}
        filepaths = [i.get("filepath", i.get("path", "")) for i in items if i.get("filepath") or i.get("path")]
        if not output_path:
            name = "playlist"
            for p in self.list():
                if p.get("id") == pid:
                    name = p.get("name", "playlist")
                    break
            output_path = f"{name}.m3u"
        try:
            export_m3u(output_path, filepaths)
            return {"ok": True, "path": output_path, "count": len(filepaths)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def create(self, name: str) -> dict:
        if not self._can():
            return self._error("NO_DB")
        if not name or not name.strip():
            return self._error("EMPTY_NAME")
        try:
            pid = self._db.create_playlist(name.strip())
            return self._ok(id=pid, name=name.strip())
        except Exception as e:
            return self._error("CREATE_FAILED", str(e))

    def rename(self, pid: int, name: str) -> dict:
        if not self._can():
            return self._error("NO_DB")
        if not name or not name.strip():
            return self._error("EMPTY_NAME")
        try:
            self._db.update_playlist(pid, name=name.strip())
            return self._ok()
        except Exception as e:
            return self._error("RENAME_FAILED", str(e))

    def delete(self, pid: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            self._db.delete_playlist(pid)
            return self._ok()
        except Exception as e:
            return self._error("DELETE_FAILED", str(e))

    def duplicate(self, pid: int, new_name: str = "") -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            items = self._get_items_internal(pid)
            if not items:
                return self._error("NO_TRACKS")
            orig_name = ""
            for p in self.list():
                if p.get("id") == pid:
                    orig_name = p.get("name", "")
                    break
            name = new_name or f"{orig_name} (copia)"
            new_pid = self._db.create_playlist(name)
            for t in items:
                fp = t.get("filepath", "")
                if fp:
                    self._db.add_track_to_playlist(new_pid, filepath=fp)
            return self._ok(id=new_pid, name=name, count=len(items))
        except Exception as e:
            return self._error("DUPLICATE_FAILED", str(e))

    def add_track(self, pid: int, track_id: int = 0, filepath: str = "") -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            if track_id:
                self._db.add_track_to_playlist(pid, track_id=track_id)
            elif filepath:
                self._db.add_track_to_playlist(pid, filepath=filepath)
            else:
                return self._error("NO_TRACK_ID")
            return self._ok()
        except Exception as e:
            return self._error("ADD_TRACK_FAILED", str(e))

    def remove_track(self, pid: int, track_id: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            self._db.remove_track_from_playlist(pid, track_id)
            return self._ok()
        except Exception as e:
            return self._error("REMOVE_TRACK_FAILED", str(e))

    def reorder(self, pid: int, from_index: int, to_index: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            if hasattr(self._db, 'reorder_playlist_track'):
                self._db.reorder_playlist_track(pid, from_index, to_index)
                return self._ok()
            return self._error("UNSUPPORTED")
        except Exception as e:
            return self._error("REORDER_FAILED", str(e))

    def get_detail(self, pid: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            plists = self.list()
            if not any(p.get("id") == pid for p in plists):
                return self._error("NOT_FOUND", f"Playlist {pid} not found")
            items = self._get_items_internal(pid)
            tracks = [
                {
                    "track_id": t.get("track_id", 0),
                    "title": t.get("title", ""),
                    "artist": t.get("artist", ""),
                    "album": t.get("album", ""),
                    "duration": t.get("duration", 0),
                    "position": t.get("position", idx),
                }
                for idx, t in enumerate(items)
            ]
            return self._ok(tracks=tracks, count=len(tracks))
        except Exception as e:
            return self._error("DETAIL_FAILED", str(e))

    def _get_items_internal(self, pid: int) -> list[dict]:
        if not self._can():
            return []
        try:
            items = self._db.get_playlist_items(pid)
            return [
                {
                    "track_id": getattr(item, 'id', 0) if not isinstance(item, dict) else item.get("id", 0),
                    "track_uid": getattr(item, 'track_uid', '') if not isinstance(item, dict) else item.get("track_uid", ''),
                    "filepath": getattr(item, 'filepath', '') if not isinstance(item, dict) else item.get("filepath", ''),
                    "title": getattr(item, 'title', '') if not isinstance(item, dict) else item.get("title", ''),
                    "artist": getattr(item, 'artist', '') if not isinstance(item, dict) else item.get("artist", ''),
                    "album": getattr(item, 'album', '') if not isinstance(item, dict) else item.get("album", ''),
                    "duration": getattr(item, 'duration', 0) if not isinstance(item, dict) else item.get("duration", 0),
                    "position": idx,
                }
                for idx, item in enumerate(items)
            ]
        except Exception:
            return []

    def get_items_for_queue(self, pid: int) -> list[dict]:
        """Return ordered, metadata-rich playlist entries for QueueService."""
        return self._get_items_internal(pid)

    def update_description(self, pid: int, description: str) -> dict:
        if not self._can() or not hasattr(self._db, "update_playlist"):
            return self._error("NO_DB")
        self._db.update_playlist(pid, description=description)
        return self._ok(id=pid)

    def set_smart_rule(self, pid: int, rule: dict[str, Any]) -> dict:
        """Persist a validated smart-playlist rule through the service boundary."""
        if not self._can() or not hasattr(self._db, "update_playlist"):
            return self._error("NO_DB")
        try:
            self._db.update_playlist(pid, rules_json=json.dumps(rule))
            return self._ok(id=pid)
        except Exception as e:
            return self._error("SMART_RULE_FAILED", str(e))

    def import_preview(self, filepath: str) -> dict:
        if not filepath or not Path(filepath).is_file():
            return self._error("FILE_NOT_FOUND")
        try:
            from core.playlist_io import parse_playlist_entries
            entries = parse_playlist_entries(filepath)
            valid = sum(1 for entry in entries if entry.exists and not entry.is_remote)
            return self._ok(
                format=Path(filepath).suffix,
                name=Path(filepath).stem,
                total_entries=len(entries),
                valid_entries=valid,
                missing_entries=len(entries) - valid,
            )
        except Exception as e:
            return self._error("IMPORT_PREVIEW_FAILED", str(e))

    def import_confirm(self, filepath: str, name: str = "") -> dict:
        """Synchronous import (small files) with SKIP_INVALID semantics.

        Keeps the historical result shape ({ok, id, count, name}) as a
        superset of the policy-aware import result (debt D1).
        """
        if not filepath:
            return self._error("FILE_NOT_FOUND")
        if not self._can():
            return self._error("NO_DB")
        result = self.import_playlist_file(filepath, target_name=name,
                                           policy=SKIP_INVALID)
        if not result.get("ok"):
            return result
        return {
            "ok": True,
            "id": result["playlist_id"],
            "count": result.get("added", 0),
            "name": result["name"],
            "status": result.get("status"),
            "policy": result.get("policy"),
            "playlist_id": result["playlist_id"],
            "requested": result.get("requested", 0),
            "added": result.get("added", 0),
            "skipped": result.get("skipped", 0),
            "failed": result.get("failed", 0),
            "duplicates": result.get("duplicates", 0),
            "missing": result.get("missing", []),
            "rollback_performed": result.get("rollback_performed", False),
        }

    def export(self, pid: int, destination_path: str) -> dict:
        if not destination_path:
            return self._error("EMPTY_PATH")
        if not self._can():
            return self._error("NO_DB")
        try:
            from core.playlist_io import export_m3u
            items = self._get_items_internal(pid)
            if not items:
                return self._error("NO_TRACKS")
            fps = [t["filepath"] for t in items if t.get("filepath")]
            if not fps:
                return self._error("NO_VALID_TRACKS")
            export_m3u(destination_path, fps)
            return self._ok(count=len(fps))
        except Exception as e:
            return self._error("EXPORT_FAILED", str(e))

    def batch_add(self, pid: int, track_ids: list[int],
                  filepaths: list[str] | None = None) -> dict:
        """Legacy batch add — now delegates to :meth:`add_tracks`.

        PARTIAL_COMMIT semantics: valid tracks are added, failures are
        counted; ok is False when nothing could be added (never a blind
        success with unmarked failures — debt D1).
        """
        refs: list[Any] = [int(t) for t in (track_ids or [])]
        refs += [fp for fp in (filepaths or []) if fp]
        if not refs:
            return {"ok": False, "error_code": "EMPTY",
                    "message": "No tracks to add"}
        result = self.add_tracks(pid, refs, policy=PARTIAL_COMMIT)
        return {
            "ok": result.get("ok", False),
            "count": result.get("added", 0),
            "added": result.get("added", 0),
            "status": result.get("status"),
            "policy": result.get("policy"),
            "requested": result.get("requested", 0),
            "skipped": result.get("skipped", 0),
            "failed": result.get("failed", 0),
            "duplicates": result.get("duplicates", 0),
            "missing": result.get("missing", []),
            "rollback_performed": result.get("rollback_performed", False),
        }

    # ── Debt D1: policy-aware batch additions ──────────────────────────

    def add_tracks(self, playlist_id: int, track_refs: list[Any],
                   policy: str = SKIP_INVALID, ctx: Any | None = None) -> dict:
        """Add many tracks with an explicit *policy* (debt D1).

        *track_refs* items may be dicts ({track_id}/{filepath}), ints
        (track ids) or strings (file paths). A track already in the
        playlist is counted as a duplicate and never added twice.

        Result counters: requested, added, skipped, failed, duplicates,
        missing (list of unresolved refs), rollback_performed; ``status``
        is COMPLETED / PARTIAL_SUCCESS / FAILED and ``policy`` is echoed.
        Cancellation is cooperative through ``ctx.raise_if_cancelled()``
        checked every CANCEL_CHECK_EVERY tracks.
        """
        if not self._can():
            return self._error("NO_DB")
        if policy not in POLICIES:
            return self._error("INVALID_POLICY", f"Unknown policy {policy!r}")
        refs = list(track_refs or [])
        if not refs:
            return self._error("EMPTY", "No tracks to add")
        # Warm the lazy FTS index BEFORE any transaction: the first
        # ``db.conn`` access may rebuild media_fts and commit (debt D1).
        _ = self._db.conn
        if policy == ATOMIC_ROLLBACK:
            return self._add_tracks_atomic(playlist_id, refs, ctx)
        return self._add_tracks_loop(playlist_id, refs, policy, ctx)

    def _batch_base(self, policy: str) -> dict:
        return {
            "ok": True,
            "status": "COMPLETED",
            "policy": policy,
            "requested": 0,
            "added": 0,
            "skipped": 0,
            "failed": 0,
            "duplicates": 0,
            "missing": [],
            "rollback_performed": False,
        }

    def _rollback_txn(self) -> None:
        if self._txn is not None:
            self._txn.rollback()

    def _cancelled_result(self, policy: str,
                          rollback_performed: bool = False) -> dict:
        result = self._batch_base(policy)
        result["ok"] = False
        result["status"] = "CANCELLED"
        result["rollback_performed"] = rollback_performed
        return result

    def _add_tracks_atomic(self, pid: int, refs: list[Any],
                           ctx: Any | None = None) -> dict:
        """ATOMIC_ROLLBACK: one transaction; any failure rolls back all."""
        result = self._batch_base(ATOMIC_ROLLBACK)
        result["requested"] = len(refs)
        try:
            self._txn.begin()
            outcome = self._atomic_loop(pid, refs, ctx, result)
            if not outcome.get("ok"):
                self._txn.rollback()
                outcome["rollback_performed"] = True
                outcome["added"] = 0
                return outcome
            self._txn.commit()
            return outcome
        except CancelledError:
            self._rollback_txn()
            return self._cancelled_result(ATOMIC_ROLLBACK, rollback_performed=True)
        except Exception as e:
            self._rollback_txn()
            result["error"] = str(e)
            result["error_code"] = "BATCH_ROLLED_BACK"
            result["failed"] = max(result.get("failed", 0), 1)
            result["rollback_performed"] = True
            result["ok"] = False
            result["status"] = "FAILED"
            return result

    def _check_cancelled(self, ctx: Any, idx: int) -> None:
        """Cooperative cancellation check (debt D1).

        Both job ctx flavours expose the token (``_SyncContext`` and the
        worker ``TaskContext``); the token is the single cancellation
        authority. A ctx object with its own ``raise_if_cancelled`` (e.g.
        a test double) is honoured directly.
        """
        if ctx is None or idx % CANCEL_CHECK_EVERY != 0:
            return
        if hasattr(ctx, "raise_if_cancelled"):
            ctx.raise_if_cancelled()
        elif getattr(ctx, "token", None) is not None:
            ctx.token.raise_if_cancelled()

    def _atomic_loop(self, pid: int, refs: list[Any], ctx: Any | None,
                     result: dict) -> dict:
        """Validate + raw-insert loop inside an already-active transaction."""
        existing_tids, existing_fps = self._raw_membership(pid)
        for idx, ref in enumerate(refs):
            self._check_cancelled(ctx, idx)
            verdict, resolved = self._evaluate_ref(ref, existing_tids,
                                                    existing_fps)
            if verdict != "addable":
                if verdict == "duplicate":
                    result["duplicates"] += 1
                else:
                    result["missing"].append(self._ref_label(ref))
                    result["failed"] += 1
                result["ok"] = False
                result["status"] = "FAILED"
                return result
            self._insert_membership_raw(pid, resolved, self._fp_of(ref))
            existing_tids.add(resolved)
            result["added"] += 1
        return result

    def _add_tracks_loop(self, pid: int, refs: list[Any], policy: str,
                         ctx: Any | None = None) -> dict:
        """Per-track adds: PARTIAL_COMMIT counts failures; SKIP_INVALID
        counts invalid entries as skipped. Duplicates never double-add."""
        result = self._batch_base(policy)
        result["requested"] = len(refs)
        existing_tids, existing_fps = self._raw_membership(pid)
        try:
            for idx, ref in enumerate(refs):
                self._check_cancelled(ctx, idx)
                verdict, resolved = self._evaluate_ref(ref, existing_tids,
                                                       existing_fps)
                if verdict == "duplicate":
                    result["duplicates"] += 1
                    continue
                if verdict == "missing":
                    result["missing"].append(self._ref_label(ref))
                    if policy == SKIP_INVALID:
                        result["skipped"] += 1
                        continue
                    # PARTIAL_COMMIT keeps the tracks added before the
                    # first failure and stops there (debt D1 semantics).
                    result["failed"] += 1
                    break
                try:
                    self._db.add_track_to_playlist(
                        pid, track_id=resolved, filepath=self._fp_of(ref))
                    existing_tids.add(resolved)
                    result["added"] += 1
                except Exception:
                    result["failed"] += 1
        except CancelledError:
            return self._cancelled_result(policy, rollback_performed=False)
        if result["added"] == 0 and (result["failed"] or result["missing"]):
            result["ok"] = False
            result["status"] = "FAILED"
        elif result["added"] < result["requested"]:
            result["status"] = "PARTIAL_SUCCESS"
        return result

    # ── Ref classification helpers (debt D1) ───────────────────────────

    def _normalize_ref(self, ref: Any) -> tuple[int, str]:
        """Normalize a track reference to (track_id, filepath)."""
        if isinstance(ref, dict):
            tid = ref.get("track_id") or 0
            fp = ref.get("filepath") or ""
        elif isinstance(ref, int):
            tid, fp = ref, ""
        elif isinstance(ref, str):
            tid, fp = 0, ref
        else:
            return 0, ""
        return (int(tid) if tid else 0), str(fp or "")

    def _fp_of(self, ref: Any) -> str:
        return self._normalize_ref(ref)[1]

    def _ref_label(self, ref: Any) -> dict:
        tid, fp = self._normalize_ref(ref)
        return {"track_id": tid, "filepath": fp} if tid else {"filepath": fp}

    def _evaluate_ref(self, ref: Any, existing_tids: set[int],
                      existing_fps: set[str]) -> tuple[str, int]:
        """Classify one ref → ("addable", track_id) | ("duplicate", 0) |
        ("missing", 0).

        track_id refs must exist in media_items; filepath refs must exist
        on disk (legacy filepath-only membership is preserved when the file
        is not indexed). A DB that cannot answer the checks (e.g. a test
        double without the tables) accepts track_ids leniently.
        """
        tid, fp = self._normalize_ref(ref)
        if tid:
            if tid in existing_tids:
                return "duplicate", 0
            if not self._media_item_exists(tid):
                return "missing", 0
            return "addable", tid
        if fp:
            if fp in existing_fps:
                return "duplicate", 0
            if not os.path.exists(fp):
                return "missing", 0
            resolved = self._resolve_track_id(fp) or 0
            if resolved and resolved in existing_tids:
                return "duplicate", 0
            return "addable", resolved
        return "missing", 0

    def _media_item_exists(self, track_id: int) -> bool:
        try:
            row = self._db.conn.execute(
                "SELECT 1 FROM media_items WHERE id=?", (int(track_id),)
            ).fetchone()
            return row is not None
        except Exception:
            # Cannot verify (no media_items surface): accept leniently so
            # legacy callers on partial DB doubles keep working.
            return True

    def _resolve_track_id(self, filepath: str) -> int | None:
        try:
            row = self._db.conn.execute(
                "SELECT id FROM media_items WHERE filepath=?",
                (filepath,)).fetchone()
            return int(row[0]) if row else None
        except Exception:
            return None

    def _raw_membership(self, pid: int) -> tuple[set[int], set[str]]:
        """Existing track_ids and filepaths of a playlist (empty on error)."""
        tids: set[int] = set()
        fps: set[str] = set()
        try:
            rows = self._db.conn.execute(
                "SELECT track_id, filepath FROM playlist_items "
                "WHERE playlist_id=?", (pid,)).fetchall()
            for tid, fp in rows:
                if tid is not None:
                    tids.add(int(tid))
                if fp:
                    fps.add(str(fp))
        except Exception:
            logger.debug("playlist membership query failed", exc_info=True)
        return tids, fps

    def _insert_membership_raw(self, pid: int, track_id: int,
                               filepath: str) -> None:
        """INSERT membership without committing (used inside transactions)."""
        pos = self._db.conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM playlist_items "
            "WHERE playlist_id=?", (pid,)).fetchone()[0]
        self._db.conn.execute(
            "INSERT INTO playlist_items (playlist_id, filepath, track_id, "
            "position) VALUES (?,?,?,?)",
            (pid, filepath or "", track_id or None, int(pos or 0)))

    def batch_remove(self, pid: int, track_ids: list[int]) -> dict:
        if not track_ids:
            return {"ok": False, "error_code": "EMPTY", "message": "No tracks to remove"}
        removed = 0
        for tid in track_ids:
            result = self.remove_track(pid, tid)
            if result.get("ok"):
                removed += 1
        return {"ok": True, "count": removed, "removed": removed}

    def detect_missing_tracks(self, pid: int) -> dict:
        return self.detect_missing(pid)

    def clear_playlist(self, pid: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            if hasattr(self._db, 'clear_playlist'):
                self._db.clear_playlist(pid)
                return self._ok()
            return self._error("UNSUPPORTED")
        except Exception as e:
            return self._error("CLEAR_FAILED", str(e))

    def cancel_import(self, import_id: str = "") -> dict:
        """Real import cancellation (debt D1 — was a nominal stub).

        Routes to ``job_service.cancel_job`` when *import_id* is an active
        playlist_import job; returns an honest NO_ACTIVE_IMPORT otherwise.
        Never reports cancelled=True without an actual job cancellation.
        """
        if not import_id:
            return self._error("NO_ACTIVE_IMPORT", "No import ID provided")
        if self._job_service is None:
            return self._error("NO_ACTIVE_IMPORT", "No job service wired")
        job = self._job_service.get_job(import_id)
        if job is None:
            return self._error("NO_ACTIVE_IMPORT",
                               f"No active import for {import_id!r}")
        if getattr(job, "type", "") != "playlist_import":
            return self._error("NO_ACTIVE_IMPORT",
                               f"{import_id!r} is not a playlist import job")
        state = getattr(getattr(job, "state", None), "value",
                        getattr(job, "state", ""))
        if state in _TERMINAL_JOB_STATES:
            return self._error("NO_ACTIVE_IMPORT",
                               f"Import {import_id!r} already finished")
        cancelled = self._job_service.cancel_job(import_id)
        if not cancelled:
            return self._error("CANCEL_FAILED",
                               f"Could not cancel import {import_id!r}")
        return self._ok(cancelled=True, import_id=import_id)

    def detect_missing(self, pid: int) -> dict:
        items = self._get_items_internal(pid)
        missing = []
        for item in items:
            fp = item.get("filepath") if isinstance(item, dict) else getattr(item, 'filepath', '')
            if fp and not Path(fp).exists():
                missing.append({"track_id": item.get("id") if isinstance(item, dict) else getattr(item, 'id', ''), "filepath": fp})
        return {"ok": True, "count": len(missing), "missing_count": len(missing), "missing": missing}

    def play_from_index(self, pid: int, index: int,
                        player_service: Any | None = None) -> dict:
        items = self._get_items_internal(pid)
        if index < 0 or index >= len(items):
            return {"ok": False, "error_code": "INVALID_INDEX", "message": "Índice fuera de rango"}
        item = items[index]
        fp = item.get("filepath") if isinstance(item, dict) else getattr(item, 'filepath', '')
        if not fp:
            return {"ok": False, "error_code": "NO_FILEPATH", "message": "Pista sin archivo"}
        if player_service and hasattr(player_service, 'play'):
            try:
                player_service.play(fp)
                return {"ok": True, "index": index, "filepath": fp}
            except Exception as e:
                return {"ok": False, "error_code": "PLAY_FAILED", "message": str(e)}
        return {"ok": True, "index": index, "filepath": fp}

    def save_queue(self, items: list[dict[str, Any]], name: str) -> dict:
        if not name or not name.strip():
            return self._error("EMPTY_NAME")
        if not self._can():
            return self._error("NO_DB")
        try:
            fps = []
            for item in (items or []):
                fp = (getattr(item, "filepath", None)
                      if not isinstance(item, dict) else item.get("filepath", ""))
                if fp:
                    fps.append(fp)
            if not fps:
                return self._error("NO_TRACKS")
            pid = self._db.create_playlist(name.strip())
            for fp in fps:
                self._db.add_track_to_playlist(pid, filepath=fp)
            return self._ok(id=pid, count=len(fps))
        except Exception as e:
            return self._error("SAVE_QUEUE_FAILED", str(e))
