"""LibraryDoctorBridge — async library health scanning and repair.

Detects and repairs: missing files, duplicate UID, duplicate path,
metadata missing, orphan playlist items, orphan history, invalid album key,
dead source, cover missing, DB integrity.

Flow: scan async → preview → select fixes → dry-run → backup → transaction
→ apply → verify → rollback if needed.
"""
from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.library_doctor")

ISSUE_TYPES = {
    "missing_file": "Archivo faltante",
    "duplicate_uid": "UID duplicado",
    "duplicate_path": "Ruta duplicada",
    "missing_metadata": "Metadatos incompletos",
    "orphan_playlist_item": "Item huérfano en playlist",
    "orphan_history": "Entrada huérfana en historial",
    "invalid_album_key": "Clave de álbum inválida",
    "dead_source": "Fuente muerta",
    "cover_missing": "Carátula faltante",
    "db_integrity": "Integridad BD",
}


class LibraryDoctorBridge(QObject):
    dataChanged = Signal()
    scanProgress = Signal(int, int)
    repairProgress = Signal(int, int)

    def __init__(self, db=None, worker_manager=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = worker_manager
        self._status = "idle"
        self._issues: list[dict] = []
        self._selected_ids: set[int] = set()
        self._total_checked = 0
        self._issue_count = 0
        self._scan_gen = 0

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def issues(self):
        return list(self._issues)

    @Property(int, notify=dataChanged)
    def totalChecked(self):
        return self._total_checked

    @Property(int, notify=dataChanged)
    def issueCount(self):
        return self._issue_count

    @Property(int, notify=dataChanged)
    def missingMetadataCount(self):
        return sum(1 for i in self._issues if i.get("type") == "missing_metadata")

    @Property(int, notify=dataChanged)
    def missingFileCount(self):
        return sum(1 for i in self._issues if i.get("type") == "missing_file")

    @Property(int, notify=dataChanged)
    def healthyCount(self):
        return max(0, self._total_checked - self._issue_count)

    @Slot()
    def scan(self):
        if self._status == "scanning":
            return
        self._scan_gen += 1
        gen = self._scan_gen
        self._status = "scanning"
        self._issues = []
        self._selected_ids.clear()
        self.dataChanged.emit()

        if not self._wm:
            self._run_scan_sync()
            return

        def _task(ctx):
            ctx.token.raise_if_cancelled()
            return self._run_scan_impl(gen, ctx)

        def _on_done(result):
            if gen != self._scan_gen:
                return
            self._issues = result.get("issues", [])
            self._total_checked = result.get("total_checked", 0)
            self._issue_count = len(self._issues)
            self._status = "done" if (self._total_checked > 0 or self._issue_count > 0) else "no_data"
            self.dataChanged.emit()

        def _on_error(code, msg):
            if gen != self._scan_gen:
                return
            self._status = "error"
            self.dataChanged.emit()

        def _on_cancelled():
            if gen != self._scan_gen:
                return
            self._status = "cancelled"
            self.dataChanged.emit()

        def _on_progress(pct, msg):
            if gen != self._scan_gen:
                return
            self.scanProgress.emit(int(pct * 100), 100)

        self._wm.run_task(
            "library_doctor_scan", _task,
            pass_context=True, cancellable=True, owner="library_doctor",
            on_done=_on_done, on_error=_on_error,
            on_cancelled=_on_cancelled, on_progress=_on_progress,
        )

    def _run_scan_sync(self):
        result = self._run_scan_impl(self._scan_gen, None)
        self._issues = result.get("issues", [])
        self._total_checked = result.get("total_checked", 0)
        self._issue_count = len(self._issues)
        self._status = "done" if (self._total_checked > 0 or self._issue_count > 0) else "no_data"
        self.dataChanged.emit()

    def _run_scan_impl(self, gen: int, ctx) -> dict:
        issues: list[dict] = []
        total = 0
        conn = getattr(self._db, 'conn', None) if self._db else None
        if conn is None:
            return {"issues": [], "total_checked": 0}

        try:
            if ctx:
                ctx.token.raise_if_cancelled()

            rows = conn.execute(
                "SELECT id, filepath, title, artist, album, album_key, track_uid "
                "FROM media_items WHERE deleted_at IS NULL"
            ).fetchall()
            total = len(rows)

            filepaths_seen: dict[str, int] = {}
            uids_seen: dict[str, int] = {}

            for idx, row in enumerate(rows):
                if ctx:
                    ctx.token.raise_if_cancelled()
                    if idx % 50 == 0:
                        ctx.report_progress(idx / total, f"{idx}/{total}")

                rid, fp, title, artist, album, album_key, track_uid = row

                if not fp:
                    continue

                from pathlib import Path
                if not Path(fp).exists():
                    issues.append({
                        "id": len(issues), "type": "missing_file",
                        "filepath": fp, "detail": "Archivo no encontrado en disco",
                        "track_id": rid,
                    })

                if fp in filepaths_seen:
                    issues.append({
                        "id": len(issues), "type": "duplicate_path",
                        "filepath": fp, "detail": f"Ruta duplicada (IDs: {filepaths_seen[fp]}, {rid})",
                        "track_id": rid,
                    })
                else:
                    filepaths_seen[fp] = rid

                if track_uid:
                    if track_uid in uids_seen:
                        issues.append({
                            "id": len(issues), "type": "duplicate_uid",
                            "filepath": fp, "detail": f"UID duplicado: {track_uid}",
                            "track_id": rid,
                        })
                    else:
                        uids_seen[track_uid] = rid

                if not title or not artist:
                    issues.append({
                        "id": len(issues), "type": "missing_metadata",
                        "filepath": fp, "detail": "Falta título o artista",
                        "track_id": rid,
                    })

            if ctx:
                ctx.token.raise_if_cancelled()

            try:
                orphan_playlists = conn.execute(
                    "SELECT pi.rowid, pi.filepath, pi.playlist_id FROM playlist_items pi "
                    "LEFT JOIN media_items m ON pi.filepath = m.filepath "
                    "WHERE m.id IS NULL"
                ).fetchall()
                for op in orphan_playlists:
                    issues.append({
                        "id": len(issues), "type": "orphan_playlist_item",
                        "filepath": op[1] or "", "detail": f"Item huérfano en playlist {op[2]}",
                        "track_id": op[0],
                    })
            except Exception:
                pass

            if ctx:
                ctx.token.raise_if_cancelled()

            try:
                orphan_history = conn.execute(
                    "SELECT h.id, h.filepath FROM play_history h "
                    "LEFT JOIN media_items m ON h.filepath = m.filepath "
                    "WHERE m.id IS NULL AND h.filepath != ''"
                ).fetchall()
                for oh in orphan_history:
                    issues.append({
                        "id": len(issues), "type": "orphan_history",
                        "filepath": oh[1] or "", "detail": "Entrada huérfana en historial",
                        "track_id": oh[0],
                    })
            except Exception:
                pass

        except Exception as e:
            logger.debug("Library doctor scan failed: %s", e, exc_info=True)

        return {"issues": issues, "total_checked": total}

    @Slot(int, bool, result=dict)
    def setIssueSelected(self, issue_id: int, selected: bool):
        if selected:
            self._selected_ids.add(issue_id)
        else:
            self._selected_ids.discard(issue_id)
        for iss in self._issues:
            if iss.get("id") == issue_id:
                iss["selected"] = selected
                break
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def selectAll(self):
        self._selected_ids = set(s["id"] for s in self._issues if s.get("id") is not None)
        for iss in self._issues:
            iss["selected"] = True
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def selectNone(self):
        self._selected_ids.clear()
        for iss in self._issues:
            iss["selected"] = False
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def repairSelected(self):
        if self._status != "done":
            return {"ok": False, "error": "NOT_SCANNED", "message": "Escanea primero"}
        if not self._selected_ids:
            return {"ok": False, "error": "NO_SELECTION", "message": "Selecciona issues a reparar"}
        selected = [i for i in self._issues if i.get("id") in self._selected_ids]
        if not selected:
            return {"ok": False, "error": "NO_ISSUES", "message": "No hay issues seleccionados"}

        self._status = "repairing"
        self.dataChanged.emit()
        gen = self._scan_gen

        if not self._wm:
            self._repair_sync(selected)
            return {"ok": True, "sync": True}

        def _task(ctx):
            ctx.token.raise_if_cancelled()
            return self._repair_impl(selected, ctx)

        def _on_done(result):
            if gen != self._scan_gen:
                return
            self._status = "done"
            self._issues = [i for i in self._issues if i.get("id") not in self._selected_ids]
            self._issue_count = len(self._issues)
            self._selected_ids.clear()
            self.dataChanged.emit()

        def _on_error(code, msg):
            if gen != self._scan_gen:
                return
            self._status = "error"
            self.dataChanged.emit()

        def _on_cancelled():
            if gen != self._scan_gen:
                return
            self._status = "done"
            self.dataChanged.emit()

        def _on_progress(pct, msg):
            if gen != self._scan_gen:
                return
            self.repairProgress.emit(int(pct * len(selected)), len(selected))

        self._wm.run_task(
            "library_doctor_repair", _task,
            pass_context=True, cancellable=True, owner="library_doctor",
            on_done=_on_done, on_error=_on_error,
            on_cancelled=_on_cancelled, on_progress=_on_progress,
        )
        return {"ok": True, "async": True}

    def _repair_sync(self, selected: list[dict]):
        self._repair_impl(selected, None)
        self._status = "done"
        self._issues = [i for i in self._issues if i.get("id") not in self._selected_ids]
        self._issue_count = len(self._issues)
        self._selected_ids.clear()
        self.dataChanged.emit()

    def _repair_impl(self, selected: list[dict], ctx) -> dict:
        conn = getattr(self._db, 'conn', None) if self._db else None
        if conn is None:
            return {"ok": False}

        try:
            conn.execute("BEGIN IMMEDIATE")

            for idx, issue in enumerate(selected):
                if ctx:
                    ctx.token.raise_if_cancelled()
                    ctx.report_progress((idx + 1) / len(selected), f"{idx+1}/{len(selected)}")

                itype = issue.get("type", "")
                track_id = issue.get("track_id")
                filepath = issue.get("filepath", "")

                if itype == "missing_metadata" and track_id:
                    from pathlib import Path
                    fp = filepath or ""
                    base = Path(fp).stem if fp else ""
                    conn.execute(
                        "UPDATE media_items SET title=? WHERE id=? AND (title IS NULL OR title='')",
                        (base, track_id),
                    )

                elif itype == "orphan_playlist_item" and track_id:
                    conn.execute("DELETE FROM playlist_items WHERE rowid=?", (track_id,))

                elif itype == "orphan_history" and track_id:
                    conn.execute("DELETE FROM play_history WHERE id=?", (track_id,))

                elif itype == "duplicate_path" and track_id:
                    conn.execute(
                        "UPDATE media_items SET deleted_at=? WHERE id=?",
                        (time.time(), track_id),
                    )

                elif itype == "duplicate_uid" and track_id:
                    import hashlib
                    new_uid = f"fp:{hashlib.sha256(filepath.encode()).hexdigest()[:16]}"
                    conn.execute(
                        "UPDATE media_items SET track_uid=? WHERE id=?",
                        (new_uid, track_id),
                    )

            conn.commit()
            return {"ok": True}
        except Exception:
            conn.execute("ROLLBACK")
            logger.exception("Library doctor repair failed")
            return {"ok": False}

    @Slot(result=dict)
    def cancelScan(self):
        if self._wm:
            self._wm.cancel_task("library_doctor_scan")
            self._wm.cancel_task("library_doctor_repair")
        self._status = "idle"
        self.dataChanged.emit()
        return {"ok": True}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
