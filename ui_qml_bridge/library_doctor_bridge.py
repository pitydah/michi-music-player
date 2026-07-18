from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.library_doctor.repositories.scan_repository import LibraryDoctorScanRepository

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
        assert db is not None, "LibraryDoctorBridge: db is REQUIRED"
        assert worker_manager is not None, "LibraryDoctorBridge: worker_manager is REQUIRED"
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
        repo = LibraryDoctorScanRepository(self._db)
        issues: list[dict] = []
        total = 0
        conn = getattr(self._db, 'conn', None) if self._db else None
        if conn is None:
            return {"issues": [], "total_checked": 0}

        try:
            if ctx:
                ctx.token.raise_if_cancelled()

            rows = repo.fetch_all_tracks()
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

            for op in repo.find_orphan_playlist_items():
                issues.append({
                    "id": len(issues), "type": "orphan_playlist_item",
                    "filepath": op[1] or "", "detail": f"Item huérfano en playlist {op[2]}",
                    "track_id": op[0],
                })

            if ctx:
                ctx.token.raise_if_cancelled()

            for oh in repo.find_orphan_history():
                issues.append({
                    "id": len(issues), "type": "orphan_history",
                    "filepath": oh[1] or "", "detail": "Entrada huérfana en historial",
                    "track_id": oh[0],
                })

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
        return {"ok": True, "count": len(self._selected_ids)}

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
        repo = LibraryDoctorScanRepository(self._db)
        conn = getattr(self._db, 'conn', None) if self._db else None
        if conn is None:
            return {"ok": False}

        try:
            repo.begin()

            for idx, issue in enumerate(selected):
                if ctx:
                    ctx.token.raise_if_cancelled()
                    ctx.report_progress((idx + 1) / len(selected), f"{idx+1}/{len(selected)}")

                itype = issue.get("type", "")
                track_id = issue.get("track_id")
                filepath = issue.get("filepath", "")

                if itype == "missing_metadata" and track_id:
                    base = Path(filepath).stem if filepath else ""
                    repo.update_title(track_id, base)

                elif itype == "orphan_playlist_item" and track_id:
                    repo.delete_playlist_item(track_id)

                elif itype == "orphan_history" and track_id:
                    repo.delete_history(track_id)

                elif itype == "duplicate_path" and track_id:
                    repo.mark_deleted(track_id)

                elif itype == "duplicate_uid" and track_id:
                    repo.update_uid(track_id, filepath)

            repo.commit()
            return {"ok": True}
        except Exception:
            repo.rollback()
            logger.exception("Library doctor repair failed")
            return {"ok": False}

    @Slot(str, result=str)
    def fileName(self, path: str) -> str:
        if not path:
            return ""
        return Path(path).name

    @Slot(result=dict)
    def cancelScan(self):
        if self._wm:
            self._wm.cancel_task("library_doctor_scan")
            self._wm.cancel_task("library_doctor_repair")
        self._status = "idle"
        self.dataChanged.emit()
        return {"ok": True, "cancelled": True}

    @Slot(str, str, result=dict)
    def exportReport(self, filepath: str, format: str) -> dict:
        if not self._issues:
            return {"ok": False, "error": "NO_DATA", "message": "No hay datos de escaneo para exportar"}

        path = Path(filepath)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if format == "json":
                import json
                data = {
                    "total_checked": self._total_checked,
                    "issue_count": self._issue_count,
                    "issues": self._issues,
                }
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            elif format == "csv":
                import csv
                with path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["id", "type", "filepath", "detail", "track_id"])
                    writer.writeheader()
                    for iss in self._issues:
                        writer.writerow({
                            "id": iss.get("id"),
                            "type": iss.get("type", ""),
                            "filepath": iss.get("filepath", ""),
                            "detail": iss.get("detail", ""),
                            "track_id": iss.get("track_id", ""),
                        })
            else:
                return {"ok": False, "error": "INVALID_FORMAT", "message": f"Formato no soportado: {format}"}
            return {"ok": True, "path": str(path)}
        except Exception as e:
            logger.exception("Failed to export report")
            return {"ok": False, "error": "EXPORT_FAILED", "message": str(e)}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
