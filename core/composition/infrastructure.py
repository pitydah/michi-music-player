"""Infrastructure services — config, database, workers, persistence."""
from __future__ import annotations

import os

from core.service_container import ServiceContainer


def build(container: ServiceContainer) -> None:
    from core.settings_manager import SETTINGS
    from core.paths import database_path as _dp
    from library.library_db import LibraryDB
    from core.runtime_persistence import RuntimePersistence
    from core.process_controller import ProcessController
    from core.event_bus import EventBus
    from core.worker_manager import WorkerManager
    from core.query_executor import QueryExecutor
    from core.job_service import JobService
    from core.confirmation_service import ConfirmationService
    from core.settings_service import SettingsService
    from core.settings_runtime_coordinator import SettingsRuntimeCoordinator
    from core.settings_migrations import migrate_all

    container.register("settings_manager", SETTINGS)
    container.register("paths", _dp)

    db = LibraryDB(_dp())
    container.register("database", db)
    container.register("connection_factory", db)

    # SQLite concurrency — one writer, N readers (Patch 5). Registered under
    # dedicated keys so existing consumers of ``connection_factory``/``database``
    # (which rely on LibraryDB's ``.conn``/``.db_path``) are unaffected.
    from library.connection_factory import ReadConnectionFactory, WriterCoordinator
    container.register("read_connection_factory", ReadConnectionFactory(_dp()))
    container.register("writer_coordinator", WriterCoordinator(_dp()))

    from core.library.repositories.track_repository import TrackRepository
    from core.library.repositories.album_repository import AlbumRepository
    from core.library.repositories.artist_repository import ArtistRepository
    container.register("track_repository", TrackRepository(db))
    container.register("album_repository", AlbumRepository(db))
    container.register("artist_repository", ArtistRepository(db))

    container.register("runtime_persistence", RuntimePersistence())

    container.register("process_controller", ProcessController())

    eb = EventBus()
    container.register("event_bus", eb)

    wm = WorkerManager()
    qe = QueryExecutor(worker_manager=wm)
    container.register("worker_manager", wm)
    container.register("query_executor", qe)

    job_service = JobService(worker_manager=wm)
    container.register("job_service", job_service)

    from core import paths as core_paths
    confirmation_audit = os.path.join(core_paths.app_data_dir(),
                                      "confirmation_audit.jsonl")
    container.register("confirmation_service",
                       ConfirmationService(audit_path=confirmation_audit))

    from core.undo_service import UndoService
    undo_log = os.path.join(core_paths.app_data_dir(), "undo_log.jsonl")
    container.register("undo_service",
                       UndoService(event_bus=eb, persistence_path=undo_log))

    from core.notification_action_service import NotificationActionService
    container.register(
        "notification_action_service",
        NotificationActionService(
            job_service=job_service,
            undo_service=container.get("undo_service"),
            service_locator=container.get,
        ),
    )

    migrate_all()
    # Settings wiring direction (manifest cycle fix, P0 FASE 1):
    # settings_coordinator is constructed FIRST without any settings_service
    # dependency; settings_service consumes the coordinator. The coordinator
    # never depends on settings_service — playback/queue/worker are late-wired
    # in composition/settings.py as explicit wiring, not manifest deps.
    coordinator = SettingsRuntimeCoordinator()
    svc = SettingsService(coordinator=coordinator, event_bus=eb)
    container.register("settings_coordinator", coordinator)
    container.register("settings_service", svc)
