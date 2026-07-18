"""Infrastructure services — config, database, workers, persistence."""
from __future__ import annotations

from core.service_container import ServiceContainer


def build(container: ServiceContainer) -> None:
    from core.settings_manager import SETTINGS
    from core.paths import database_path as _dp
    from library.library_db import LibraryDB
    from core.runtime_persistence import RuntimePersistence
    from core.process_controller import ProcessController
    from core.event_bus import EventBus
    from core.worker_manager import WorkerManager
    from ui_qml_bridge.query_executor import QueryExecutor
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

    container.register("job_service", JobService())
    container.register("confirmation_service", ConfirmationService())

    migrate_all()
    coordinator = SettingsRuntimeCoordinator()
    svc = SettingsService()
    container.register("settings_coordinator", coordinator)
    container.register("settings_service", svc)
