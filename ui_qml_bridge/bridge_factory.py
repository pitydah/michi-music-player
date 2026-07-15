"""BridgeFactory  creates bridges from ServiceContainer, no caching.

Does not open databases, construct backends, or start services.
Does not cache or create core services internally.
API: BridgeFactory(container).create_all() -> BridgeRegistry.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

if TYPE_CHECKING:
    from core.service_container import ServiceContainer

logger = logging.getLogger("michi.bridge_factory")

# Deterministic creation order from specification
INFRASTRUCTURE = [
    "page_state", "route_registry", "navigation", "action_registry",
    "query_executor", "job_bridge", "confirmation", "theme", "accessibility",
    "app_state",
]

DOMAIN = [
    "library_sources", "library", "playback", "nowplaying", "queue",
    "playlists", "history", "global_search", "mix", "lyrics",
    "settings", "output_profiles", "eq", "connections",
    "home_audio", "devices", "radio", "audio_lab", "metadata",
    "smart_tagging", "disc_lab", "library_doctor", "diagnostics", "michi_ai",
]

AGGREGATORS = [
    "notification", "command_palette", "home", "capability",
    "app", "desktop", "runtime_quality", "physical_audio",
]


class BridgeFactory(QObject):
    """Creates each bridge with injected dependencies from ServiceContainer."""

    def __init__(self, container: ServiceContainer, parent=None):
        super().__init__(parent)
        self._container = container
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
        required_keys = ["playback_service", "worker_manager"]
        for key in required_keys:
            if not self._container.contains(key):
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
                coordinator=self._container.settings_coordinator,
            )

    def create_library_bridge(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        if "library" not in self._bridges:
            self._bridges["library"] = LibraryBridge(
                db=self._container.database,
                search_engine=self._container.global_search_service,
                playback_ctrl=self._container.playback_service,
                query_service=None,
                query_executor=self._bridges.get("query_executor"),
                worker_manager=self._container.worker_manager,
                job_bridge=self._bridges.get("job_bridge"),
                track_action_service=self._container.track_action_service,
            )

    def create_playback_bridge(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        if "playback" not in self._bridges:
            self.create_nowplaying_bridge()
            npb = self._bridges.get("nowplaying")
            self._bridges["playback"] = PlaybackBridge(
                player_service=self._container.playback_service,
                nowplaying_bridge=npb,
            )

    def create_nowplaying_bridge(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        from ui_qml_bridge.audio_quality_adapter import AudioQualityAdapter
        if "nowplaying" not in self._bridges:
            quality_adapter = AudioQualityAdapter(
                worker_manager=self._container.worker_manager,
            )
            self._bridges["nowplaying"] = NowPlayingBridge(
                player_service=self._container.playback_service,
                audio_quality_adapter=quality_adapter,
            )

    def create_mix_bridge(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        if "mix" not in self._bridges:
            self._bridges["mix"] = MixBridge(
                mix_service=self._container.mix_query_service,
                job_service=self._container.job_service,
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                playlist_service=self._container.playlist_service,
                playback_service=self._container.playback_service,
                queue_service=self._container.queue_service,
            )

    def create_lyrics_bridge(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        if "lyrics" not in self._bridges:
            self._bridges["lyrics"] = LyricsBridge(
                worker_manager=self._container.worker_manager,
                nowplaying_bridge=self.get("nowplaying"),
            )

    def create_connections_bridge(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        if "connections" not in self._bridges:
            self._bridges["connections"] = ConnectionsBridge(
                michi_link_ctrl=self._container.connection_service,
                navigation_bridge=self._bridges.get("navigation"),
            )

    def create_home_audio_bridge(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        if "home_audio" not in self._bridges:
            self._bridges["home_audio"] = HomeAudioBridge(
                ha_controller=self._container.home_audio_service,
                snapcast_ctrl=self._container.home_audio_service,
            )

    def create_devices_bridge(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        if "devices" not in self._bridges:
            self._bridges["devices"] = DevicesBridge(
                device_sync_service=self._container.device_sync_service,
                job_service=self._container.job_service,
                action_registry=self._bridges.get("action_registry"),
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
                page_state_store=self._bridges.get("page_state"),
                accessibility_bridge=self._bridges.get("accessibility"),
            )
        return self._bridges["devices"]

    def create_radio_bridge(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        if "radio" not in self._bridges:
            self._bridges["radio"] = RadioBridge(
                radio_manager=self._container.radio_service,
                player_service=self._container.playback_service,
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
                db=self._container.database,
                selection_context=sel,
                player_service=self._container.playback_service,
                playlist_service=self._container.playlist_service,
                action_registry=self._bridges.get("action_registry"),
                confirmation_bridge=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_settings_bridge(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        if "settings" not in self._bridges:
            bridge = SettingsBridgeV2(service=self._container.settings_service)
            self._bridges["settings"] = bridge
            self._bridges["settings_v2"] = bridge

    def create_eq_bridge(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        if "eq" not in self._bridges:
            self._bridges["eq"] = EqBridge(
                player_service=self._container.playback_service,
            ) if self._container.playback_service else None

    def create_audio_lab_bridge(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        if "audio_lab" not in self._bridges:
            self._bridges["audio_lab"] = AudioLabBridge(
                audio_lab_service=self._container.audio_lab_service,
                job_service=self._container.job_service,
                process_controller=self._container.process_controller,
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
            )
        return self._bridges["audio_lab"]

    def create_metadata_bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        if "metadata" not in self._bridges:
            self._bridges["metadata"] = MetadataBridge(
                metadata_service=self._container.metadata_service,
                job_service=self._container.job_service,
            )

    def create_smart_tagging_bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        if "smart_tagging" not in self._bridges:
            self._bridges["smart_tagging"] = SmartTaggingBridge(
                service=self._container.smart_tagging_service,
                worker_manager=self._container.worker_manager,
                query_service=None,
            )

    def create_disc_lab_bridge(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        if "disc_lab" not in self._bridges:
            self._bridges["disc_lab"] = DiscLabBridge(
                disc_detection_service=None,
                worker_manager=self._container.worker_manager,
            )

    def create_library_doctor_bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        if "library_doctor" not in self._bridges:
            self._bridges["library_doctor"] = LibraryDoctorBridge(
                db=self._container.database,
                worker_manager=self._container.worker_manager,
            )

    def create_michi_ai_bridge(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        if "michi_ai" not in self._bridges:
            self._bridges["michi_ai"] = MichiAIBridge(
                device_sync_service=self._container.device_sync_service,
                job_service=self._container.job_service,
                action_registry=self._bridges.get("action_registry"),
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
                page_state_store=self._bridges.get("page_state"),
                accessibility_bridge=self._bridges.get("accessibility"),
            )

    def create_cover_bridge(self):
        self._bridges.setdefault("cover", None)

    def create_notification_bridge(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        if "notification" not in self._bridges:
            ar = self._bridges.get("action_registry")
            jb = self._bridges.get("job_bridge")
            ns = self._container.notification_service
            nav = self._bridges.get("navigation")
            ds = self._container.diagnostics_service
            self._bridges["notification"] = NotificationBridge(
                action_registry=ar,
                job_bridge=jb,
                notification_service=ns,
                navigation_bridge=nav,
                diagnostics_service=ds,
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
                player_service=self._container.playback_service,
                db=self._container.database,
                radio_manager=self._container.radio_service,
                sync_manager=self._container.device_sync_service,
                worker_manager=self._container.worker_manager,
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
                capability_bridge=self._bridges.get("capability"),
                confirmation_bridge=self._bridges.get("confirmation"),
                page_state_store=self._bridges.get("page_state"),
            )

    def create_global_search_bridge(self):
        if "global_search" not in self._bridges:
            from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
            self._bridges["global_search"] = GlobalSearchBridge(
                search_service=self._container.global_search_service,
                query_executor=self._bridges.get("query_executor"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
            )

    def create_cover_provider_bridge(self):
        if "cover_provider" not in self._bridges:
            from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
            cover_bridge = self.get("cover")
            self._bridges["cover_provider"] = CoverProviderBridge(cover_bridge=cover_bridge)

    def create_query_executor(self):
        if "query_executor" not in self._bridges:
            from ui_qml_bridge.query_executor import QueryExecutor
            self._bridges["query_executor"] = QueryExecutor(
                worker_manager=self._container.worker_manager,
                owns_worker_manager=False,
            )

    def create_job_bridge(self):
        if "job_bridge" not in self._bridges:
            from ui_qml_bridge.job_bridge import JobBridge
            self._bridges["job_bridge"] = JobBridge(
                worker_manager=self._container.worker_manager,
                db=self._container.database,
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
                player_service=self._container.playback_service,
                playlists_bridge=self.get("playlists"),
                queue_service=self._container.queue_service,
            )

    def create_history_bridge(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        if "history" not in self._bridges:
            self._bridges["history"] = HistoryBridge(
                db=self._container.database,
                history_query_service=self._container.history_query_service,
                query_executor=self._bridges.get("query_executor"),
                playback_service=self._container.playback_service,
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_home_bridge(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        if "home" not in self._bridges:
            self._bridges["home"] = HomeBridge(
                db=self._container.database,
                player_service=self._container.playback_service,
                library_bridge=self._bridges.get("library"),
                library_sources_service=self._container.library_sources_service,
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_output_profiles_bridge(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        if "output_profiles" not in self._bridges:
            self._bridges["output_profiles"] = OutputProfilesBridge(
                player_service=self._container.playback_service,
            )

    def create_capability_bridge(self):
        from ui_qml_bridge.capability_bridge import CapabilityBridge
        if "capability" not in self._bridges:
            cb = CapabilityBridge(factory=self)
            self._bridges["capability"] = cb

    def create_accessibility_bridge(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        if "accessibility" not in self._bridges:
            self._bridges["accessibility"] = AccessibilityBridge(
                service=self._container.settings_coordinator,
                settings_service=self._container.settings_coordinator,
                playback_service=self._container.playback_service,
            )

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
                service=self._container.library_sources_service,
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_action_registry_bridge(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        if "action_registry" not in self._bridges:
            self._bridges["action_registry"] = ActionRegistry()

    def create_confirmation_bridge(self):
        from ui_qml_bridge.confirmation_bridge import ConfirmationBridge
        if "confirmation" not in self._bridges:
            self._bridges["confirmation"] = ConfirmationBridge(
                confirmation_service=self._container.confirmation_service,
                action_registry=self._bridges.get("action_registry"),
            )

    def create_app_bridge(self):
        from ui_qml_bridge.app_bridge import AppBridge
        if "app" not in self._bridges:
            self._bridges["app"] = AppBridge(
                worker_manager=self._container.worker_manager,
                query_executor=self._bridges.get("query_executor"),
                player_service=self._container.playback_service,
                queue_bridge=self._bridges.get("queue"),
                sync_manager=self._container.device_sync_service,
                home_audio_controller=self._container.home_audio_service,
                radio_manager=self._container.radio_service,
                discovery=None,
                db=self._container.database,
            )

    def _create_infrastructure(self):
        for name in INFRASTRUCTURE:
            method_name = {
                "page_state": "create_page_state_store",
                "route_registry": "create_route_registry_bridge",
                "navigation": "create_navigation_bridge",
                "action_registry": "create_action_registry_bridge",
                "query_executor": "create_query_executor",
                "job_bridge": "create_job_bridge",
                "confirmation": "create_confirmation_bridge",
                "theme": "create_theme_bridge",
                "accessibility": "create_accessibility_bridge",
                "app_state": "create_app_state_bridge",
            }[name]
            getattr(self, method_name)()

    def _create_domain(self):
        for name in DOMAIN:
            method_name = {
                "library_sources": "create_library_sources_bridge",
                "library": "create_library_bridge",
                "playback": "create_playback_bridge",
                "nowplaying": "create_nowplaying_bridge",
                "queue": "create_queue_bridge",
                "playlists": "create_playlists_bridge",
                "history": "create_history_bridge",
                "global_search": "create_global_search_bridge",
                "mix": "create_mix_bridge",
                "lyrics": "create_lyrics_bridge",
                "settings": "create_settings_bridge",
                "output_profiles": "create_output_profiles_bridge",
                "eq": "create_eq_bridge",
                "connections": "create_connections_bridge",
                "home_audio": "create_home_audio_bridge",
                "devices": "create_devices_bridge",
                "radio": "create_radio_bridge",
                "audio_lab": "create_audio_lab_bridge",
                "metadata": "create_metadata_bridge",
                "smart_tagging": "create_smart_tagging_bridge",
                "disc_lab": "create_disc_lab_bridge",
                "library_doctor": "create_library_doctor_bridge",
                "diagnostics": "create_diagnostics_bridge",
                "michi_ai": "create_michi_ai_bridge",
            }[name]
            getattr(self, method_name)()

    def _create_aggregators(self):
        for name in AGGREGATORS:
            method_name = {
                "notification": "create_notification_bridge",
                "command_palette": "create_command_palette_bridge",
                "home": "create_home_bridge",
                "capability": "create_capability_bridge",
                "app": "create_app_bridge",
                "desktop": "create_desktop_bridge",
                "runtime_quality": "create_runtime_quality_bridge",
                "physical_audio": "create_physical_audio_bridge",
            }[name]
            getattr(self, method_name)()

    def create_all(self) -> dict[str, QObject]:
        missing = self.validate_required_dependencies()
        if missing:
            logger.warning("BridgeFactory: missing required dependencies: %s", missing)

        self._create_infrastructure()
        self._create_domain()
        self._create_aggregators()

        self.create_selection_context_bridge()
        self.create_cover_bridge()
        self.create_cover_provider_bridge()

        self.bind_action_handlers()
        self._refresh_capability()
        self._audit_identities()
        self._audit_required_dependencies()
        return self._bridges

    def _refresh_capability(self):
        cap = self._bridges.get("capability")
        if cap and hasattr(cap, "refresh"):
            cap.refresh()

    def _audit_identities(self):
        pass

    def _audit_required_dependencies(self):
        pass

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
    factory = BridgeFactory(container)
    return factory.create_all()
