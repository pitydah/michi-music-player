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
        from core.library_mutation_service import LibraryMutationService
        self.container.register("library_query_service", LibraryQueryService(cf))
        self.container.register("library_sources_service", LibrarySourcesService(cf))
        self.container.register("library_mutation_service", LibraryMutationService(cf))

    def _build_playback_services(self):
        from audio.player_service import PlayerService
        from core.queue_service import QueueService
        from core.track_action_service import TrackActionService
        from core.notification_service import NotificationService
        qs = QueueService()
        ts = TrackActionService()
        ps = PlayerService(engine=None)
        ns = NotificationService()
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
        from core.audio_lab.audio_lab_service import AudioLabService
        audio = AudioLabService(worker_manager=wm)
        self.container.register("audio_lab_service", audio, priority=ServicePriority.OPTIONAL)
        try:
            from core.diagnostics_service import DiagnosticsService
            db = self.container.get("database")
            ps = self.container.get("playback_service")
            ds = DiagnosticsService(db=db, audio_diagnostics=True,
                                     player_service=ps, worker_manager=wm)
            self.container.register("diagnostics_service", ds, priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("diagnostics_service", None, priority=ServicePriority.OPTIONAL)

    def _build_radio_services(self):
        from core.radio.radio_service import RadioService
        rs = RadioService()
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
            mix_svc = MixService(db=db, recommendation_service=mqs,
                                  smart_mix_service=sms,
                                  library_query_service=lqs,
                                  playlist_service=pls)
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
            cs = ConnectionService()
            self.container.register("connection_service", cs, priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("connection_service", None, priority=ServicePriority.OPTIONAL)

    def _build_home_audio_services(self):
        try:
            from core.home_audio_service import HomeAudioService
            ha = HomeAudioService()
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

    def _build_library_data_service(self):
        try:
            from core.library_data_service import LibraryDataService
            db = self.container.get("database")
            self.container.register("library_data_service", LibraryDataService(db=db),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_output_profile_service(self):
        try:
            from core.output_profile_service import OutputProfileService
            ps = self.container.get("playback_service")
            self.container.register("output_profile_service", OutputProfileService(player_service=ps),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_equalizer_service(self):
        try:
            from core.equalizer_service import EqualizerService
            ps = self.container.get("playback_service")
            self.container.register("equalizer_service", EqualizerService(player_service=ps),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_domain_services(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        self.container.register("action_registry", ar, priority=ServicePriority.OPTIONAL)
        self._build_library_services()
        self._build_playback_services()
        self._build_playlist_and_history_services()
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
        self._build_library_data_service()
        self._build_output_profile_service()
        self._build_equalizer_service()

    def _build_action_registry(self):
        ar = self.container.get("action_registry")
        if ar is None:
            return
        from ui_qml_bridge.action_registry import ActionDescriptor

        def _handler(service_name: str, method: str, *default_args):
            svc = self.container.get(service_name)
            def _call(*args):
                if svc and hasattr(svc, method):
                    try:
                        return getattr(svc, method)(*default_args, *args)
                    except Exception:
                        pass
            return _call

        ar.register(ActionDescriptor(action_id="play", title="Play", category="playback",
                                     handler=_handler("playback_service", "play")))
        ar.register(ActionDescriptor(action_id="pause", title="Pause", category="playback",
                                     handler=_handler("playback_service", "pause")))
        ar.register(ActionDescriptor(action_id="next", title="Next", category="playback",
                                     handler=_handler("playback_service", "next")))
        ar.register(ActionDescriptor(action_id="previous", title="Prev", category="playback",
                                     handler=_handler("playback_service", "previous")))
        ar.register(ActionDescriptor(action_id="stop", title="Stop", category="playback",
                                     handler=_handler("playback_service", "stop")))
        ar.register(ActionDescriptor(action_id="track.play", title="Play", category="playback",
                                     handler=_handler("playback_service", "play_file")))
        ar.register(ActionDescriptor(action_id="track.play_next", title="Play next", category="queue",
                                     handler=_handler("queue_service", "play_next")))
        ar.register(ActionDescriptor(action_id="track.enqueue", title="Enqueue", category="queue",
                                     handler=_handler("queue_service", "enqueue")))
        ar.register(ActionDescriptor(action_id="track.favorite.toggle", title="Toggle favorite",
                                     category="track", handler=_handler("track_action_service", "toggle_favorite")))
        ar.register(ActionDescriptor(action_id="album.play", title="Play album", category="playback",
                                     handler=_handler("album_service", "play_album")))
        ar.register(ActionDescriptor(action_id="album.enqueue", title="Enqueue album", category="queue",
                                     handler=_handler("album_service", "queue_album")))
        ar.register(ActionDescriptor(action_id="album.add_to_playlist", title="Add to playlist",
                                     category="playlist",
                                     handler=_handler("playlist_service", "add_to_playlist")))
        ar.register(ActionDescriptor(action_id="artist.play", title="Play artist", category="playback",
                                     handler=_handler("artist_service", "play_artist")))
        ar.register(ActionDescriptor(action_id="artist.shuffle", title="Shuffle", category="playback",
                                     handler=_handler("playback_service", "shuffle")))
        ar.register(ActionDescriptor(action_id="queue.remove", title="Remove", category="queue",
                                     handler=_handler("queue_service", "remove")))
        ar.register(ActionDescriptor(action_id="queue.clear", title="Clear", category="queue",
                                     handler=_handler("queue_service", "clear")))
        ar.register(ActionDescriptor(action_id="queue.save_playlist", title="Save as playlist",
                                     category="queue",
                                     handler=_handler("queue_service", "save_as_playlist")))
        ar.register(ActionDescriptor(action_id="playlist.create", title="Create", category="playlist",
                                     handler=_handler("playlist_service", "create_playlist")))
        ar.register(ActionDescriptor(action_id="playlist.rename", title="Rename", category="playlist",
                                     handler=_handler("playlist_service", "rename_playlist")))
        ar.register(ActionDescriptor(action_id="playlist.delete", title="Delete", category="playlist",
                                     handler=_handler("playlist_service", "delete_playlist")))
        ar.register(ActionDescriptor(action_id="playlist.add", title="Add track", category="playlist",
                                     handler=_handler("playlist_service", "add_track")))
        ar.register(ActionDescriptor(action_id="playlist.remove", title="Remove track", category="playlist",
                                     handler=_handler("playlist_service", "remove_track")))
        ar.register(ActionDescriptor(action_id="playlist.import", title="Import M3U", category="playlist",
                                     handler=_handler("playlist_service", "import_m3u")))
        ar.register(ActionDescriptor(action_id="playlist.export", title="Export M3U", category="playlist",
                                     handler=_handler("playlist_service", "export_m3u")))
        ar.register(ActionDescriptor(action_id="history.play", title="Play", category="history",
                                     handler=_handler("playback_service", "play_file")))
        ar.register(ActionDescriptor(action_id="history.remove", title="Remove", category="history",
                                     handler=_handler("history_query_service", "remove_entry")))
        ar.register(ActionDescriptor(action_id="mix.generate", title="Generate", category="mix",
                                     handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.cancel", title="Cancel", category="mix",
                                     handler=_handler("mix_service", "cancel")))
        ar.register(ActionDescriptor(action_id="mix.play", title="Play mix", category="playback",
                                     handler=_handler("playback_service", "play_list")))
        ar.register(ActionDescriptor(action_id="mix.enqueue", title="Enqueue mix", category="queue",
                                     handler=_handler("queue_service", "enqueue")))
        ar.register(ActionDescriptor(action_id="device.discover", title="Discover", category="devices",
                                     handler=_handler("device_sync_service", "discover")))
        ar.register(ActionDescriptor(action_id="device.sync.start", title="Start sync", category="devices",
                                     handler=_handler("device_sync_service", "start_sync")))
        ar.register(ActionDescriptor(action_id="device.sync.cancel", title="Cancel sync", category="devices",
                                     handler=_handler("device_sync_service", "cancel_sync")))
        ar.register(ActionDescriptor(action_id="connection.discover", title="Discover", category="connections",
                                     handler=_handler("connection_service", "discover")))
        ar.register(ActionDescriptor(action_id="connection.connect", title="Connect", category="connections",
                                     handler=_handler("connection_service", "connect")))
        ar.register(ActionDescriptor(action_id="connection.disconnect", title="Disconnect", category="connections",
                                     handler=_handler("connection_service", "disconnect")))
        ar.register(ActionDescriptor(action_id="home_audio.volume", title="Volume", category="home_audio",
                                     handler=_handler("home_audio_service", "set_volume")))
        ar.register(ActionDescriptor(action_id="home_audio.mute", title="Mute", category="home_audio",
                                     handler=_handler("home_audio_service", "mute")))
        ar.register(ActionDescriptor(action_id="radio.play", title="Play", category="radio",
                                     handler=_handler("radio_service", "play_station")))
        ar.register(ActionDescriptor(action_id="radio.stop", title="Stop", category="radio",
                                     handler=_handler("radio_service", "stop")))
        ar.register(ActionDescriptor(action_id="settings.open", title="Settings", category="navigation",
                                     handler=_handler("settings_service", "open")))
        ar.register(ActionDescriptor(action_id="diagnostics.open", title="Diagnostics", category="navigation",
                                     handler=_handler("diagnostics_service", "check_all")))

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
        try:
            from core.background_theme_service import BackgroundThemeService
            self.container.register("theme_service", BackgroundThemeService(),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("theme_service", None, priority=ServicePriority.OPTIONAL)
        try:
            from core.accessibility_service import AccessibilityService
            self.container.register("accessibility_service", AccessibilityService(),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("accessibility_service", None, priority=ServicePriority.OPTIONAL)

    def get_queue_service(self):
        return self.container.get("queue_service")

    def get_worker_manager(self):
        return self.container.get("worker_manager")

    def get_query_executor(self):
        return self.container.get("query_executor")
