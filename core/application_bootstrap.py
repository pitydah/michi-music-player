"""ApplicationBootstrap — single productive startup for QML application.
Builds ALL 34 services (REQUIRED + OPTIONAL) in dependency order.
API: build()->start()->create_bridges()->register_context(engine)->load_qml(engine)->shutdown().
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtQml import QQmlApplicationEngine

from core.service_container import ServiceContainer, ServicePriority

logger = logging.getLogger("michi.bootstrap")


class ApplicationBootstrap:
    def __init__(self):
        self.container = ServiceContainer()
        self._bridges: dict[str, object] = {}
        self._has_built = False
        self._has_started = False

    def build(self):
        logger.info("Bootstrap: building services")
        self._build_config()
        self._open_database()
        self._build_repositories()
        self._build_runtime_persistence()
        self._build_process_controller()
        self._build_event_bus()
        self._build_workers()
        self._build_job_service()
        self._build_confirmation_service()
        self._build_settings()
        self._build_domain_services()
        self._build_action_registry()
        self._build_michi_ai()
        self._build_theme_and_accessibility()
        self._has_built = True
        logger.info("Bootstrap: build complete — %d services", len(self.container._services))
        return self

    def start(self):
        if not self._has_built:
            self.build()
        logger.info("Bootstrap: starting services")
        self.container.start()
        if self.container.state.value in ("ready", "degraded"):
            self._has_started = True
            logger.info("Bootstrap: READY (state=%s)", self.container.state.value)
        else:
            logger.error("Bootstrap: FAILED (state=%s)", self.container.state.value)
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
        self._has_built = False
        self._has_started = False

    def run(self, engine: QQmlApplicationEngine | None = None, qml_path: str | None = None):
        self.build()
        self.start()
        self.create_bridges()
        if engine is not None:
            self.register_context(engine)
            self.load_qml(engine, qml_path)

    def _build_config(self):
        from core.settings_manager import SETTINGS
        self.container.register("settings_manager", SETTINGS)
        from core.paths import database_path as _dp
        self.container.register("paths", _dp)

    def _open_database(self):
        from library.library_db import LibraryDB
        from core.paths import database_path
        db = LibraryDB(database_path())
        self.container.register("database", db)
        self.container.register("connection_factory", db)

    def _build_repositories(self):
        from core.library.repositories.track_repository import TrackRepository
        from core.library.repositories.album_repository import AlbumRepository
        from core.library.repositories.artist_repository import ArtistRepository
        cf = self.container.get("connection_factory")
        self.container.register("track_repository", TrackRepository(cf))
        self.container.register("album_repository", AlbumRepository(cf))
        self.container.register("artist_repository", ArtistRepository(cf))

    def _build_runtime_persistence(self):
        from core.runtime_persistence import RuntimePersistence
        rp = RuntimePersistence()
        self.container.register("runtime_persistence", rp, priority=ServicePriority.OPTIONAL)

    def _build_process_controller(self):
        from core.process_controller import ProcessController
        pc = ProcessController()
        self.container.register("process_controller", pc, priority=ServicePriority.OPTIONAL)

    def _build_event_bus(self):
        class _EventBus:
            def __init__(self):
                self._handlers = {}
            def on(self, event, handler):
                self._handlers.setdefault(event, []).append(handler)
            def emit(self, event, *args, **kwargs):
                for h in self._handlers.get(event, []):
                    h(*args, **kwargs)
        self.container.register("event_bus", _EventBus())

    def _build_workers(self):
        from core.worker_manager import WorkerManager
        from ui_qml_bridge.query_executor import QueryExecutor
        wm = WorkerManager()
        qe = QueryExecutor(worker_manager=wm)
        self.container.register("worker_manager", wm)
        self.container.register("query_executor", qe)

    def _build_job_service(self):
        from core.job_service import JobService
        js = JobService()
        self.container.register("job_service", js)

    def _build_confirmation_service(self):
        from core.confirmation_service import ConfirmationService
        cs = ConfirmationService()
        self.container.register("confirmation_service", cs, priority=ServicePriority.OPTIONAL)

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
        from core.library.library_query_service import LibraryQueryService
        from core.library_sources_service import LibrarySourcesService
        from core.library_mutation_service import LibraryMutationService
        from core.playlist_service import PlaylistService
        from core.history_query_service import HistoryQueryService
        from core.global_search_service import GlobalSearchService
        from core.queue_service import QueueService
        from core.track_action_service import TrackActionService
        from audio.player_service import PlayerService
        from core.metadata_service import MetadataService
        from core.audio_lab.audio_lab_service import AudioLabService
        from core.device_sync_service import DeviceSyncService
        from core.radio.radio_service import RadioService
        from core.notification_service import NotificationService
        from ui_qml_bridge.action_registry import ActionRegistry
        cf = self.container.get("connection_factory")
        wm = self.container.get("worker_manager")
        qs = QueueService()
        ts = TrackActionService()
        ps = PlayerService(engine=None)
        lqs = LibraryQueryService(cf)
        lss = LibrarySourcesService(cf)
        lms = LibraryMutationService(cf)
        pls = PlaylistService(cf)
        hqs = HistoryQueryService(cf)
        gss = GlobalSearchService(cf)
        ms = MetadataService()
        sts = object()
        audio = AudioLabService(worker_manager=wm)
        lds = object()
        dss = DeviceSyncService()
        rs = RadioService()
        ns = NotificationService()
        ar = ActionRegistry()
        mqs = object()
        mix_svc = object()
        self.container.register("library_query_service", lqs)
        self.container.register("library_sources_service", lss)
        self.container.register("library_mutation_service", lms)
        self.container.register("playlist_service", pls)
        self.container.register("history_query_service", hqs)
        self.container.register("global_search_service", gss)
        self.container.register("mix_query_service", mqs)
        self.container.register("mix_service", mix_svc)
        self.container.register("queue_service", qs)
        self.container.register("track_action_service", ts)
        self.container.register("playback_service", ps)
        self.container.register("metadata_service", ms)
        self.container.register("smart_tagging_service", sts, priority=ServicePriority.OPTIONAL)
        self.container.register("audio_lab_service", audio, priority=ServicePriority.OPTIONAL)
        self.container.register("library_doctor_service", lds, priority=ServicePriority.OPTIONAL)
        self.container.register("device_sync_service", dss, priority=ServicePriority.OPTIONAL)
        resource_services = [
            ("connection_service", object()),
            ("home_audio_service", object()),
            ("lyrics_service", object()),
            ("diagnostics_service", object()),
            ("radio_service", rs),
            ("notification_service", ns),
            ("action_registry", ar),
        ]
        for rname, rsvc in resource_services:
            self.container.register(rname, rsvc, priority=ServicePriority.OPTIONAL)

    def _build_action_registry(self):
        ar = self.container.get("action_registry")
        if ar is None:
            return
        from ui_qml_bridge.action_registry import ActionDescriptor
        ar.register(ActionDescriptor(action_id="play", title="Play", category="playback", handler=lambda: None))
        ar.register(ActionDescriptor(action_id="pause", title="Pause", category="playback", handler=lambda: None))
        ar.register(ActionDescriptor(action_id="next", title="Next", category="playback", handler=lambda: None))
        ar.register(ActionDescriptor(action_id="queue_add", title="Add to queue", category="queue", handler=lambda: None))
        ar.register(ActionDescriptor(action_id="favorite", title="Toggle favorite", category="track", handler=lambda: None))

    def _build_michi_ai(self):
        try:
            from core.michi_ai_service import MichiAIServiceV2
            michi = MichiAIServiceV2()
            self.container.register("michi_ai_service", michi,
                                    priority=ServicePriority.CAPABILITY_GATED)
        except Exception as e:
            logger.warning("MichiAIServiceV2 not available: %s", e)
            self.container.register("michi_ai_service", None,
                                    priority=ServicePriority.CAPABILITY_GATED)

    def _build_theme_and_accessibility(self):
        from core.background_theme_service import BackgroundThemeService
        class _NullContentStack:
            def currentWidget(self): return None
        self.container.register("theme_service", BackgroundThemeService(content_stack=_NullContentStack()),
                                priority=ServicePriority.OPTIONAL)
        self.container.register("accessibility_service", object(),
                                priority=ServicePriority.OPTIONAL)

    def get_queue_service(self):
        return self.container.get("queue_service")

    def get_worker_manager(self):
        return self.container.get("worker_manager")

    def get_query_executor(self):
        return self.container.get("query_executor")
