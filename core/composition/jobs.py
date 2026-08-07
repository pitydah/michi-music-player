"""Jobs composition — handler registration over composed services (ADR-004).

Registers every production job handler on the container's DurableJobService
using the PURE factories from ``core/jobs/handlers.py``, closing over port
instances built from the already-composed services. No handler resolves
anything itself: ``container.get`` happens HERE (composition), never inside
``core/jobs/handlers.py``.

Must run AFTER every builder whose services the ports need (library, audio
lab, playback, intelligence). ``build`` also resumes QUEUED jobs recovered
from the previous process (``DurableJobService.resume_pending_jobs``) so no
restored job is left silently stopped.
"""
from __future__ import annotations

import logging

from core.service_container import ServiceContainer

logger = logging.getLogger("michi.composition.jobs")


class _ScannerPort:
    """LibraryScanPort over ScannerJobAdapter + LibrarySourcesService."""

    def __init__(self, scanner, sources_service):
        self._scanner = scanner
        self._sources = sources_service

    def scan(self, ctx, folder_path: str) -> dict:
        if self._scanner is None:
            raise RuntimeError("ScannerJobAdapter unavailable")
        return self._scanner.scan(ctx, folder_path)

    def list_sources(self) -> list[dict]:
        if self._sources is None:
            return []
        return [s for s in self._sources.list()
                if s.get("enabled") and s.get("available")]


class _MetadataPort:
    """MetadataBatchPort over MetadataBatchAdapter + MetadataEditorService."""

    def __init__(self, batch_adapter, editor):
        self._adapter = batch_adapter
        self._editor = editor

    def scan_missing(self, ctx=None) -> dict:
        if self._adapter is None:
            raise RuntimeError("MetadataBatchAdapter unavailable")
        return self._adapter.scan_missing(ctx)

    def build_proposal(self, track_refs: list, fields: dict | None = None) -> dict:
        if self._editor is None:
            raise RuntimeError("MetadataEditorService unavailable")
        return self._editor.build_proposal(track_refs, fields)

    def apply_batch(self, requests: list, ctx=None) -> dict:
        if self._editor is None:
            raise RuntimeError("MetadataEditorService unavailable")
        return self._editor.apply_batch(requests, ctx=ctx)


class _MixPort:
    """MixGenerationPort over the composed MixService (single facade).

    The MixService owns every strategy (smart, recent and query-backed
    categories); the port adds no business logic, only the ctx-shaped call.
    """

    def __init__(self, mix_service):
        self._mix = mix_service

    def generate(self, strategy: str, seed: dict | None = None,
                 limit: int = 30, ctx=None) -> dict:
        if self._mix is None:
            raise RuntimeError("MixService unavailable")
        return self._mix.generate(strategy=strategy, seed=seed, limit=limit)


class _DeviceSyncPort:
    """DeviceSyncPort over the composed DeviceSyncService facade.

    The facade owns the pipeline (plan → transfer → verify → playlist →
    history → event); the port adds no business logic, only the ctx-shaped
    call used by the durable job handlers.
    """

    def __init__(self, device_sync):
        self._svc = device_sync

    def sync_device(self, device_id: str, track_ids: list,
                    playlist_name: str = "", ctx=None) -> dict:
        if self._svc is None:
            raise RuntimeError("DeviceSyncService unavailable")
        return self._svc.run_device_sync(device_id, list(track_ids),
                                         playlist_name, ctx)

    def transfer_file(self, source_path: str, dest_path: str,
                      ctx=None) -> dict:
        if self._svc is None:
            raise RuntimeError("DeviceSyncService unavailable")
        return self._svc.run_transfer_file(source_path, dest_path, ctx)


