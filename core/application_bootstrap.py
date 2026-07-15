"""ApplicationBootstrap — single productive startup for QML application.
API: build()->start()->create_bridges()->register_context(engine)->load_qml(engine)->shutdown().
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtQml import QQmlApplicationEngine

from core.service_container import ServiceContainer

logger = logging.getLogger("michi.bootstrap")


class ApplicationBootstrap:
    def __init__(self):
        self.container = ServiceContainer()
        self._bridges: dict[str, object] = {}

    def build(self):
        logger.info("Bootstrap: building services")
        self._build_config()
        self._open_database()
        self._build_repositories()
        self._build_workers()
        self._build_settings()
        self._build_domain_services()
        self._build_action_registry()
        return self

    def start(self):
        logger.info("Bootstrap: starting services")
        self.container.start()
        logger.info("Bootstrap: READY")
        return self

    def create_bridges(self):
        from ui_qml_bridge.bridge_factory import create_all_bridges
        self._bridges = create_all_bridges(self.container)
        return self._bridges

    def register_context(self, engine: QQmlApplicationEngine):
        from ui_qml_bridge.context_registrar import ContextRegistrar
        from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
        registrar = ContextRegistrar(engine)
        for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
            bridge = self._bridges.get(bridge_key)
            if bridge is not None:
                registrar.register(qml_name, bridge)
        eq_bridge = self._bridges.get("eq")
        if eq_bridge:
            registrar.register("eqBridge", eq_bridge)
        audit = registrar.audit()
        logger.info("Bootstrap: registered %d context properties", audit["total"])
        if audit["duplicates"]:
            logger.warning("Bootstrap: duplicate context: %s", audit["duplicates"])
        return registrar

    def load_qml(self, engine: QQmlApplicationEngine, qml_path: str | None = None) -> bool:
        if qml_path is None:
            qml_path = str(Path(__file__).resolve().parent.parent / "ui_qml" / "Main.qml")
        engine.addImportPath(str(Path(qml_path).parent.parent))
        engine.load(qml_path)
        if not engine.rootObjects():
            logger.error("Failed to load QML root objects")
            return False
        app_bridge = self._bridges.get("app")
        if app_bridge and hasattr(app_bridge, 'setReady'):
            app_bridge.setReady()
        return True

    def shutdown(self):
        logger.info("Bootstrap: shutting down")
        self.container.shutdown()

    def _build_config(self):
        from core.settings_manager import SETTINGS
        self.container.register("settings_manager", SETTINGS)

    def _open_database(self):
        from library.library_db import LibraryDB
        from core.paths import database_path
        db = LibraryDB(database_path())
        self.container.register("connection_factory", db)

    def _build_repositories(self):
        from core.library.repositories.track_repository import TrackRepository
        from core.library.repositories.album_repository import AlbumRepository
        from core.library.repositories.artist_repository import ArtistRepository
        cf = self.container.get("connection_factory")
        self.container.register("track_repository", TrackRepository(cf))
        self.container.register("album_repository", AlbumRepository(cf))
        self.container.register("artist_repository", ArtistRepository(cf))

    def _build_workers(self):
        from core.worker_manager import WorkerManager
        from ui_qml_bridge.query_executor import QueryExecutor
        from core.job_service import JobService
        wm = WorkerManager(max_workers=4)
        qe = QueryExecutor(worker_manager=wm)
        js = JobService()
        self.container.register("worker_manager", wm)
        self.container.register("query_executor", qe)
        self.container.register("job_service", js)

    def _build_settings(self):
        from core.settings_service import SettingsService
        from core.settings_runtime_coordinator import SettingsRuntimeCoordinator
        from core.settings_migrations import migrate_all
        migrate_all()
        coordinator = SettingsRuntimeCoordinator()
        svc = SettingsService()
        self.container.register("settings_coordinator", coordinator)
        self.container.register("settings_service", svc)

    def _build_domain_services(self):
        from core.playlist_service import PlaylistService
        from core.history_query_service import HistoryQueryService
        from core.global_search_service import GlobalSearchService
        from core.library_query_service import LibraryQueryService
        from core.queue_service import QueueService
        from core.audio_lab.audio_lab_service import AudioLabService
        from core.metadata_service import MetadataService
        from core.smart_tagging_service import SmartTaggingService
        from core.library_doctor.library_doctor_scan_service import LibraryDoctorScanService
        from core.device_sync_service import DeviceSyncService
        from core.notification_service import NotificationService
        from ui_qml_bridge.action_registry import ActionRegistry
        cf = self.container.get("connection_factory")
        wm = self.container.get("worker_manager")
        lqs = LibraryQueryService(cf)
        hqs = HistoryQueryService(cf)
        gss = GlobalSearchService(cf)
        ps = PlaylistService(cf)
        qs = QueueService()
        audio = AudioLabService(worker_manager=wm)
        ms = MetadataService(worker_manager=wm)
        sts = SmartTaggingService()
        lds = LibraryDoctorScanService(cf)
        dss = DeviceSyncService(worker_manager=wm)
        ns = NotificationService()
        ar = ActionRegistry()
        self.container.register("library_query_service", lqs)
        self.container.register("history_query_service", hqs)
        self.container.register("global_search_service", gss)
        self.container.register("playlist_service", ps)
        self.container.register("queue_service", qs)
        self.container.register("audio_lab_service", audio)
        self.container.register("metadata_service", ms)
        self.container.register("smart_tagging_service", sts)
        self.container.register("library_doctor_service", lds)
        self.container.register("device_sync_service", dss)
        self.container.register("notification_service", ns)
        self.container.register("action_registry", ar)

    def _build_action_registry(self):
        ar = self.container.get("action_registry")
        ar.register("play", {"scope": "track", "handler": "playback_service.play"})
        ar.register("pause", {"scope": "playback", "handler": "playback_service.pause"})
        ar.register("next", {"scope": "playback", "handler": "playback_service.next"})
        ar.register("queue_add", {"scope": "track", "handler": "queue_service.add"})
        ar.register("favorite", {"scope": "track", "handler": "track_action_service.toggle_favorite"})

    def get_queue_service(self):
        return self.container.get("queue_service")

    def get_worker_manager(self):
        return self.container.get("worker_manager")

    def get_query_executor(self):
        return self.container.get("query_executor")
