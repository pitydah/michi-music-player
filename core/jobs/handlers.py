"""Production job handler factories for the DurableJobService.

Every factory closes over the port instance passed from composition
(see ``core/composition/jobs.py`` for the composition-side assembly).
Handlers NEVER resolve services: no ``ServiceClass(...)``, no
``container.get(...)``, no fallback instantiation — the port IS the
dependency (ADR-004, Fase Jobs).

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
    "mix_generate": "Generando mix",
}


def make_library_scan_handler(port) -> callable:
    """Close over a LibraryScanPort; scan the folder from the job payload."""

    def handler(job, ctx):
        folder = (job.payload or {}).get("folder_path", "")
        ctx.report_progress(0.05, "Iniciando escaneo")
        ctx.token.raise_if_cancelled()
        result = port.scan(ctx, folder)
        if result.get("error_code") == "CANCELLED":
            ctx.token.raise_if_cancelled()
        if result.get("error_code"):
            raise RuntimeError(result["error_code"])
        if result.get("errors", 0) > 0:
            result["partial"] = True
        ctx.report_progress(1.0, "Escaneo finalizado")
        return result

    return handler


def make_library_scan_all_handler(port) -> callable:
    """Close over a LibraryScanPort; scan every enabled source sequentially."""

    def handler(job, ctx):
        sources = [s for s in port.list_sources()
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
            result = port.scan(ctx, source["path"])
            for key in combined:
                if key != "sources" and key in result:
                    combined[key] += result[key] or 0
        ctx.report_progress(1.0, "Escaneo completo")
        if combined.get("errors", 0) > 0:
            combined["partial"] = True
        return combined

    return handler


def make_metadata_scan_handler(port) -> callable:
    """Close over a MetadataBatchPort; detect tracks with missing metadata."""

    def handler(job, ctx):
        ctx.report_progress(0.1, "Analizando metadatos")
        ctx.token.raise_if_cancelled()
        result = port.scan_missing(ctx)
        ctx.token.raise_if_cancelled()
        if result.get("error"):
            raise RuntimeError(result["error"])
        ctx.report_progress(1.0, "Análisis finalizado")
        return result

    return handler


def make_doctor_scan_handler(port) -> callable:
    """Close over a DoctorRepairPort; run a library health scan."""

    def handler(job, ctx):
        if port is None:
            raise RuntimeError("LibraryDoctorService unavailable")
        ctx.report_progress(0.1, "Revisando biblioteca")
        ctx.token.raise_if_cancelled()
        result = port.scan(ctx)
        ctx.token.raise_if_cancelled()
        if result.get("code") == "CANCELLED":
            ctx.token.raise_if_cancelled()
        if not result.get("ok"):
            raise RuntimeError(result.get("message", "SCAN_FAILED"))
        ctx.report_progress(1.0, "Revisión finalizada")
        return result

    return handler


def make_doctor_repair_handler(port) -> callable:
    """Close over a DoctorRepairPort; repair the issue from the job payload."""

    def handler(job, ctx):
        if port is None:
            raise RuntimeError("LibraryDoctorService unavailable")
        payload = job.payload or {}
        issue = payload.get("issue") or {}
        ctx.report_progress(0.1, "Reparando")
        ctx.token.raise_if_cancelled()
        result = port.repair(
            issue,
            confirmation_token=str(payload.get("confirmation_token", "") or ""),
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


def make_metadata_batch_handler(port) -> callable:
    """Close over a MetadataBatchPort; apply a batch metadata edit.

    The job payload carries the proposal_id and the approved ConfirmationToken
    issued by the bridge flow (proposal → confirm → approve). A job without a
    token is rejected with TOKEN_REQUIRED — self-declared confirmation is
    never accepted.
    """

    def handler(job, ctx):
        payload = job.payload or {}
        proposal_id = str(payload.get("proposal_id", "") or "")
        confirmation_token = str(payload.get("confirmation_token", "") or "")
        if not proposal_id or not confirmation_token:
            raise RuntimeError(
                "TOKEN_REQUIRED: batch edit requires an approved "
                "confirmation token")
        result = port.apply_batch(
            [{"proposal_id": proposal_id,
              "confirmation_token": confirmation_token}],
            ctx=ctx,
        )
        if result.get("status") == "CANCELLED":
            ctx.token.raise_if_cancelled()
        result["ok"] = result.get("ok", False)
        result["total"] = len(payload.get("filepaths") or [])
        if result.get("status") == "PARTIAL_SUCCESS":
            result["partial"] = True
        if result.get("status") == "FAILED":
            raise RuntimeError(result.get("error") or "BATCH_FAILED")
        return result

    return handler


def make_history_export_handler(port) -> callable:
    """Close over a HistoryExportPort; export history to the job payload path."""

    def handler(job, ctx):
        if port is None:
            raise RuntimeError("HistoryExportService unavailable")
        payload = job.payload or {}
        filepath = payload.get("filepath", "")
        fmt = payload.get("fmt", "json")
        filters = payload.get("filters") or {}
        ctx.report_progress(0.1, "Leyendo historial")
        ctx.token.raise_if_cancelled()
        result = port.export_history(filepath, fmt, filters=filters, ctx=ctx)
        ctx.token.raise_if_cancelled()
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "Export failed"))
        ctx.report_progress(1.0, "Exportación finalizada")
        return result

    return handler


def make_mix_generate_handler(port) -> callable:
    """Close over a MixGenerationPort; generate the mix from the job payload.

    The job payload carries {strategy, seed, limit}; the canonical
    MixService outcome ({ok, status, tracks, ...}) becomes the job result
    verbatim — including honest ok=False outcomes (NO_MATCHES,
    EMPTY_LIBRARY, ...) that are NOT failures of the job itself.  Only a
    raised exception fails the job; cancellation is cooperative through ctx.
    """

    def handler(job, ctx):
        if port is None:
            raise RuntimeError("MixService unavailable")
        payload = job.payload or {}
        strategy = str(payload.get("strategy", "") or "daily")
        seed = payload.get("seed") or {}
        try:
            limit = int(payload.get("limit") or 30)
        except (TypeError, ValueError):
            limit = 30
        ctx.report_progress(0.1, "Generando mix")
        ctx.token.raise_if_cancelled()
        result = port.generate(strategy, seed, limit, ctx)
        ctx.token.raise_if_cancelled()
        ctx.report_progress(1.0, "Mix generado")
        return result

    return handler
