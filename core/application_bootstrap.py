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
            eb = self.container.get("event_bus")
            cs = ConnectionService(event_bus=eb)
            self.container.register("connection_service", cs, priority=ServicePriority.OPTIONAL)
        except Exception:
            self.container.register("connection_service", None, priority=ServicePriority.OPTIONAL)

    def _build_home_audio_services(self):
        try:
            from core.home_audio_service import HomeAudioService
            eb = self.container.get("event_bus")
            ha = HomeAudioService(event_bus=eb)
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

    def _build_songs_service(self):
        try:
            from core.songs_service import SongsService
            db = self.container.get("database")
            ps = self.container.get("playback_service")
            lqs = self.container.get("library_query_service")
            self.container.register("songs_service", SongsService(db=db, playback_service=ps,
                                    library_query_service=lqs),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_track_service(self):
        try:
            from core.track_service import TrackService
            db = self.container.get("database")
            ps = self.container.get("playback_service")
            self.container.register("track_service", TrackService(db=db, playback_service=ps),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_genres_service(self):
        try:
            from core.genres_service import GenresService
            db = self.container.get("database")
            ps = self.container.get("playback_service")
            self.container.register("genres_service", GenresService(db=db, playback_service=ps),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_folder_service(self):
        try:
            from core.folder_service import FolderService
            db = self.container.get("database")
            wm = self.container.get("worker_manager")
            self.container.register("folder_service", FolderService(db=db, worker_manager=wm),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_micro_server_service(self):
        try:
            from core.micro_server_service import MicroServerService
            db = self.container.get("database")
            self.container.register("micro_server_service", MicroServerService(db=db),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_mobile_sync_service(self):
        try:
            from core.mobile_sync_service import MobileSyncService
            db = self.container.get("database")
            self.container.register("mobile_sync_service", MobileSyncService(db=db),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_cover_art_service(self):
        try:
            from core.cover_art_service import CoverArtService
            self.container.register("cover_art_service", CoverArtService(),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_metadata_editor_service(self):
        try:
            from core.metadata_editor_service import MetadataEditorService
            db = self.container.get("database")
            self.container.register("metadata_editor_service", MetadataEditorService(db=db),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_player_bar_service(self):
        try:
            from core.player_bar_service import PlayerBarService
            ps = self.container.get("playback_service")
            self.container.register("player_bar_service", PlayerBarService(player_service=ps),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_navigation_service(self):
        try:
            from core.navigation_service import NavigationService
            self.container.register("navigation_service", NavigationService(),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_history_export_service(self):
        try:
            from core.history_export_service import HistoryExportService
            db = self.container.get("database")
            self.container.register("history_export_service", HistoryExportService(db=db),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_notification_action_service(self):
        try:
            from core.notification_action_service import NotificationActionService
            nav = self.container.get("navigation_service")
            self.container.register("notification_action_service", NotificationActionService(navigation_service=nav),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_quality_analysis_service(self):
        try:
            from core.quality_analysis_service import QualityAnalysisService
            db = self.container.get("database")
            self.container.register("quality_analysis_service", QualityAnalysisService(db=db),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_album_enrichment_service(self):
        try:
            from core.album_enrichment_service import AlbumEnrichmentService
            db = self.container.get("database")
            self.container.register("album_enrichment_service", AlbumEnrichmentService(db=db),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_artist_enrichment_service(self):
        try:
            from core.artist_enrichment_service import ArtistEnrichmentService
            db = self.container.get("database")
            self.container.register("artist_enrichment_service", ArtistEnrichmentService(db=db),
                                    priority=ServicePriority.OPTIONAL)
        except Exception:
            pass

    def _build_device_discovery_service(self):
        try:
            from core.device_discovery_service import DeviceDiscoveryService
            self.container.register("device_discovery_service", DeviceDiscoveryService(),
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
        self._build_songs_service()
        self._build_track_service()
        self._build_genres_service()
        self._build_folder_service()
        self._build_output_profile_service()
        self._build_equalizer_service()
        self._build_micro_server_service()
        self._build_mobile_sync_service()
        self._build_cover_art_service()
        self._build_metadata_editor_service()
        self._build_player_bar_service()
        self._build_navigation_service()
        self._build_history_export_service()
        self._build_notification_action_service()
        self._build_quality_analysis_service()
        self._build_album_enrichment_service()
        self._build_artist_enrichment_service()
        self._build_device_discovery_service()

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
                                     handler=_handler("playlist_service", "add_track")))
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
                                     handler=_handler("history_query_service", "remove_history_item")))
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
        ar.register(ActionDescriptor(action_id="track.metadata.edit", title="Edit metadata",
                                     category="track", handler=_handler("metadata_service", "edit_file")))
        ar.register(ActionDescriptor(action_id="track.tagging.open", title="Smart tagging",
                                     category="track", handler=_handler("smart_tagging_service", "identify")))
        ar.register(ActionDescriptor(action_id="track.doctor.open", title="Library doctor",
                                     category="track", handler=_handler("library_doctor_service", "scan")))
        ar.register(ActionDescriptor(action_id="queue.reorder", title="Reorder", category="queue",
                                     handler=_handler("queue_service", "reorder")))
        ar.register(ActionDescriptor(action_id="queue.undo", title="Undo", category="queue",
                                     handler=_handler("queue_service", "undo")))
        ar.register(ActionDescriptor(action_id="playlist.duplicate", title="Duplicate", category="playlist",
                                     handler=_handler("playlist_service", "duplicate")))
        ar.register(ActionDescriptor(action_id="playlist.reorder", title="Reorder", category="playlist",
                                     handler=_handler("playlist_service", "reorder")))
        ar.register(ActionDescriptor(action_id="history.clear", title="Clear history", category="history",
                                     handler=_handler("history_query_service", "clear_all")))
        ar.register(ActionDescriptor(action_id="mix.save", title="Save mix", category="mix",
                                     handler=_handler("mix_service", "save")))
        ar.register(ActionDescriptor(action_id="device.pair", title="Pair device", category="devices",
                                     handler=_handler("device_sync_service", "pair")))
        ar.register(ActionDescriptor(action_id="device.sync.plan", title="Sync plan", category="devices",
                                     handler=_handler("device_sync_service", "build_manifest")))
        ar.register(ActionDescriptor(action_id="connection.forget", title="Forget", category="connections",
                                     handler=_handler("connection_service", "forget")))
        ar.register(ActionDescriptor(action_id="home_audio.group", title="Group zones", category="home_audio",
                                     handler=_handler("home_audio_service", "create_group")))
        ar.register(ActionDescriptor(action_id="home_audio.ungroup", title="Ungroup", category="home_audio",
                                     handler=_handler("home_audio_service", "delete_group")))
        ar.register(ActionDescriptor(action_id="home_audio.transfer", title="Transfer", category="home_audio",
                                     handler=_handler("home_audio_service", "transfer_playback")))
        ar.register(ActionDescriptor(action_id="album.play_next", title="Play next",
                                     category="playback",
                                     handler=_handler("album_service", "play_next_album")))
        ar.register(ActionDescriptor(action_id="album.create_playlist", title="Create playlist",
                                     category="playlist",
                                     handler=_handler("album_service", "create_playlist_from_tracks")))
        ar.register(ActionDescriptor(action_id="album.analyze_quality", title="Analyze quality",
                                     category="playback",
                                     handler=_handler("album_service", "analyze_album_quality")))
        ar.register(ActionDescriptor(action_id="album.navigate", title="Navigate to album",
                                     category="navigation",
                                     handler=_handler("album_service", "navigate_to_album_by_title")))
        ar.register(ActionDescriptor(action_id="artist.create_mix", title="Create artist mix",
                                     category="mix",
                                     handler=_handler("artist_service", "create_artist_mix")))
        ar.register(ActionDescriptor(action_id="artist.analyze_discography", title="Analyze discography",
                                     category="playback",
                                     handler=_handler("artist_service", "analyze_artist_discography")))
        ar.register(ActionDescriptor(action_id="artist.create_playlist", title="Create playlist",
                                     category="playlist",
                                     handler=_handler("artist_service", "create_playlist_from_artist")))
        ar.register(ActionDescriptor(action_id="genre.play", title="Play genre",
                                     category="playback",
                                     handler=_handler("genres_service", "play_genre")))
        # ── Additional actions ──
        ar.register(ActionDescriptor(action_id="playback.shuffle", title="Shuffle on", category="playback", handler=_handler("playback_service", "toggle_shuffle")))
        ar.register(ActionDescriptor(action_id="playback.repeat", title="Repeat toggle", category="playback", handler=_handler("playback_service", "toggle_repeat")))
        ar.register(ActionDescriptor(action_id="playback.volume.up", title="Volume up", category="playback", handler=_handler("playback_service", "volume_up")))
        ar.register(ActionDescriptor(action_id="playback.volume.down", title="Volume down", category="playback", handler=_handler("playback_service", "volume_down")))
        ar.register(ActionDescriptor(action_id="playback.seek", title="Seek", category="playback", handler=_handler("playback_service", "seek")))
        ar.register(ActionDescriptor(action_id="library.scan", title="Scan library", category="library", handler=_handler("library_mutation_service", "scan")))
        ar.register(ActionDescriptor(action_id="library.refresh", title="Refresh", category="library", handler=_handler("library_service", "load")))
        ar.register(ActionDescriptor(action_id="library.songs", title="Songs", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="library.albums", title="Albums", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="library.artists", title="Artists", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="library.genres", title="Genres", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="library.folders", title="Folders", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.home", title="Home", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.back", title="Back", category="navigation", handler=_handler("navigation_service", "back")))
        ar.register(ActionDescriptor(action_id="nav.library", title="Library", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.settings", title="Settings", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.diagnostics", title="Diagnostics", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.queue", title="Queue", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.playlists", title="Playlists", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.mix", title="Mix", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.radio", title="Radio", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.devices", title="Devices", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.connections", title="Connections", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.home_audio", title="Home Audio", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.nowplaying", title="Now Playing", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="device.info", title="Device info", category="devices", handler=_handler("device_sync_service", "identify")))
        ar.register(ActionDescriptor(action_id="device.free_space", title="Free space", category="devices", handler=_handler("device_sync_service", "free_space")))
        ar.register(ActionDescriptor(action_id="device.eject", title="Eject", category="devices", handler=_handler("device_sync_service", "eject")))
        ar.register(ActionDescriptor(action_id="connection.info", title="Connection info", category="connections", handler=_handler("connection_service", "get_connections")))
        ar.register(ActionDescriptor(action_id="connection.latency", title="Latency", category="connections", handler=_handler("connection_service", "diagnose")))
        ar.register(ActionDescriptor(action_id="radio.add", title="Add station", category="radio", handler=_handler("radio_service", "add_station")))
        ar.register(ActionDescriptor(action_id="radio.edit", title="Edit station", category="radio", handler=_handler("radio_service", "edit_station")))
        ar.register(ActionDescriptor(action_id="radio.delete", title="Delete station", category="radio", handler=_handler("radio_service", "delete_station")))
        ar.register(ActionDescriptor(action_id="radio.search", title="Search radio", category="radio", handler=_handler("radio_service", "search_stations")))
        ar.register(ActionDescriptor(action_id="radio.favorite", title="Favorite", category="radio", handler=_handler("radio_service", "favorite_station")))
        ar.register(ActionDescriptor(action_id="radio.import", title="Import stations", category="radio", handler=_handler("radio_service", "import_stations")))
        ar.register(ActionDescriptor(action_id="radio.export", title="Export stations", category="radio", handler=_handler("radio_service", "export_stations")))
        ar.register(ActionDescriptor(action_id="queue.play", title="Play from queue", category="queue", handler=_handler("queue_service", "play_next")))
        ar.register(ActionDescriptor(action_id="queue.move_up", title="Move up", category="queue", handler=_handler("queue_service", "move")))
        ar.register(ActionDescriptor(action_id="queue.move_down", title="Move down", category="queue", handler=_handler("queue_service", "reorder")))
        ar.register(ActionDescriptor(action_id="playlist.info", title="Playlist info", category="playlist", handler=_handler("playlist_service", "get_info")))
        ar.register(ActionDescriptor(action_id="playlist.duplicate", title="Duplicate", category="playlist", handler=_handler("playlist_service", "duplicate")))
        ar.register(ActionDescriptor(action_id="playlist.add_album", title="Add album", category="playlist", handler=_handler("playlist_service", "add_track")))
        ar.register(ActionDescriptor(action_id="mix.daily", title="Daily mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.favorites", title="Favorites mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.recent", title="Recent mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.unplayed", title="Unplayed mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.most_played", title="Most played mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.artist", title="Artist mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.genre", title="Genre mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.decade", title="Decade mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.quality", title="Quality mix", category="mix", handler=_handler("mix_service", "generate")))
        ar.register(ActionDescriptor(action_id="mix.explain", title="Explain mix", category="mix", handler=_handler("mix_service", "explain")))
        ar.register(ActionDescriptor(action_id="history.export.csv", title="Export CSV", category="history", handler=_handler("history_query_service", "export_history")))
        ar.register(ActionDescriptor(action_id="history.export.json", title="Export JSON", category="history", handler=_handler("history_export_service", "export_json")))
        ar.register(ActionDescriptor(action_id="history.stats", title="Statistics", category="history", handler=_handler("history_query_service", "statistics")))
        ar.register(ActionDescriptor(action_id="album.shuffle", title="Shuffle album", category="playback", handler=_handler("album_service", "play_album")))
        ar.register(ActionDescriptor(action_id="album.info", title="Album info", category="navigation", handler=_handler("album_service", "navigate_to_album_by_title")))
        ar.register(ActionDescriptor(action_id="artist.shuffle", title="Shuffle artist", category="playback", handler=_handler("artist_service", "play_artist")))
        ar.register(ActionDescriptor(action_id="artist.albums", title="Artist albums", category="navigation", handler=_handler("artist_service", "get_albums")))
        ar.register(ActionDescriptor(action_id="artist.tracks", title="Artist tracks", category="navigation", handler=_handler("artist_service", "get_tracks")))
        ar.register(ActionDescriptor(action_id="library.filter.artist", title="Filter by artist", category="library", handler=_handler("library_query_service", "tracks_for_artist")))
        ar.register(ActionDescriptor(action_id="library.filter.album", title="Filter by album", category="library", handler=_handler("library_query_service", "tracks_for_album")))
        ar.register(ActionDescriptor(action_id="library.filter.genre", title="Filter by genre", category="library", handler=_handler("genres_service", "play_genre")))
        ar.register(ActionDescriptor(action_id="library.view.grid", title="Grid view", category="library", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="library.view.list", title="List view", category="library", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="library.select.all", title="Select all", category="library", handler=_handler("library_query_service", "search")))
        ar.register(ActionDescriptor(action_id="songs.play", title="Play songs", category="playback", handler=_handler("songs_service", "play_items")))
        ar.register(ActionDescriptor(action_id="songs.enqueue", title="Enqueue songs", category="queue", handler=_handler("songs_service", "queue_items")))
        ar.register(ActionDescriptor(action_id="track.locate", title="Locate file", category="track", handler=_handler("track_service", "locate_file")))
        ar.register(ActionDescriptor(action_id="folder.scan", title="Scan folder", category="folder", handler=_handler("folder_service", "scan")))
        ar.register(ActionDescriptor(action_id="folder.integrity", title="Check integrity", category="folder", handler=_handler("folder_service", "integrity_check")))
        ar.register(ActionDescriptor(action_id="track.favorite.add", title="Add favorite", category="track", handler=_handler("track_action_service", "add_favorite")))
        ar.register(ActionDescriptor(action_id="track.favorite.remove", title="Remove favorite", category="track", handler=_handler("track_action_service", "remove_favorite")))
        ar.register(ActionDescriptor(action_id="track.share", title="Share track", category="track", handler=_handler("track_action_service", "share")))
        ar.register(ActionDescriptor(action_id="playlist.reorder.up", title="Move up", category="playlist", handler=_handler("playlist_service", "reorder")))
        ar.register(ActionDescriptor(action_id="playlist.reorder.down", title="Move down", category="playlist", handler=_handler("playlist_service", "reorder")))
        ar.register(ActionDescriptor(action_id="playlist.clear", title="Clear playlist", category="playlist", handler=_handler("playlist_service", "clear")))
        ar.register(ActionDescriptor(action_id="playlist.batch_add", title="Batch add", category="playlist", handler=_handler("playlist_service", "batch_add")))
        ar.register(ActionDescriptor(action_id="mix.cancel", title="Cancel mix", category="mix", handler=_handler("mix_service", "cancel")))
        ar.register(ActionDescriptor(action_id="mix.playlist", title="Save as playlist", category="mix", handler=_handler("mix_service", "save_playlist")))
        ar.register(ActionDescriptor(action_id="mix.explain", title="Explain", category="mix", handler=_handler("mix_service", "explain")))
        ar.register(ActionDescriptor(action_id="device.transcode.lossless", title="Lossless", category="devices", handler=_handler("device_sync_service", "transcode_policy")))
        ar.register(ActionDescriptor(action_id="device.transcode.high", title="High quality", category="devices", handler=_handler("device_sync_service", "transcode_policy")))
        ar.register(ActionDescriptor(action_id="device.transcode.medium", title="Medium", category="devices", handler=_handler("device_sync_service", "transcode_policy")))
        ar.register(ActionDescriptor(action_id="device.sync.profile", title="Sync profile", category="devices", handler=_handler("device_sync_service", "profiles")))
        ar.register(ActionDescriptor(action_id="device.naming.keep", title="Keep names", category="devices", handler=_handler("device_sync_service", "naming_policy")))
        ar.register(ActionDescriptor(action_id="device.collision.skip", title="Skip duplicates", category="devices", handler=_handler("device_sync_service", "collision_policy")))
        ar.register(ActionDescriptor(action_id="device.collision.overwrite", title="Overwrite", category="devices", handler=_handler("device_sync_service", "collision_policy")))
        ar.register(ActionDescriptor(action_id="device.collision.rename", title="Rename", category="devices", handler=_handler("device_sync_service", "collision_policy")))
        ar.register(ActionDescriptor(action_id="home_audio.discover", title="Discover zones", category="home_audio", handler=_handler("home_audio_service", "discover_zones")))
        ar.register(ActionDescriptor(action_id="home_audio.test", title="Test connection", category="home_audio", handler=_handler("home_audio_service", "test_connection")))
        ar.register(ActionDescriptor(action_id="home_audio.reconnect", title="Reconnect", category="home_audio", handler=_handler("home_audio_service", "reconnect")))
        ar.register(ActionDescriptor(action_id="home_audio.volume.up", title="Volume up", category="home_audio", handler=_handler("home_audio_service", "set_volume")))
        ar.register(ActionDescriptor(action_id="home_audio.volume.down", title="Volume down", category="home_audio", handler=_handler("home_audio_service", "set_volume")))
        ar.register(ActionDescriptor(action_id="home_audio.mute", title="Mute", category="home_audio", handler=_handler("home_audio_service", "mute")))
        ar.register(ActionDescriptor(action_id="home_audio.unmute", title="Unmute", category="home_audio", handler=_handler("home_audio_service", "mute")))
        ar.register(ActionDescriptor(action_id="radio.buffer", title="Buffer", category="radio", handler=_handler("radio_service", "set_buffer_ms")))
        ar.register(ActionDescriptor(action_id="radio.timeout", title="Timeout", category="radio", handler=_handler("radio_service", "set_timeout_s")))
        ar.register(ActionDescriptor(action_id="radio.reconnect.auto", title="Auto reconnect", category="radio", handler=_handler("radio_service", "set_reconnect_policy")))
        ar.register(ActionDescriptor(action_id="eq.enable", title="Enable EQ", category="equalizer", handler=_handler("equalizer_service", "set_enabled")))
        ar.register(ActionDescriptor(action_id="eq.disable", title="Disable EQ", category="equalizer", handler=_handler("equalizer_service", "set_enabled")))
        ar.register(ActionDescriptor(action_id="eq.reset", title="Reset EQ", category="equalizer", handler=_handler("equalizer_service", "reset")))
        ar.register(ActionDescriptor(action_id="eq.preset.save", title="Save preset", category="equalizer", handler=_handler("equalizer_service", "save_preset")))
        ar.register(ActionDescriptor(action_id="eq.preset.load", title="Load preset", category="equalizer", handler=_handler("equalizer_service", "load_preset")))
        ar.register(ActionDescriptor(action_id="eq.preset.delete", title="Delete preset", category="equalizer", handler=_handler("equalizer_service", "delete_preset")))
        ar.register(ActionDescriptor(action_id="output.profile.list", title="List profiles", category="outputs", handler=_handler("output_profile_service", "list_profiles")))
        ar.register(ActionDescriptor(action_id="output.profile.apply", title="Apply profile", category="outputs", handler=_handler("output_profile_service", "apply")))
        ar.register(ActionDescriptor(action_id="notif.retry", title="Retry", category="notifications", handler=_handler("notification_service", "retry")))
        ar.register(ActionDescriptor(action_id="notif.undo", title="Undo", category="notifications", handler=_handler("notification_service", "undo")))
        ar.register(ActionDescriptor(action_id="notif.open_job", title="Open job", category="notifications", handler=_handler("notification_service", "open_job")))
        ar.register(ActionDescriptor(action_id="notif.open_track", title="Open track", category="notifications", handler=_handler("notification_service", "open_track")))
        ar.register(ActionDescriptor(action_id="notif.open_settings", title="Settings", category="notifications", handler=_handler("notification_service", "open_settings")))
        ar.register(ActionDescriptor(action_id="notif.open_diagnostics", title="Diagnostics", category="notifications", handler=_handler("notification_service", "open_diagnostics")))
        ar.register(ActionDescriptor(action_id="genre.list", title="List genres", category="library", handler=_handler("genres_service", "list_genres")))
        ar.register(ActionDescriptor(action_id="genre.normalize", title="Normalize genre", category="library", handler=_handler("genres_service", "normalize_genre")))
        ar.register(ActionDescriptor(action_id="diagnostics.audio.analyze", title="Analyze audio", category="diagnostics", handler=_handler("diagnostics_service", "analyse_file")))
        ar.register(ActionDescriptor(action_id="diagnostics.library.check", title="Check library", category="diagnostics", handler=_handler("diagnostics_service", "check_library")))
        ar.register(ActionDescriptor(action_id="diagnostics.playback.check", title="Check playback", category="diagnostics", handler=_handler("diagnostics_service", "check_playback")))
        ar.register(ActionDescriptor(action_id="diagnostics.database.check", title="Check database", category="diagnostics", handler=_handler("diagnostics_service", "check_database")))
        ar.register(ActionDescriptor(action_id="micro_server.import.tracks", title="Import tracks", category="server", handler=_handler("micro_server_service", "import_tracks")))
        ar.register(ActionDescriptor(action_id="micro_server.import.album", title="Import album", category="server", handler=_handler("micro_server_service", "import_album")))
        ar.register(ActionDescriptor(action_id="micro_server.import.artist", title="Import artist", category="server", handler=_handler("micro_server_service", "import_artist")))
        ar.register(ActionDescriptor(action_id="album.enrich", title="Enrich album", category="metadata", handler=_handler("album_enrichment_service", "fetch_metadata")))
        ar.register(ActionDescriptor(action_id="artist.enrich", title="Enrich artist", category="metadata", handler=_handler("artist_enrichment_service", "fetch_image")))
        ar.register(ActionDescriptor(action_id="artist.aliases", title="Artist aliases", category="metadata", handler=_handler("artist_service", "resolve_artist_aliases")))
        ar.register(ActionDescriptor(action_id="device.discover.mtp", title="Discover MTP", category="devices", handler=_handler("device_discovery_service", "discover_mtp")))
        ar.register(ActionDescriptor(action_id="device.discover.ums", title="Discover UMS", category="devices", handler=_handler("device_discovery_service", "discover_ums")))
        ar.register(ActionDescriptor(action_id="device.discover.network", title="Discover network", category="devices", handler=_handler("device_discovery_service", "discover_network")))
        ar.register(ActionDescriptor(action_id="disc_lab.scan", title="Scan disc", category="disc_lab", handler=_handler("disc_lab_service", "detect_disc")))
        ar.register(ActionDescriptor(action_id="disc_lab.rip", title="Rip disc", category="disc_lab", handler=_handler("disc_lab_service", "start_rip")))
        ar.register(ActionDescriptor(action_id="disc_lab.cancel", title="Cancel rip", category="disc_lab", handler=_handler("disc_lab_service", "cancel")))
        ar.register(ActionDescriptor(action_id="disc_lab.plan", title="Rip plan", category="disc_lab", handler=_handler("disc_lab_service", "rip_plan")))
        ar.register(ActionDescriptor(action_id="track.quality", title="Analyze quality", category="track", handler=_handler("quality_analysis_service", "analyze_track")))
        ar.register(ActionDescriptor(action_id="nav.notifications", title="Notifications", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.equalizer", title="Equalizer", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.outputs", title="Outputs", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.library_doctor", title="Library Doctor", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.metadata", title="Metadata", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.tagging", title="Tagging", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.disc_lab", title="Disc Lab", category="navigation", handler=_handler("navigation_service", "navigate")))
        ar.register(ActionDescriptor(action_id="nav.audio_lab", title="Audio Lab", category="navigation", handler=_handler("navigation_service", "navigate")))

    def _build_michi_ai(self):
        try:
            nav_svc = self.container.get("navigation_service")
            from core.assistant_initializer import create_assistant_composition
            comp = create_assistant_composition(
                metadata_service=self.container.get("metadata_service"),
                queue_service=self.container.get("queue_service"),
                playlist_service=self.container.get("playlist_service"),
                confirmation_service=self.container.get("confirmation_service"),
                job_service=self.container.get("job_service"),
                settings_service=self.container.get("settings_service"),
                player_service=self.container.get("playback_service"),
                library_db=self.container.get("database"),
                audio_lab_service=self.container.get("audio_lab_service"),
                sync_manager=self.container.get("device_sync_service"),
                diagnostics_service=self.container.get("diagnostics_service"),
                mix_service=self.container.get("mix_service"),
                navigation_service=nav_svc,
                lyrics_service=self.container.get("lyrics_service"),
                connection_service=self.container.get("connection_service"),
                home_audio_service=self.container.get("home_audio_service"),
                library_doctor_service=self.container.get("library_doctor_service"),
            )
            self.container.register("michi_ai_service", comp.core_service,
                                    priority=ServicePriority.CAPABILITY_GATED)
        except Exception as e:
            logger.error("Michi AI composition failed: %s", e, exc_info=True)

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
