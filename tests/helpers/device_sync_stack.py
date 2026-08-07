"""Shared test helper — build a fully injected DeviceSyncService stack.

Fase Sync contract: the facade NEVER constructs its own pipeline pieces;
tests (and composition) inject every dependency. This helper mirrors
``core/composition/ecosystem.py`` with temp files, so tests exercise the
same wiring as production.
"""
from __future__ import annotations


def make_device_sync_stack(
    tmp_path,
    *,
    with_jobs: bool = True,
    process_controller=None,
    event_bus=None,
    adapters=None,
    worker_manager=None,
    jobs_db: str = "",
    transfer_adapter=None,
):
    """Return a real facade with real (temp) registry, planners, jobs, history.

    Args:
        tmp_path: pytest tmp_path for registry + jobs db.
        with_jobs: when False, job_service stays None (facade methods that
            need it return honest UNAVAILABLE outcomes).
        process_controller: injected into the TransferAdapter (transcode
            path). Tests simulating external tools pass a fake here.
        event_bus: injected EventBus (the test keeps its own reference).
        adapters: optional DiscoveryComposite override (fake adapters).
        worker_manager: optional real WorkerManager for async job runs.
        jobs_db: optional durable jobs db path (shared across restarts).
        transfer_adapter: optional TransferAdapter override.
    """
    from core.device_sync.discovery import (
        DiscoveryComposite,
        MscDiscoveryAdapter,
        MtpDiscoveryAdapter,
        NetworkDiscoveryAdapter,
    )
    from core.device_sync.history import SyncHistoryRepository
    from core.device_sync.planning import DeviceSyncPlanner
    from core.device_sync.profile_resolver import DeviceProfileResolver
    from core.device_sync.transcode_planning import TranscodePlanner
    from core.device_sync.transfer import TransferAdapter
    from core.device_sync.verification import VerificationService
    from core.device_sync_service import DeviceSyncService
    from core.event_bus import EventBus
    from core.job_service import JobService
    from core.sync.device_registry import DeviceRegistry
    from library.library_db import LibraryDB

    registry = DeviceRegistry(path=str(tmp_path / "paired_devices.json"))
    if adapters is None:
        adapters = DiscoveryComposite([
            MscDiscoveryAdapter(),
            MtpDiscoveryAdapter(),
            NetworkDiscoveryAdapter(),
        ])
    resolver = DeviceProfileResolver()
    transcode_planner = TranscodePlanner()
    planner = DeviceSyncPlanner(transcode_planner=transcode_planner)
    if transfer_adapter is None:
        transfer_adapter = TransferAdapter(process_controller=process_controller)
    verification = VerificationService()
    db = LibraryDB(":memory:")
    history = SyncHistoryRepository(db)
    history.initialize()

    job_service = None
    if with_jobs:
        job_service = JobService(
            db_path=jobs_db or str(tmp_path / "jobs.db"),
            worker_manager=worker_manager,
        )

    svc = DeviceSyncService(
        device_registry=registry,
        discovery_adapters=adapters,
        profile_resolver=resolver,
        sync_planner=planner,
        transcode_planner=transcode_planner,
        job_service=job_service,
        transfer_adapter=transfer_adapter,
        verification_service=verification,
        history_repository=history,
        event_bus=event_bus if event_bus is not None else EventBus(),
        process_controller=process_controller,
    )
    if job_service is not None:
        # Mirrors core.composition.jobs: handlers are registered on the
        # composed job service right after the facade exists.
        register_handlers_for(svc, job_service)
    return svc


def register_handlers_for(svc, job_service):
    """Register production device job handlers closing over the facade."""
    from core.jobs.handlers import (
        make_device_sync_handler,
        make_device_transfer_handler,
    )

    class _Port:
        def __init__(self, target):
            self._target = target

        def sync_device(self, device_id, track_ids, playlist_name="", ctx=None):
            return self._target.run_device_sync(device_id, list(track_ids),
                                                playlist_name, ctx)

        def transfer_file(self, source_path, dest_path, ctx=None):
            return self._target.run_transfer_file(source_path, dest_path, ctx)

    port = _Port(svc)
    job_service.register_handler("device_sync",
                                 make_device_sync_handler(port))
    job_service.register_handler("device_transfer",
                                 make_device_transfer_handler(port))