class _PlaylistImportPort:
    """PlaylistImportPort over the composed PlaylistService (debt D1).

    The service owns every policy (ATOMIC_ROLLBACK / PARTIAL_COMMIT /
    SKIP_INVALID); the port adds no business logic, only the ctx-shaped
    call used by the durable job handler.
    """

    def __init__(self, playlist_service):
        self._svc = playlist_service

    def import_playlist(self, path: str, name: str = "",
                        policy: str = "SKIP_INVALID", ctx=None) -> dict:
        if self._svc is None:
            raise RuntimeError("PlaylistService unavailable")
        return self._svc.import_playlist_file(
            path, target_name=name or None, policy=policy, ctx=ctx)


def _build_ports(container: ServiceContainer) -> dict[str, object]:
    """Assemble the port implementations from composed services."""
    from core.scanner_job_adapter import ScannerJobAdapter
    from core.metadata_batch_adapter import MetadataBatchAdapter
    from core.history_export_service import HistoryExportService

    db = container.get("database")

    scanner = ScannerJobAdapter(db, library_bridge=None) if db is not None else None
    batch_adapter = MetadataBatchAdapter(db=db) if db is not None else None

    scan_port = _ScannerPort(
        scanner,
        container.get("library_sources_service"),
    )
    metadata_port = _MetadataPort(
        batch_adapter,
        container.get("metadata_editor_service"),
    )
    history_port = HistoryExportService(db=db) if db is not None else None
    doctor_port = container.get("library_doctor_service")
    mix_port = _MixPort(container.get("mix_service"))
    device_port = _DeviceSyncPort(container.get("device_sync_service"))
    playlist_port = _PlaylistImportPort(container.get("playlist_service"))

    return {
        "scan": scan_port,
        "metadata": metadata_port,
        "history": history_port,
        "doctor": doctor_port,
        "mix": mix_port,
        "device_sync": device_port,
        "playlist_import": playlist_port,
    }


def register_production_job_handlers(job_service, container: ServiceContainer) -> None:
    """Register every production job handler with its composed port.

    Called by the jobs composition builder; kept as a named function so
    architecture audits can verify registration happens in composition.
    """
    from core.jobs.handlers import (
        make_device_sync_handler,
        make_device_transfer_handler,
        make_doctor_repair_handler,
        make_doctor_scan_handler,
        make_history_export_handler,
        make_library_scan_all_handler,
        make_library_scan_handler,
        make_metadata_batch_handler,
        make_metadata_scan_handler,
        make_mix_generate_handler,
        make_playlist_import_handler,
    )

    ports = _build_ports(container)
    job_service.register_handler("library_scan",
                                 make_library_scan_handler(ports["scan"]))
    job_service.register_handler("library_scan_all",
                                 make_library_scan_all_handler(ports["scan"]))
    job_service.register_handler("metadata_scan",
                                 make_metadata_scan_handler(ports["metadata"]))
    job_service.register_handler("metadata_batch",
                                 make_metadata_batch_handler(ports["metadata"]))
    job_service.register_handler("doctor_scan",
                                 make_doctor_scan_handler(ports["doctor"]))
    job_service.register_handler("doctor_repair",
                                 make_doctor_repair_handler(ports["doctor"]))
    job_service.register_handler("history_export",
                                 make_history_export_handler(ports["history"]))
    job_service.register_handler("mix_generate",
                                 make_mix_generate_handler(ports["mix"]))
    job_service.register_handler("device_sync",
                                 make_device_sync_handler(ports["device_sync"]))
    job_service.register_handler("device_transfer",
                                 make_device_transfer_handler(ports["device_sync"]))
    job_service.register_handler("playlist_import",
                                 make_playlist_import_handler(ports["playlist_import"]))


def build(container: ServiceContainer) -> None:
    """Compose job handlers and resume jobs recovered from the last process."""
    job_service = container.get("job_service")
    if job_service is None:
        logger.warning("Jobs composition: job_service unavailable — skipping")
        return
    register_production_job_handlers(job_service, container)
    try:
        stats = job_service.resume_pending_jobs()
        if any(stats.values()):
            logger.info("Jobs composition: resumed pending jobs %s", stats)
    except Exception:  # noqa: BLE001
        logger.exception("Jobs composition: resume_pending_jobs failed")
