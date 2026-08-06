"""Production job handlers registered on the DurableJobService.

Every job kind the UI can submit through JobBridge has an explicit handler
here: library_scan, library_scan_all, metadata_scan, doctor_scan,
metadata_batch and history_export. Audio Lab operations are migrated in a
later slice; the registry mechanism already supports them.

Handler contract (DurableJobService): ``handler(job, ctx)`` where ``ctx``
exposes ``raise_if_cancelled()`` and ``report_progress(percent, message)``.
Handlers run on a WorkerManager thread when the service has one injected;
they must never touch the UI layer directly.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.jobs.handlers")

JOB_TITLES = {
    "library_scan": "Escaneando biblioteca",
    "library_scan_all": "Escaneando todas las fuentes",
    "metadata_scan": "Analizando metadatos",
    "doctor_scan": "Revisando biblioteca",
    "metadata_batch": "Edición de metadatos en lote",
    "history_export": "Exportando historial",
}


def register_production_job_handlers(job_service, container) -> None:
    """Register every production job handler on *job_service*.

    Services are resolved lazily from *container* at execution time, so this
    may be called from the infrastructure builder before other composition
    modules run.
    """
    job_service.register_handler("library_scan", _make_library_scan_handler(container))
    job_service.register_handler("library_scan_all", _make_library_scan_all_handler(container))
    job_service.register_handler("metadata_scan", _make_metadata_scan_handler(container))
    job_service.register_handler("doctor_scan", _make_doctor_scan_handler(container))
    job_service.register_handler("metadata_batch", _make_metadata_batch_handler(container))
    job_service.register_handler("doctor_repair", _make_doctor_repair_handler(container))
    job_service.register_handler("history_export", _make_history_export_handler(container))


def _run_library_scan(ctx, container, folder_path: str) -> dict:
    from core.scanner_job_adapter import ScannerJobAdapter

    db = container.get("database")
    adapter = ScannerJobAdapter(db, library_bridge=None)
    result = adapter.scan(ctx, folder_path)
    if result.get("error_code") == "CANCELLED":
        ctx.token.raise_if_cancelled()
    if result.get("error_code"):
        raise RuntimeError(result["error_code"])
    if result.get("errors", 0) > 0:
        result["partial"] = True
    return result


def _make_library_scan_handler(container):
    def handler(job, ctx):
        folder = (job.payload or {}).get("folder_path", "")
        ctx.report_progress(0.05, "Iniciando escaneo")
        ctx.token.raise_if_cancelled()
        result = _run_library_scan(ctx, container, folder)
        ctx.report_progress(1.0, "Escaneo finalizado")
        return result

    return handler


def _make_library_scan_all_handler(container):
    def handler(job, ctx):
        from core.library_sources_service import LibrarySourcesService

        db = container.get("database")
        src_svc = container.get("library_sources_service")
        if src_svc is None:
            src_svc = LibrarySourcesService(db=db)
        sources = [s for s in src_svc.list()
                   if s.get("enabled") and s.get("available")]
        total = max(len(sources), 1)
        combined: dict = {
            "sources": len(sources), "files_seen": 0, "added": 0,
            "updated": 0, "unchanged": 0, "skipped": 0, "errors": 0,
            "missing": 0, "elapsed": 0,
        }
        for idx, source in enumerate(sources):
            ctx.token.raise_if_cancelled()
            ctx.report_progress(idx / total, f"Escaneando {source['path']}")
            result = _run_library_scan(ctx, container, source["path"])
            for key in combined:
                if key != "sources" and key in result:
                    combined[key] += result[key] or 0
        ctx.report_progress(1.0, "Escaneo completo")
        if combined.get("errors", 0) > 0:
            combined["partial"] = True
        return combined

    return handler


def _make_metadata_scan_handler(container):
    def handler(job, ctx):
        from core.metadata_batch_adapter import MetadataBatchAdapter

        db = container.get("database")
        ctx.report_progress(0.1, "Analizando metadatos")
        ctx.token.raise_if_cancelled()
        adapter = MetadataBatchAdapter(db=db)
        result = adapter.scan_missing(ctx)
        ctx.token.raise_if_cancelled()
        if result.get("error"):
            raise RuntimeError(result["error"])
        ctx.report_progress(1.0, "Análisis finalizado")
        return result

    return handler


def _make_doctor_scan_handler(container):
    def handler(job, ctx):
        doctor = container.get("library_doctor_service")
        if doctor is None:
            raise RuntimeError("LibraryDoctorService unavailable")
        ctx.report_progress(0.1, "Revisando biblioteca")
        ctx.token.raise_if_cancelled()
        result = doctor.scan(ctx)
        ctx.token.raise_if_cancelled()
        if result.get("code") == "CANCELLED":
            ctx.token.raise_if_cancelled()
        if not result.get("ok"):
            raise RuntimeError(result.get("message", "SCAN_FAILED"))
        ctx.report_progress(1.0, "Revisión finalizada")
        return result

    return handler


def _make_doctor_repair_handler(container):
    def handler(job, ctx):
        doctor = container.get("library_doctor_service")
        if doctor is None:
            raise RuntimeError("LibraryDoctorService unavailable")
        payload = job.payload or {}
        issue = payload.get("issue") or {}
        ctx.report_progress(0.1, "Reparando")
        ctx.token.raise_if_cancelled()
        result = doctor.repair(
            issue,
            confirmation_token=str(payload.get("confirmation_token", "") or ""),
            confirmed_source=str(payload.get("confirmed_source", "") or ""),
            ctx=ctx,
        )
        if result.get("code") == "CANCELLED":
            ctx.token.raise_if_cancelled()
        ctx.report_progress(1.0, "Reparación finalizada")
        if not result.get("ok"):
            if result.get("status") == "JOB_STARTED":
                return {"partial": True, **result}
            raise RuntimeError(result.get("code", "REPAIR_FAILED"))
        return result

    return handler


def _make_metadata_batch_handler(container):
    def handler(job, ctx):
        editor = container.get("metadata_editor_service")
        if editor is None:
            raise RuntimeError("MetadataEditorService unavailable")
        payload = job.payload or {}
        filepaths = list(payload.get("filepaths") or [])
        key = payload.get("field", "")
        value = str(payload.get("value", ""))
        proposal = editor.build_proposal(
            [{"filepath": fp} for fp in filepaths],
            {key: value},
        )
        if not proposal.get("ok"):
            raise RuntimeError(proposal.get("code", "PROPOSAL_FAILED"))
        result = editor.apply_batch(
            [{"proposal_id": proposal["proposal_id"],
              "confirmed": True, "source": "ui"}],
            ctx=ctx,
        )
        if result.get("status") == "CANCELLED":
            ctx.token.raise_if_cancelled()
        result["ok"] = result.get("ok", False)
        result["total"] = len(filepaths)
        if result.get("status") == "PARTIAL_SUCCESS":
            result["partial"] = True
        if result.get("status") == "FAILED":
            raise RuntimeError(result.get("error") or "BATCH_FAILED")
        return result

    return handler


def _make_history_export_handler(container):
    def handler(job, ctx):
        from core.history_export_service import HistoryExportService

        db = container.get("database")
        payload = job.payload or {}
        filepath = payload.get("filepath", "")
        fmt = payload.get("fmt", "json")
        filters = payload.get("filters") or {}
        ctx.report_progress(0.1, "Leyendo historial")
        ctx.token.raise_if_cancelled()
        svc = HistoryExportService(db=db)
        result = svc.export_history(filepath, fmt, filters=filters, ctx=ctx)
        ctx.token.raise_if_cancelled()
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Export failed"))
        ctx.report_progress(1.0, "Exportación finalizada")
        return result

    return handler
