"""BridgeFactory — creates bridges from ServiceContainer, no caching.

Does not open databases, construct backends, or start services.
Does not cache or create core services internally.
API: BridgeFactory(container).create_all() -> BridgeRegistry.
"""
from __future__ import annotations

import logging
from PySide6.QtCore import QObject

from ui_qml_bridge.service_bundle import ServiceBundle

logger = logging.getLogger("michi.bridge_factory")


class BridgeFactory(QObject):
    """Creates each bridge with injected dependencies from ServiceContainer."""

    def __init__(self, services: ServiceBundle, parent=None):
        super().__init__(parent)
        self._services = services
        self._bridges: dict[str, QObject] = {}
        self._capabilities: dict[str, bool] = {}

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

    def validate_required_dependencies(self) -> list[str]:
        missing = []
        required_keys = ["player_service", "db", "worker_manager"]
        for key in required_keys:
            if not self._services.has(key):
                missing.append(key)
        return missing

    def create_navigation_bridge(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        if "navigation" not in self._bridges:
            self._bridges["navigation"] = NavigationBridge()

    def create_theme_bridge(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        if "theme" not in self._bridges:
            self._bridges["theme"] = ThemeBridge(
                coordinator=self._services.settings_coordinator,
            )

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

    def create_playback_bridge(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        if "playback" not in self._bridges:
            self.create_nowplaying_bridge()
            npb = self._bridges.get("nowplaying")
            self._bridges["playback"] = PlaybackBridge(
                player_service=self._services.player_service,
                nowplaying_bridge=npb,
            )

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

    def create_lyrics_bridge(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        if "lyrics" not in self._bridges:
            self._bridges["lyrics"] = LyricsBridge(
                worker_manager=self._services.worker_manager,
                nowplaying_bridge=self.get("nowplaying"),
            )

    def create_connections_bridge(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        if "connections" not in self._bridges:
            self._bridges["connections"] = ConnectionsBridge(
                michi_link_ctrl=self._services.michi_link_controller,
                navigation_bridge=None,
            )

    def create_home_audio_bridge(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        if "home_audio" not in self._bridges:
            self._bridges["home_audio"] = HomeAudioBridge(
                ha_controller=self._services.home_audio_controller,
                snapcast_ctrl=self._services.snapcast_controller,
            )

    def create_devices_bridge(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        if "devices" not in self._bridges:
            self._bridges["devices"] = DevicesBridge(
                sync_manager=self._services.sync_manager,
            )

    def create_radio_bridge(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        if "radio" not in self._bridges:
            self._bridges["radio"] = RadioBridge(
                radio_manager=self._services.radio_manager,
                player_service=self._services.player_service,
            )

    def create_selection_context_bridge(self):
        from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
        if "selection_context" not in self._bridges:
            self._bridges["selection_context"] = SelectionContextBridge()

    def create_playlists_bridge(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        if "playlists" not in self._bridges:
            self.create_selection_context_bridge()
            sel = self._bridges.get("selection_context")
            self._bridges["playlists"] = PlaylistsBridge(
                db=self._services.db,
                selection_context=sel,
                player_service=self._services.player_service,
                playlist_service=None,
            )

    def create_settings_bridge(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        if "settings" not in self._bridges:
            bridge = SettingsBridgeV2(service=None)
            self._bridges["settings"] = bridge
            self._bridges["settings_v2"] = bridge

    def create_eq_bridge(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        if "eq" not in self._bridges:
            self._bridges["eq"] = EqBridge(
                player_service=self._services.player_service,
            ) if self._services.player_service else None

    def create_audio_lab_bridge(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        if "audio_lab" not in self._bridges:
            self._bridges["audio_lab"] = AudioLabBridge(
                db_conn=self._services.db_connection,
                navigation_bridge=None,
                player_service=self._services.player_service,
                worker_manager=self._services.worker_manager,
            )

    def create_metadata_bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        if "metadata" not in self._bridges:
            self._bridges["metadata"] = MetadataBridge(
                metadata_service=self._services.metadata_service,
                job_service=self._services.job_service,
            )

    def create_smart_tagging_bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        if "smart_tagging" not in self._bridges:
            self._bridges["smart_tagging"] = SmartTaggingBridge(
                service=self._services.smart_tagging_service,
                worker_manager=self._services.worker_manager,
                query_service=None,
            )

    def create_disc_lab_bridge(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        if "disc_lab" not in self._bridges:
            self._bridges["disc_lab"] = DiscLabBridge(
                disc_detection_service=self._services.disc_service,
                worker_manager=self._services.worker_manager,
            )

    def create_library_doctor_bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        if "library_doctor" not in self._bridges:
            self._bridges["library_doctor"] = LibraryDoctorBridge(
                db=self._services.db,
                worker_manager=self._services.worker_manager,
            )

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
            action_registry = None
            try:
                from ui_qml_bridge.action_registry import ActionRegistry
                action_registry = ActionRegistry()
            except Exception:
                pass
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

    def create_cover_bridge(self):
        self._bridges.setdefault("cover", None)

    def create_notification_bridge(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        if "notification" not in self._bridges:
            ar = None
            try:
                from ui_qml_bridge.action_registry import ActionRegistry
                ar = ActionRegistry()
            except Exception:
                pass
            jb = self._bridges.get("job_bridge")
            self._bridges["notification"] = NotificationBridge(
                action_registry=ar,
                job_bridge=jb,
            )

    def create_route_registry_bridge(self):
        from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
        if "route_registry" not in self._bridges:
            self._bridges["route_registry"] = RouteRegistryBridge()

    def create_app_state_bridge(self):
        from ui_qml_bridge.app_state_bridge import AppStateBridge
        if "app_state" not in self._bridges:
            self._bridges["app_state"] = AppStateBridge()

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

    def create_command_palette_bridge(self):
        if "command_palette" not in self._bridges:
            from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
            self._bridges["command_palette"] = CommandPaletteBridge(
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                nowplaying_bridge=self.get("nowplaying"),
            )

    def create_global_search_bridge(self):
        if "global_search" not in self._bridges:
            from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
            self._bridges["global_search"] = GlobalSearchBridge(
                search_service=None,
            )

    def create_cover_provider_bridge(self):
        if "cover_provider" not in self._bridges:
            from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
            cover_bridge = self.get("cover")
            self._bridges["cover_provider"] = CoverProviderBridge(cover_bridge=cover_bridge)

    def create_job_bridge(self):
        if "job_bridge" not in self._bridges:
            from ui_qml_bridge.job_bridge import JobBridge
            self._bridges["job_bridge"] = JobBridge(
                worker_manager=self._services.worker_manager,
                db=self._services.db,
            )

    def create_desktop_bridge(self):
        if "desktop" not in self._bridges:
            from ui_qml_bridge.desktop_bridge import DesktopBridge
            self._bridges["desktop"] = DesktopBridge()

    def create_page_state_store(self):
        if "page_state" not in self._bridges:
            from ui_qml_bridge.page_state_store import PageStateStore
            self._bridges["page_state"] = PageStateStore()

    def create_queue_bridge(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        if "queue" not in self._bridges:
            self._bridges["queue"] = QueueBridge(
                player_service=self._services.player_service,
                playlists_bridge=self.get("playlists"),
            )

    def create_history_bridge(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        if "history" not in self._bridges:
            self._bridges["history"] = HistoryBridge(
                db=self._services.db,
                history_query_service=None,
                query_executor=None,
            )

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

    def create_output_profiles_bridge(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        if "output_profiles" not in self._bridges:
            self._bridges["output_profiles"] = OutputProfilesBridge(
                player_service=self._services.player_service,
            )

    def create_capability_bridge(self):
        from ui_qml_bridge.capability_bridge import CapabilityBridge
        if "capability" not in self._bridges:
            cb = CapabilityBridge(factory=self)
            cb.refresh()
            self._bridges["capability"] = cb

    def create_accessibility_bridge(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        if "accessibility" not in self._bridges:
            self._bridges["accessibility"] = AccessibilityBridge()

    def create_runtime_quality_bridge(self):
        from ui_qml_bridge.runtime_quality_bridge import RuntimeQualityBridge
        if "runtime_quality" not in self._bridges:
            self._bridges["runtime_quality"] = RuntimeQualityBridge()

    def create_physical_audio_bridge(self):
        from ui_qml_bridge.physical_audio_bridge import PhysicalAudioBridge
        if "physical_audio" not in self._bridges:
            self._bridges["physical_audio"] = PhysicalAudioBridge()

    def create_library_sources_bridge(self):
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        if "library_sources" not in self._bridges:
            self._bridges["library_sources"] = LibrarySourcesBridge(
                service=None, job_bridge=self._bridges.get("job_bridge"))

    def create_action_registry_bridge(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        if "action_registry" not in self._bridges:
            self._bridges["action_registry"] = ActionRegistry()

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

    def create_all(self) -> dict[str, QObject]:
        missing = self.validate_required_dependencies()
        if missing:
            logger.warning("BridgeFactory: missing required dependencies: %s", missing)

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
        self.create_library_bridge()
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

        self.bind_action_handlers()
        return self._bridges

    def bind_action_handlers(self):
        registry = self._bridges.get("action_registry")
        if not registry:
            return
        from ui_qml_bridge.action_registry_binder import ActionRegistryBinder
        binder = ActionRegistryBinder(registry, self._bridges)
        binder.bind_all()

    def __repr__(self) -> str:
        return f"BridgeFactory(bridges={len(self._bridges)})"


def create_all_bridges(container) -> dict[str, QObject]:
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
