"""BridgeFactory — creates bridges once, injects ServiceContainer.

Does not open databases, construct backends, or start services.
Does not cache or create core services internally.
"""
from __future__ import annotations

import logging
from pathlib import Path
from PySide6.QtCore import QObject

from ui_qml_bridge.service_bundle import ServiceBundle

logger = logging.getLogger("michi.bridge_factory")


class BridgeFactory(QObject):
    """Creates each bridge exactly once with injected dependencies from ServiceContainer."""

    def __init__(self, services: ServiceBundle, parent=None):
        super().__init__(parent)
        self._services = services
        self._bridges: dict[str, QObject] = {}
        self._capabilities: dict[str, bool] = {}
        self._action_registry = None

    @property
    def bridges(self) -> dict[str, QObject]:
        return dict(self._bridges)

    @property
    def capabilities(self) -> dict[str, bool]:
        return dict(self._capabilities)

    def get(self, name: str) -> QObject | None:
        return self._bridges.get(name)

    def has(self, name: str) -> bool:
        return name in self._bridges

    def _register_capability(self, bridge_name: str, *required_services: str):
        self._capabilities[bridge_name] = all(self._services.has(s) for s in required_services)

    def create_app_bridge(self):
        from ui_qml_bridge.app_bridge import AppBridge
        if "app" not in self._bridges:
            self._bridges["app"] = AppBridge(
                worker_manager=self._services.worker_manager,
                query_executor=None,
                player_service=self._services.player_service,
                queue_bridge=self._bridges.get("queue"),
                sync_manager=self._services.sync_manager,
                home_audio_controller=self._services.home_audio_controller,
                radio_manager=self._services.radio_manager,
                discovery=None,
                db=self._services.db,
            )
            if hasattr(self._bridges["app"], 'setPhase'):
                self._bridges["app"].setPhase(AppBridge.PHASE_LOADING_SERVICES)
        return self._bridges["app"]

    def create_navigation_bridge(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        if "navigation" not in self._bridges:
            nav = NavigationBridge()
            self._bridges["navigation"] = nav
        return self._bridges["navigation"]

    def create_theme_bridge(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        if "theme" not in self._bridges:
            self._bridges["theme"] = ThemeBridge(
                coordinator=self._services.settings_coordinator,
            )
        return self._bridges["theme"]

    def create_library_bridge(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        if "library" not in self._bridges:
            self._bridges["library"] = LibraryBridge(
                db=self._services.db,
                search_engine=self._services.search_engine,
                playback_ctrl=self._services.player_service,
                query_service=None,
                query_executor=None,
                worker_manager=self._services.worker_manager,
                job_bridge=self._bridges.get("job_bridge"),
                track_action_service=None,
            )
        self._register_capability("library", "db")
        return self._bridges["library"]

    def create_playback_bridge(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        if "playback" not in self._bridges:
            npb = self.create_nowplaying_bridge()
            self._bridges["playback"] = PlaybackBridge(
                player_service=self._services.player_service,
                nowplaying_bridge=npb,
            )
        self._register_capability("playback", "player_service")
        return self._bridges["playback"]

    def create_nowplaying_bridge(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        from ui_qml_bridge.audio_quality_adapter import AudioQualityAdapter
        if "nowplaying" not in self._bridges:
            quality_adapter = AudioQualityAdapter(
                worker_manager=self._services.worker_manager,
            )
            self._bridges["nowplaying"] = NowPlayingBridge(
                player_service=self._services.player_service,
                audio_quality_adapter=quality_adapter,
            )
        self._register_capability("nowplaying", "player_service")
        return self._bridges["nowplaying"]

    def create_mix_bridge(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        if "mix" not in self._bridges:
            self._bridges["mix"] = MixBridge(
                db=self._services.db,
                player_service=self._services.player_service,
                track_action_service=None,
                playlist_bridge=self._bridges.get("playlists"),
                query_service=None,
                query_executor=None,
            )
        self._register_capability("mix", "db")
        return self._bridges["mix"]

    def create_lyrics_bridge(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        if "lyrics" not in self._bridges:
            self._bridges["lyrics"] = LyricsBridge(
                worker_manager=self._services.worker_manager,
                nowplaying_bridge=self.get("nowplaying"),
            )
        self._register_capability("lyrics", "worker_manager")
        return self._bridges["lyrics"]

    def create_connections_bridge(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        if "connections" not in self._bridges:
            self._bridges["connections"] = ConnectionsBridge(
                michi_link_ctrl=self._services.michi_link_controller,
                navigation_bridge=None,
            )
        self._register_capability("connections", "michi_link_controller")
        return self._bridges["connections"]

    def create_home_audio_bridge(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        if "home_audio" not in self._bridges:
            self._bridges["home_audio"] = HomeAudioBridge(
                ha_controller=self._services.home_audio_controller,
                snapcast_ctrl=self._services.snapcast_controller,
            )
        self._register_capability("home_audio", "home_audio_controller")
        return self._bridges["home_audio"]

    def create_devices_bridge(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        if "devices" not in self._bridges:
            self._bridges["devices"] = DevicesBridge(
                sync_manager=self._services.sync_manager,
            )
        self._register_capability("devices", "sync_manager")
        return self._bridges["devices"]

    def create_radio_bridge(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        if "radio" not in self._bridges:
            self._bridges["radio"] = RadioBridge(
                radio_manager=self._services.radio_manager,
                player_service=self._services.player_service,
            )
        self._register_capability("radio", "radio_manager")
        return self._bridges["radio"]

    def create_selection_context_bridge(self):
        from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
        if "selection_context" not in self._bridges:
            self._bridges["selection_context"] = SelectionContextBridge()
        return self._bridges["selection_context"]

    def create_playlists_bridge(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        if "playlists" not in self._bridges:
            sel = self.create_selection_context_bridge()
            self._bridges["playlists"] = PlaylistsBridge(
                db=self._services.db,
                selection_context=sel,
                player_service=self._services.player_service,
                playlist_service=None,
            )
        self._register_capability("playlists", "db")
        return self._bridges["playlists"]

    def create_settings_bridge(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        if "settings" not in self._bridges:
            bridge = SettingsBridgeV2(service=None)
            self._bridges["settings"] = bridge
            self._bridges["settings_v2"] = bridge
        return self._bridges["settings"]

    def create_eq_bridge(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        if "eq" not in self._bridges:
            self._bridges["eq"] = EqBridge(
                player_service=self._services.player_service,
            ) if self._services.player_service else None
        self._register_capability("eq", "player_service")
        return self._bridges.get("eq")

    def create_audio_lab_bridge(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        if "audio_lab" not in self._bridges:
            self._bridges["audio_lab"] = AudioLabBridge(
                db_conn=self._services.db_connection,
                navigation_bridge=None,
                player_service=self._services.player_service,
                worker_manager=self._services.worker_manager,
            )
        self._register_capability("audio_lab", "db_connection")
        return self._bridges["audio_lab"]

    def create_metadata_bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        if "metadata" not in self._bridges:
            ms = self._services.metadata_service
            js = self._services.job_service
            self._bridges["metadata"] = MetadataBridge(
                metadata_service=ms,
                job_service=js,
            )
        return self._bridges["metadata"]

    def create_smart_tagging_bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        if "smart_tagging" not in self._bridges:
            br = SmartTaggingBridge(service=self._services.smart_tagging_service,
                                    worker_manager=self._services.worker_manager,
                                    query_service=None)
            self._bridges["smart_tagging"] = br
        return self._bridges["smart_tagging"]

    def create_disc_lab_bridge(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        if "disc_lab" not in self._bridges:
            self._bridges["disc_lab"] = DiscLabBridge(
                disc_detection_service=self._services.disc_service,
                worker_manager=self._services.worker_manager,
            )
        self._register_capability("disc_lab", "disc_service")
        return self._bridges["disc_lab"]

    def create_library_doctor_bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        if "library_doctor" not in self._bridges:
            self._bridges["library_doctor"] = LibraryDoctorBridge(
                db=self._services.db,
                worker_manager=self._services.worker_manager,
            )
        self._register_capability("library_doctor", "db")
        return self._bridges["library_doctor"]

    def create_michi_ai_bridge(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        if "michi_ai" not in self._bridges:
            ai_controller = None
            try:
                from michi_ai.intelligence.controller import AIController
                ai_controller = AIController()
            except Exception:
                pass
            context_service = None
            try:
                from core.context.context_service import ContextService
                context_service = ContextService(db=self._services.db)
            except Exception:
                pass
            plan_builder = None
            try:
                from michi_ai.planner.plan_builder import PlanBuilder
                plan_builder = PlanBuilder()
            except Exception:
                pass
            tool_registry = None
            try:
                from michi_ai.tools.tool_registry import ToolRegistry
                tool_registry = ToolRegistry()
            except Exception:
                pass
            action_registry = self._action_registry
            nav = self._bridges.get("navigation")
            wm = self._services.worker_manager
            self._bridges["michi_ai"] = MichiAIBridge(
                ai_controller=ai_controller,
                context_service=context_service,
                plan_builder=plan_builder,
                tool_registry=tool_registry,
                action_registry=action_registry,
                navigation_bridge=nav,
                track_action_service=None,
                playlist_service=None,
                global_search_service=None,
                settings_service=None,
                diagnostics_service=None,
                worker_manager=wm,
            )
        return self._bridges["michi_ai"]

    def create_cover_bridge(self):
        if "cover" not in self._bridges:
            pass
        return self._bridges.get("cover")

    def create_notification_bridge(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        if "notification" not in self._bridges:
            ar = self._action_registry
            jb = self._bridges.get("job_bridge")
            self._bridges["notification"] = NotificationBridge(
                action_registry=ar,
                job_bridge=jb,
            )
        return self._bridges["notification"]

    def create_route_registry_bridge(self):
        from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
        if "route_registry" not in self._bridges:
            self._bridges["route_registry"] = RouteRegistryBridge()
        return self._bridges["route_registry"]

    def create_app_state_bridge(self):
        from ui_qml_bridge.app_state_bridge import AppStateBridge
        if "app_state" not in self._bridges:
            self._bridges["app_state"] = AppStateBridge()
        return self._bridges["app_state"]

    def create_diagnostics_bridge(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        if "diagnostics" not in self._bridges:
            self._bridges["diagnostics"] = DiagnosticsBridge(
                player_service=self._services.player_service,
                db=self._services.db,
                radio_manager=self._services.radio_manager,
                sync_manager=self._services.sync_manager,
                worker_manager=self._services.worker_manager,
                query_executor=None,
                library_bridge=self._bridges.get("library"),
            )
        self._register_capability("diagnostics", "db")
        return self._bridges["diagnostics"]

    def get_action_registry(self):
        if self._action_registry is None:
            from ui_qml_bridge.action_registry import ActionRegistry
            self._action_registry = ActionRegistry()
        return self._action_registry

    def create_action_registry_bridge(self):
        registry = self.get_action_registry()
        if "action_registry" not in self._bridges:
            self._bridges["action_registry"] = registry
        return registry

    def bind_action_handlers(self):
        registry = self.get_action_registry()
        from ui_qml_bridge.action_registry_binder import ActionRegistryBinder
        binder = ActionRegistryBinder(registry, self._bridges)
        binder.bind_all()

    def create_command_palette_bridge(self):
        if "command_palette" not in self._bridges:
            from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
            registry = self.get_action_registry()
            self._bridges["command_palette"] = CommandPaletteBridge(
                action_registry=registry,
                navigation_bridge=self._bridges.get("navigation"),
                nowplaying_bridge=self.get("nowplaying"),
            )
        return self._bridges["command_palette"]

    def create_global_search_bridge(self):
        if "global_search" not in self._bridges:
            from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
            self._bridges["global_search"] = GlobalSearchBridge(
                search_service=None,
            )
        return self._bridges["global_search"]

    def create_cover_provider_bridge(self):
        if "cover_provider" not in self._bridges:
            from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
            cover_bridge = self.get("cover")
            self._bridges["cover_provider"] = CoverProviderBridge(cover_bridge=cover_bridge)
        return self._bridges["cover_provider"]

    def create_job_bridge(self):
        if "job_bridge" not in self._bridges:
            from ui_qml_bridge.job_bridge import JobBridge
            self._bridges["job_bridge"] = JobBridge(
                worker_manager=self._services.worker_manager,
                db=self._services.db,
            )
        return self._bridges["job_bridge"]

    def _wire_job_bridge_library(self):
        jb = self._bridges.get("job_bridge")
        lib = self._bridges.get("library")
        if jb and lib and hasattr(jb, 'attach_library_coordinator'):
            jb.attach_library_coordinator(lib)

    def create_desktop_bridge(self):
        if "desktop" not in self._bridges:
            from ui_qml_bridge.desktop_bridge import DesktopBridge
            self._bridges["desktop"] = DesktopBridge()
        return self._bridges["desktop"]

    def create_page_state_store(self):
        if "page_state" not in self._bridges:
            from ui_qml_bridge.page_state_store import PageStateStore
            self._bridges["page_state"] = PageStateStore()
        return self._bridges["page_state"]

    def create_queue_bridge(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        if "queue" not in self._bridges:
            self._bridges["queue"] = QueueBridge(
                player_service=self._services.player_service,
                playlists_bridge=self.get("playlists"),
            )
        return self._bridges["queue"]

    def create_history_bridge(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        if "history" not in self._bridges:
            self._bridges["history"] = HistoryBridge(
                db=self._services.db,
                history_query_service=None,
                query_executor=None,
            )
        return self._bridges["history"]

    def _run_settings_migrations(self):
        try:
            from core.settings_migrations import migrate_all
            from core.settings_manager import SETTINGS
            from core.paths import app_config_dir
            import shutil
            backup_path = Path(app_config_dir()) / "settings_backup_before_migration.ini"
            if SETTINGS and hasattr(SETTINGS, 'fileName'):
                try:
                    src = SETTINGS.fileName()
                    if src and Path(src).is_file():
                        shutil.copy2(src, backup_path)
                        logger.debug("Settings backed up to %s", backup_path)
                except Exception:
                    pass
            migrate_all()
        except Exception as e:
            logger.warning("Settings migrations failed: %s", e)

    def create_home_bridge(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        if "home" not in self._bridges:
            self._bridges["home"] = HomeBridge(
                db=self._services.db,
                player_service=self._services.player_service,
                library_bridge=self._bridges.get("library"),
                library_sources_service=None,
                job_bridge=self._bridges.get("job_bridge"),
            )
        self._register_capability("home", "db")
        return self._bridges["home"]

    def create_output_profiles_bridge(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        if "output_profiles" not in self._bridges:
            self._bridges["output_profiles"] = OutputProfilesBridge(
                player_service=self._services.player_service,
            )
        return self._bridges["output_profiles"]

    def create_capability_bridge(self):
        from ui_qml_bridge.capability_bridge import CapabilityBridge
        if "capability" not in self._bridges:
            cb = CapabilityBridge(factory=self)
            cb.refresh()
            self._bridges["capability"] = cb
        return self._bridges["capability"]

    def create_accessibility_bridge(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        if "accessibility" not in self._bridges:
            self._bridges["accessibility"] = AccessibilityBridge()
        return self._bridges["accessibility"]

    def create_runtime_quality_bridge(self):
        from ui_qml_bridge.runtime_quality_bridge import RuntimeQualityBridge
        if "runtime_quality" not in self._bridges:
            self._bridges["runtime_quality"] = RuntimeQualityBridge()
        return self._bridges["runtime_quality"]

    def create_physical_audio_bridge(self):
        from ui_qml_bridge.physical_audio_bridge import PhysicalAudioBridge
        if "physical_audio" not in self._bridges:
            self._bridges["physical_audio"] = PhysicalAudioBridge()
        return self._bridges["physical_audio"]

    def create_library_sources_bridge(self):
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        if "library_sources" not in self._bridges:
            self._bridges["library_sources"] = LibrarySourcesBridge(
                service=None, job_bridge=self._bridges.get("job_bridge"))
        return self._bridges["library_sources"]

    def create_all(self) -> dict[str, QObject]:
        """Phase 0: settings migrations before any service."""
        self._run_settings_migrations()

        """Phase B: fundamental bridges (no domain dependencies)."""
        self.create_navigation_bridge()
        self.create_app_bridge()
        self.create_theme_bridge()
        self.create_notification_bridge()
        self.create_accessibility_bridge()
        self.create_app_state_bridge()
        self.create_route_registry_bridge()
        self.create_action_registry_bridge()
        self.create_capability_bridge()
        self.create_playlists_bridge()
        self.create_selection_context_bridge()
        self.create_job_bridge()

        """Phase C: domain bridges (may depend on Phase B)."""
        self.create_library_bridge()
        self._wire_job_bridge_library()
        self.create_playback_bridge()
        self.create_nowplaying_bridge()
        self.create_queue_bridge()
        self.create_history_bridge()
        self.create_mix_bridge()
        self.create_lyrics_bridge()
        self.create_global_search_bridge()
        self.create_settings_bridge()
        self.create_output_profiles_bridge()
        self.create_eq_bridge()
        self.create_connections_bridge()
        self.create_home_audio_bridge()
        self.create_devices_bridge()
        self.create_radio_bridge()
        self.create_library_sources_bridge()
        self.create_home_bridge()

        """Phase D: advanced tools (may depend on Phase C)."""
        self.create_audio_lab_bridge()
        self.create_metadata_bridge()
        self.create_smart_tagging_bridge()
        self.create_disc_lab_bridge()
        self.create_library_doctor_bridge()
        self.create_michi_ai_bridge()
        self.create_diagnostics_bridge()
        self.create_runtime_quality_bridge()
        self.create_physical_audio_bridge()
        self.create_command_palette_bridge()
        self.create_cover_provider_bridge()
        self.create_desktop_bridge()
        self.create_page_state_store()

        """Phase E: wiring assertions."""
        self._assert_wiring()
        self.bind_action_handlers()
        return self._bridges

    def _assert_wiring(self):
        """Verify critical dependency chains are complete via public APIs."""
        sv = self._bridges.get("settings")
        sv2 = self._bridges.get("settings_v2")
        if sv and sv2:
            assert sv is sv2, "settings and settings_v2 must be the same object"
        services = self._services
        app = self._bridges.get("app")
        queue = self._bridges.get("queue")
        audio_lab = self._bridges.get("audio_lab")
        devices = self._bridges.get("devices")
        notifications = self._bridges.get("notification")
        history = self._bridges.get("history")
        global_search = self._bridges.get("global_search")
        michi_ai = self._bridges.get("michi_ai")
        if app and hasattr(app, 'queue_service'):
            assert app.queue_service is services.queue_service
        if queue and hasattr(queue, 'queue_service'):
            assert queue.queue_service is services.queue_service
        if audio_lab and hasattr(audio_lab, 'audio_lab_service'):
            assert audio_lab.audio_lab_service is services.audio_lab_service
        if devices and hasattr(devices, 'device_sync_service'):
            assert devices.device_sync_service is services.device_sync_service
        if notifications and hasattr(notifications, 'notification_service'):
            assert notifications.notification_service is services.notification_service
        if notifications and hasattr(notifications, 'action_registry'):
            assert notifications.action_registry is services.action_registry
        if history and hasattr(history, 'history_query_service'):
            assert history.history_query_service is services.history_query_service
        if global_search and hasattr(global_search, 'search_service'):
            assert global_search.search_service is services.global_search_service
        if michi_ai and hasattr(michi_ai, 'diagnostics_service'):
            assert michi_ai.diagnostics_service is services.diagnostics_service

    def __repr__(self) -> str:
        return f"BridgeFactory(bridges={len(self._bridges)}, capabilities={self._capabilities})"


def create_all_bridges(container) -> dict[str, QObject]:
    """Create all bridges from a ServiceContainer container.

    Adapter function used by ApplicationBootstrap._build_bridges().
    Extracts services from the container into a ServiceBundle,
    then delegates to BridgeFactory.create_all().
    """
    from ui_qml_bridge.service_bundle import ServiceBundle

    services = ServiceBundle(
        db=container.get("connection_factory"),
        db_connection=None,
        player_service=container.get("playback_service"),
        worker_manager=container.get("worker_manager"),
        search_engine=container.get("global_search_service"),
        radio_manager=container.get("radio_manager"),
        sync_manager=container.get("device_sync_service"),
        michi_link_controller=container.get("michi_link_service"),
        home_audio_controller=container.get("home_audio_service"),
        snapcast_controller=container.get("snapcast_service"),
        disc_service=None,
        metadata_service=container.get("metadata_service"),
        smart_tagging_service=container.get("smart_tagging_service"),
    )
    services.job_service = container.get("job_service")

    factory = BridgeFactory(services)
    return factory.create_all()
