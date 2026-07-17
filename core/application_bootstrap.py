"""ApplicationBootstrap — single productive startup for QML application.
Builds ALL 34 services (REQUIRED + OPTIONAL) in dependency order.
API: build()->start()->create_bridges()->register_context(engine)->load_qml(engine)->shutdown().
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtQml import QQmlApplicationEngine

from core.service_container import ObservableServiceContainer, ServiceContainer, ServicePriority

logger = logging.getLogger("michi.bootstrap")


class ApplicationBootstrap:
    def __init__(self):
        self.container = ObservableServiceContainer()
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
        from core.event_bus import EventBus
        self.container.register("event_bus", EventBus())

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

    def _build_library_services(self):
        cf = self.container.get("connection_factory")
        from core.library.library_query_service import LibraryQueryService
        from core.library_sources_service import LibrarySourcesService
        from core.metadata_editor_service import MetadataEditorService
        from core.library_service import LibraryService
        db = self.container.get("database")
        wm = self.container.get("worker_manager")
        lqs = LibraryQueryService(cf)
        self.container.register("library_query_service", lqs)
        self.container.register("library_sources_service", LibrarySourcesService(cf))
        self.container.register("library_mutation_service", MetadataEditorService(db=db))
        self.container.register("library_service", LibraryService(db=db, worker_manager=wm, library_query_service=lqs))

    def _build_playback_services(self):
        from audio.player_service import PlayerService
        from core.queue_service import QueueService
        from core.track_action_service import TrackActionService
        from core.notification_service import NotificationService
        from audio.player import GStreamerEngine
        eb = self.container.get("event_bus")
        qs = QueueService(event_bus=eb)
        ts = TrackActionService()
        engine = GStreamerEngine()
        ps = PlayerService(engine=engine, event_bus=eb)
        ns = NotificationService(event_bus=eb)
        self.container.register("queue_service", qs)
        self.container.register("track_action_service", ts)
        self.container.register("playback_service", ps)
        self.container.register("notification_service", ns, priority=ServicePriority.OPTIONAL)

    def _build_playlist_and_history_services(self):
        cf = self.container.get("connection_factory")
        from core.playlist_service import PlaylistService
        from core.history_query_service import HistoryQueryService
        from core.global_search_service import GlobalSearchService
        self.container.register("playlist_service", PlaylistService(cf))
        self.container.register("history_query_service", HistoryQueryService(cf))
        self.container.register("global_search_service", GlobalSearchService(cf))

    def _build_metadata_services(self):
        from core.metadata_service import MetadataService
        ms = MetadataService()
        self.container.register("metadata_service", ms)
        try:
            from core.smart_tagging_service import SmartTaggingService
            wm = self.container.get("worker_manager")
            lqs = self.container.get("library_query_service")
            sts = SmartTaggingService(worker_manager=wm, library_query_service=lqs)
            self.container.register("smart_tagging_service", sts, priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("smart_tagging_service", None, priority=ServicePriority.OPTIONAL)

    def _build_audio_lab_services(self):
        wm = self.container.get("worker_manager")
        db = self.container.get("database")
        from core.audio_lab.audio_lab_service import AudioLabService
        audio = AudioLabService(db=db, worker_manager=wm)
        self.container.register("audio_lab_service", audio, priority=ServicePriority.OPTIONAL)
        try:
            from core.diagnostics_service import DiagnosticsService
            ps = self.container.get("playback_service")
            ds = DiagnosticsService(db=db, audio_diagnostics=True,
                                     player_service=ps, worker_manager=wm)
            self.container.register("diagnostics_service", ds, priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("diagnostics_service", None, priority=ServicePriority.OPTIONAL)

    def _build_radio_services(self):
        from core.radio.radio_service import RadioService
        eb = self.container.get("event_bus")
        rs = RadioService(event_bus=eb)
        self.container.register("radio_service", rs, priority=ServicePriority.OPTIONAL)

    def _build_mix_services(self):
        try:
            from recommendation.smart_mix_service import SmartMixService
            from recommendation.recommendation_service import RecommendationService
            from core.mix_service import MixService
            db = self.container.get("database")
            pls = self.container.get("playlist_service")
            lqs = self.container.get("library_query_service")
            sms = SmartMixService(db)
            mqs = RecommendationService(db)
            eb = self.container.get("event_bus")
            mix_svc = MixService(db=db, recommendation_service=mqs,
                                  smart_mix_service=sms,
                                  library_query_service=lqs,
                                  playlist_service=pls,
                                  event_bus=eb)
            self.container.register("mix_query_service", mqs)
            self.container.register("mix_service", mix_svc)
        except Exception:
            self.container.register("mix_query_service", None)
            self.container.register("mix_service", None)

    def _build_device_services(self):
        from core.device_sync_service import DeviceSyncService
        dss = DeviceSyncService()
        self.container.register("device_sync_service", dss, priority=ServicePriority.OPTIONAL)
        try:
            from core.sync.device_registry import DeviceRegistry
            self.container.register("device_registry", DeviceRegistry(),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_connection_services(self):
        try:
            from core.connection_service import ConnectionService
            from integrations.connections.connection_manager import ConnectionManager
            from integrations.connections.discovery_manager import DiscoveryManager
            from integrations.connections.credentials_store import CredentialsStore
            from integrations.michi_link.client import MichiLinkClient
            eb = self.container.get("event_bus")
            disc_mgr = DiscoveryManager()
            conn_mgr = ConnectionManager()
            creds = CredentialsStore()
            michi = MichiLinkClient()
            cs = ConnectionService(connection_manager=conn_mgr,
                                   discovery_manager=disc_mgr,
                                   credentials_store=creds,
                                   michi_link_client=michi,
                                   event_bus=eb)
            self.container.register("connection_service", cs, priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("connection_service", None, priority=ServicePriority.OPTIONAL)

    def _build_home_audio_services(self):
        try:
            from core.home_audio_service import HomeAudioService
            from integrations.snapcast.group_manager import GroupManager
            from integrations.snapcast.discovery import SnapClientDiscovery
            from integrations.snapcast.snapserver_manager import SnapServerManager
            eb = self.container.get("event_bus")
            disc = SnapClientDiscovery()
            snapserver = SnapServerManager()
            group_mgr = GroupManager()
            ha = HomeAudioService(snapcast_group_manager=group_mgr,
                                  snapcast_discovery=disc,
                                  snapserver_manager=snapserver,
                                  event_bus=eb)
            self.container.register("home_audio_service", ha, priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("home_audio_service", None, priority=ServicePriority.OPTIONAL)

    def _build_lyrics_services(self):
        try:
            from lyrics.lrclib_client import LrcLibClient
            from core.lyrics_service import LyricsService
            wm = self.container.get("worker_manager")
            lrc = LrcLibClient()
            ls = LyricsService(lrclib_client=lrc, worker_manager=wm)
            self.container.register("lyrics_service", ls, priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("lyrics_service", None, priority=ServicePriority.OPTIONAL)

    def _build_album_service(self):
        try:
            from core.album_service import AlbumService
            db = self.container.get("database")
            ps = self.container.get("playback_service")
            self.container.register("album_service", AlbumService(db=db, playback_service=ps),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_artist_service(self):
        try:
            from core.artist_service import ArtistService
            db = self.container.get("database")
            ps = self.container.get("playback_service")
            self.container.register("artist_service", ArtistService(db=db, playback_service=ps),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_domain_services(self):
        self._build_library_services()
        self._build_playlist_and_history_services()
        self._build_playback_services()
        self._build_metadata_services()
        self._build_audio_lab_services()
        self._build_radio_services()
        self._build_mix_services()
        self._build_device_services()
        self._build_connection_services()
        self._build_home_audio_services()
        self._build_lyrics_services()
        self._build_album_service()
        self._build_artist_service()

    def _build_action_registry(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        self.container.register("action_registry", ActionRegistry())

    def _build_michi_ai(self):
        try:
            from core.michi_ai_service import MichiAIService
            svc = MichiAIService()
            self.container.register("michi_ai_service", svc, priority=ServicePriority.CAPABILITY_GATED)
        except Exception:
            self.container.register("michi_ai_service", None, priority=ServicePriority.CAPABILITY_GATED)

    def _build_theme_and_accessibility(self):
        try:
            from core.theme_service import ThemeService
            self.container.register("theme_service", ThemeService(), priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("theme_service", None, priority=ServicePriority.OPTIONAL)
        try:
            from core.accessibility_service import AccessibilityService
            self.container.register("accessibility_service", AccessibilityService(), priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("accessibility_service", None, priority=ServicePriority.OPTIONAL)
