"""BridgeFactory creates bridges from ServiceContainer, no caching.

Does not open databases, construct backends, or start services.
Does not cache or create core services internally.
API: BridgeFactory(container).create_all() -> BridgeRegistry.
"""
from __future__ import annotations

import logging
from PySide6.QtCore import QObject

from core.service_container import ServiceContainer

logger = logging.getLogger("michi.bridge_factory")

INFRASTRUCTURE = [
    "page_state", "route_registry", "navigation", "action_registry",
    "query_executor", "job_bridge", "confirmation", "theme", "accessibility",
    "notification", "capability", "app_state",
]

DOMAIN = [
    "library_sources", "library", "playback", "nowplaying", "queue",
    "playlists", "history", "global_search", "mix", "lyrics",
    "settings", "output_profiles", "eq", "connections",
    "home_audio", "devices", "radio", "audio_lab", "metadata",
    "smart_tagging", "disc_lab", "library_doctor", "diagnostics", "michi_ai",
]

AGGREGATORS = [
    "command_palette", "home",
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

    def _get(self, name: str):
        return self._container.get(name)

    def create_page_state_store(self):
        if "page_state" not in self._bridges:
            from ui_qml_bridge.page_state_store import PageStateStore
            self._bridges["page_state"] = PageStateStore()

    def create_route_registry_bridge(self):
        if "route_registry" not in self._bridges:
            from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
            self._bridges["route_registry"] = RouteRegistryBridge()

    def create_navigation_bridge(self):
        if "navigation" not in self._bridges:
            from ui_qml_bridge.navigation_bridge import NavigationBridge
            self._bridges["navigation"] = NavigationBridge()

    def create_job_bridge(self):
        if "job_bridge" not in self._bridges:
            from ui_qml_bridge.job_bridge import JobBridge
            self._bridges["job_bridge"] = JobBridge(
                worker_manager=self._get("worker_manager"),
                db=self._get("database"),
            )

    def create_confirmation_bridge(self):
        if "confirmation" not in self._bridges:
            from ui_qml_bridge.confirmation_bridge import ConfirmationBridge
            self._bridges["confirmation"] = ConfirmationBridge(
                confirmation_service=self._get("confirmation_service"),
                action_registry=self._bridges.get("action_registry"),
            )

    def create_accessibility_bridge(self):
        if "accessibility" not in self._bridges:
            from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
            self._bridges["accessibility"] = AccessibilityBridge(
                service=self._get("settings_coordinator"),
                settings_service=self._get("settings_coordinator"),
                playback_service=self._get("playback_service"),
            )

    def create_theme_bridge(self):
        if "theme" not in self._bridges:
            from ui_qml_bridge.theme_bridge import ThemeBridge
            self._bridges["theme"] = ThemeBridge(
                coordinator=self._get("settings_coordinator"),
            )

    def create_capability_bridge(self):
        if "capability" not in self._bridges:
            from ui_qml_bridge.capability_bridge import CapabilityBridge
            cb = CapabilityBridge(factory=self)
            self._bridges["capability"] = cb

    def create_library_bridge(self):
        if "library" not in self._bridges:
            from ui_qml_bridge.library_bridge import LibraryBridge
            self._bridges["library"] = LibraryBridge(
                db=self._get("database"),
                search_engine=self._get("global_search_service"),
                playback_ctrl=self._get("playback_service"),
                query_service=self._get("library_query_service"),
                query_executor=self._get("query_executor"),
                worker_manager=self._get("worker_manager"),
                job_bridge=self._bridges.get("job_bridge"),
                track_action_service=self._get("track_action_service"),
                library_service=self._get("library_data_service"),
                songs_service=self._get("songs_service"),
                track_service=self._get("track_service"),
                genres_service=self._get("genres_service"),
            )

    def create_library_sources_bridge(self):
        if "library_sources" not in self._bridges:
            from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
            self._bridges["library_sources"] = LibrarySourcesBridge(
                service=self._get("library_sources_service"),
                job_bridge=self._bridges.get("job_bridge"),
                folder_service=self._get("folder_service"),
            )

    def create_nowplaying_bridge(self):
        if "nowplaying" not in self._bridges:
            from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
            from ui_qml_bridge.audio_quality_adapter import AudioQualityAdapter
            quality_adapter = AudioQualityAdapter(
                worker_manager=self._get("worker_manager"),
            )
            self._bridges["nowplaying"] = NowPlayingBridge(
                player_service=self._get("playback_service"),
                audio_quality_adapter=quality_adapter,
            )

    def create_playback_bridge(self):
        if "playback" not in self._bridges:
            self.create_nowplaying_bridge()
            npb = self._bridges.get("nowplaying")
            from ui_qml_bridge.playback_bridge import PlaybackBridge
            self._bridges["playback"] = PlaybackBridge(
                player_service=self._get("playback_service"),
                nowplaying_bridge=npb,
            )

    def create_queue_bridge(self):
        if "queue" not in self._bridges:
            from ui_qml_bridge.queue_bridge import QueueBridge
            self._bridges["queue"] = QueueBridge(
                player_service=self._get("playback_service"),
                playlists_bridge=self.get("playlists"),
                queue_service=self._get("queue_service"),
            )

    def create_playlists_bridge(self):
        if "playlists" not in self._bridges:
            from ui_qml_bridge.playlists_bridge import PlaylistsBridge
            from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
            sel = SelectionContextBridge()
            self._bridges["selection_context"] = sel
            self._bridges["playlists"] = PlaylistsBridge(
                db=self._get("database"),
                selection_context=sel,
                player_service=self._get("playback_service"),
                playlist_service=self._get("playlist_service"),
                action_registry=self._bridges.get("action_registry"),
                confirmation_bridge=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_history_bridge(self):
        if "history" not in self._bridges:
            from ui_qml_bridge.history_bridge import HistoryBridge
            self._bridges["history"] = HistoryBridge(
                db=self._get("database"),
                history_query_service=self._get("history_query_service"),
                query_executor=self._get("query_executor"),
                playback_service=self._get("playback_service"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_search_bridge(self):
        if "global_search" not in self._bridges:
            from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
            self._bridges["global_search"] = GlobalSearchBridge(
                search_service=self._get("global_search_service"),
                query_executor=self._get("query_executor"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                notification_bridge=self._bridges.get("notification"),
            )

    def create_mix_bridge(self):
        if "mix" not in self._bridges:
            from ui_qml_bridge.mix_bridge import MixBridge
            self._bridges["mix"] = MixBridge(
                mix_service=self._get("mix_query_service"),
                job_service=self._get("job_service"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=self._bridges.get("navigation"),
                page_state_store=self._bridges.get("page_state"),
                capability_bridge=self._bridges.get("capability"),
                accessibility_bridge=self._bridges.get("accessibility"),
                playlist_service=self._get("playlist_service"),
                playback_service=self._get("playback_service"),
                queue_service=self._get("queue_service"),
                query_executor=self._get("query_executor"),
            )

    def create_lyrics_bridge(self):
        if "lyrics" not in self._bridges:
            from ui_qml_bridge.lyrics_bridge import LyricsBridge
            self._bridges["lyrics"] = LyricsBridge(
                worker_manager=self._get("worker_manager"),
                nowplaying_bridge=self.get("nowplaying"),
            )

    def create_settings_bridge(self):
        if "settings" not in self._bridges:
            from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
            bridge = SettingsBridgeV2(service=self._get("settings_service"))
            self._bridges["settings"] = bridge
            self._bridges["settings_v2"] = bridge

    def create_output_profiles_bridge(self):
        if "output_profiles" not in self._bridges:
            from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
            self._bridges["output_profiles"] = OutputProfilesBridge(
                player_service=self._get("playback_service"),
            )

    def create_eq_bridge(self):
        if "eq" not in self._bridges:
            from ui_qml_bridge.eq_bridge import EqBridge
            self._bridges["eq"] = EqBridge(
                player_service=self._get("playback_service"),
            )

    def create_connections_bridge(self):
        if "connections" not in self._bridges:
            nav = self._bridges.get("navigation")
            if nav is None:
                self.create_navigation_bridge()
                nav = self._bridges["navigation"]
            from ui_qml_bridge.connections_bridge import ConnectionsBridge
            self._bridges["connections"] = ConnectionsBridge(
                michi_link_ctrl=self._get("connection_service"),
                connection_service=self._get("connection_service"),
                navigation_bridge=nav,
            )

    def create_home_audio_bridge(self):
        if "home_audio" not in self._bridges:
            nav = self._bridges.get("navigation")
            if nav is None:
                self.create_navigation_bridge()
                nav = self._bridges["navigation"]
            pss = self._bridges.get("page_state")
            if pss is None:
                self.create_page_state_store()
                pss = self._bridges["page_state"]
            cap = self._bridges.get("capability")
            if cap is None:
                self.create_capability_bridge()
                cap = self._bridges["capability"]
            acc = self._bridges.get("accessibility")
            if acc is None:
                self.create_accessibility_bridge()
                acc = self._bridges["accessibility"]
            notif = self._bridges.get("notification")
            if notif is None:
                self.create_notification_bridge()
                notif = self._bridges["notification"]
            from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
            self._bridges["home_audio"] = HomeAudioBridge(
                home_audio_service=self._get("home_audio_service"),
                job_service=self._get("job_service"),
                action_registry=self._bridges.get("action_registry"),
                navigation_bridge=nav,
                page_state_store=pss,
                capability_bridge=cap,
                accessibility_bridge=acc,
                notification_bridge=notif,
            )

    def create_devices_bridge(self):
        if "devices" not in self._bridges:
            from ui_qml_bridge.devices_bridge import DevicesBridge
            self._bridges["devices"] = DevicesBridge(
                device_sync_service=self._get("device_sync_service"),
                job_service=self._get("job_service"),
                action_registry=self._bridges.get("action_registry"),
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
                page_state_store=self._bridges.get("page_state"),
                accessibility_bridge=self._bridges.get("accessibility"),
            )

    def create_radio_bridge(self):
        if "radio" not in self._bridges:
            from ui_qml_bridge.radio_bridge import RadioBridge
            self._bridges["radio"] = RadioBridge(
                radio_manager=self._get("radio_service"),
                player_service=self._get("playback_service"),
            )

    def create_audio_lab_bridge(self):
        if "audio_lab" not in self._bridges:
            from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
            self._bridges["audio_lab"] = AudioLabBridge(
                audio_lab_service=self._get("audio_lab_service"),
                job_service=self._get("job_service"),
                process_controller=self._get("process_controller"),
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
                notification_bridge=self._bridges.get("notification"),
            )

    def create_metadata_bridge(self):
        if "metadata" not in self._bridges:
            from ui_qml_bridge.metadata_bridge import MetadataBridge
            self._bridges["metadata"] = MetadataBridge(
                metadata_service=self._get("metadata_service"),
                job_service=self._get("job_service"),
            )

    def create_smart_tagging_bridge(self):
        if "smart_tagging" not in self._bridges:
            from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
            self._bridges["smart_tagging"] = SmartTaggingBridge(
                service=self._get("smart_tagging_service"),
                worker_manager=self._get("worker_manager"),
                query_service=self._get("library_query_service"),
            )

    def create_disc_lab_bridge(self):
        if "disc_lab" not in self._bridges:
            from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
            self._bridges["disc_lab"] = DiscLabBridge(
                disc_detection_service=self._get("disc_lab_service"),
                worker_manager=self._get("worker_manager"),
            )

    def create_library_doctor_bridge(self):
        if "library_doctor" not in self._bridges:
            from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
            self._bridges["library_doctor"] = LibraryDoctorBridge(
                db=self._get("database"),
                worker_manager=self._get("worker_manager"),
            )

    def create_diagnostics_bridge(self):
        if "diagnostics" not in self._bridges:
            from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
            self._bridges["diagnostics"] = DiagnosticsBridge(
                diagnostics_service=self._get("diagnostics_service"),
                player_service=self._get("playback_service"),
                worker_manager=self._get("worker_manager"),
                query_executor=self._get("query_executor"),
                library_bridge=self._bridges.get("library"),
            )

    def create_michi_ai_bridge(self):
        if "michi_ai" not in self._bridges:
            from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
            self._bridges["michi_ai"] = MichiAIBridge(
                michi_ai_service=self._get("michi_ai_service"),
                job_service=self._get("job_service"),
                action_registry=self._bridges.get("action_registry"),
                confirmation_service=self._bridges.get("confirmation"),
                navigation_bridge=self._bridges.get("navigation"),
                capability_bridge=self._bridges.get("capability"),
                page_state_store=self._bridges.get("page_state"),
                accessibility_bridge=self._bridges.get("accessibility"),
            )

    def create_tagging_bridge(self):
        self.create_smart_tagging_bridge()

    def create_doctor_bridge(self):
        self.create_library_doctor_bridge()

    def create_action_registry_bridge(self):
        if "action_registry" not in self._bridges:
            from ui_qml_bridge.action_registry import ActionRegistry
            reg = self._get("action_registry")
            self._bridges["action_registry"] = reg if reg is not None else ActionRegistry()

    def create_notification_bridge(self):
        if "notification" not in self._bridges:
            from ui_qml_bridge.notification_bridge import NotificationBridge
            self._bridges["notification"] = NotificationBridge(
                action_registry=self._bridges.get("action_registry"),
                job_bridge=self._bridges.get("job_bridge"),
                notification_service=self._get("notification_service"),
                navigation_bridge=self._bridges.get("navigation"),
                diagnostics_service=self._get("diagnostics_service"),
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

    def create_home_bridge(self):
        if "home" not in self._bridges:
            from ui_qml_bridge.home_bridge import HomeBridge
            self._bridges["home"] = HomeBridge(
                db=self._get("database"),
                player_service=self._get("playback_service"),
                library_bridge=self._bridges.get("library"),
                library_sources_service=self._get("library_sources_service"),
                job_bridge=self._bridges.get("job_bridge"),
            )

    def create_app_bridge(self):
        if "app" not in self._bridges:
            from ui_qml_bridge.app_bridge import AppBridge
            self._bridges["app"] = AppBridge(
                worker_manager=self._get("worker_manager"),
                query_executor=self._get("query_executor"),
                player_service=self._get("playback_service"),
                queue_bridge=self._bridges.get("queue"),
                sync_manager=self._get("device_sync_service"),
                home_audio_controller=self._get("home_audio_service"),
                radio_manager=self._get("radio_service"),
                discovery=None,
                db=self._get("database"),
            )

    def create_desktop_bridge(self):
        if "desktop" not in self._bridges:
            from ui_qml_bridge.desktop_bridge import DesktopBridge
            self._bridges["desktop"] = DesktopBridge()

    def create_runtime_quality_bridge(self):
        if "runtime_quality" not in self._bridges:
            from ui_qml_bridge.runtime_quality_bridge import RuntimeQualityBridge
            self._bridges["runtime_quality"] = RuntimeQualityBridge()

    def create_physical_audio_bridge(self):
        if "physical_audio" not in self._bridges:
            from ui_qml_bridge.physical_audio_bridge import PhysicalAudioBridge
            self._bridges["physical_audio"] = PhysicalAudioBridge()

    def create_selection_context_bridge(self):
        if "selection_context" not in self._bridges:
            from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
            self._bridges["selection_context"] = SelectionContextBridge()

    def create_cover_provider_bridge(self):
        if "cover_provider" not in self._bridges:
            from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
            self._bridges["cover_provider"] = CoverProviderBridge(cover_bridge=self._bridges.get("cover"))

    def create_query_executor(self):
        if "query_executor" not in self._bridges:
            from ui_qml_bridge.query_executor import QueryExecutor
            self._bridges["query_executor"] = QueryExecutor(
                worker_manager=self._get("worker_manager"),
                owns_worker_manager=False,
            )

    def create_app_state_bridge(self):
        if "app_state" not in self._bridges:
            from ui_qml_bridge.app_state_bridge import AppStateBridge
            self._bridges["app_state"] = AppStateBridge()

    def validate_required_dependencies(self) -> list[str]:
        missing = []
        required_keys = [
            "playback_service", "connection_factory", "worker_manager",
            "settings_service", "queue_service", "action_registry",
        ]
        for key in required_keys:
            if not self._container.contains(key):
                missing.append(key)
        return missing

    def create_all(self) -> dict[str, QObject]:
        missing = self.validate_required_dependencies()
        if missing:
            logger.error("BridgeFactory: MISSING REQUIRED dependencies: %s", missing)
            raise RuntimeError(f"BridgeFactory cannot start: missing {missing}")

        # 1. Infraestructura
        self.create_page_state_store()
        self.create_route_registry_bridge()
        self.create_navigation_bridge()
        self.create_job_bridge()
        self.create_confirmation_bridge()
        self.create_accessibility_bridge()
        self.create_theme_bridge()
        self.create_capability_bridge()
        self.create_action_registry_bridge()

        # 2. Dominio
        self.create_library_bridge()
        self.create_library_sources_bridge()
        self.create_playback_bridge()
        self.create_nowplaying_bridge()
        self.create_queue_bridge()
        self.create_playlists_bridge()
        self.create_history_bridge()
        self.create_search_bridge()
        self.create_mix_bridge()
        self.create_lyrics_bridge()
        self.create_settings_bridge()
        self.create_output_profiles_bridge()
        self.create_eq_bridge()
        self.create_connections_bridge()
        self.create_home_audio_bridge()
        self.create_devices_bridge()
        self.create_radio_bridge()
        self.create_audio_lab_bridge()
        self.create_metadata_bridge()
        self.create_disc_lab_bridge()
        self.create_smart_tagging_bridge()
        self.create_library_doctor_bridge()
        self.create_diagnostics_bridge()
        self.create_michi_ai_bridge()

        # 3. Agregadores
        self.create_command_palette_bridge()
        self.create_home_bridge()
        self.create_app_bridge()
        self.create_desktop_bridge()

        self.create_runtime_quality_bridge()
        self.create_physical_audio_bridge()
        if "cover" not in self._bridges:
            from PySide6.QtCore import QObject
            self._bridges["cover"] = QObject()
        self.create_cover_provider_bridge()
        self.create_app_state_bridge()
        self.create_selection_context_bridge()
        self.create_query_executor()

        capability = self._bridges.get("capability")
        if capability and hasattr(capability, 'refresh'):
            capability.refresh()

        self.bind_action_handlers()

        self._validate_bridge_identities()
        self._assert_wiring()
        return self._bridges

    def _validate_bridge_identities(self):
        keys = set(self._bridges.keys())
        from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
        missing = [k for k in QML_CONTEXT_BINDINGS.values() if k not in keys]
        if missing:
            logger.warning("BridgeFactory: missing context bindings: %s", missing)

    def _assert_wiring(self):
        container = self._container
        factory = self

        reg = factory._bridges.get("action_registry")
        if reg is not None:
            container_reg = container.require("action_registry")
            assert reg is container_reg, "action_registry identity mismatch"

        pb = factory._bridges.get("playback")
        if pb is not None:
            np = pb._nowplaying
            assert np._player is container.require("playback_service"), \
                "playback_bridge.service identity mismatch"

        qb = factory._bridges.get("queue")
        if qb is not None:
            assert qb._queue_service is container.require("queue_service"), \
                "queue_bridge.queue_service identity mismatch"

        sb = factory._bridges.get("settings")
        if sb is not None:
            assert sb._svc is container.require("settings_service"), \
                "settings_bridge.service identity mismatch"

        plb = factory._bridges.get("playlists")
        if plb is not None:
            container_svc = container.require("playlist_service")
            assert plb._svc is container_svc, \
                "playlists_bridge.playlist_service identity mismatch"

        search = factory._bridges.get("global_search")
        if search is not None:
            assert search._svc is container.require("global_search_service"), \
                "search_bridge.search_service identity mismatch"

        mix = factory._bridges.get("mix")
        if mix is not None:
            assert mix._mix_svc is container.require("mix_query_service"), \
                "mix_bridge.mix_service identity mismatch"

        ai = factory._bridges.get("michi_ai")
        if ai is not None:
            assert ai._registry is container.require("action_registry"), \
                "ai_bridge.action_registry identity mismatch"

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
                "capability": "create_capability_bridge",
                "notification": "create_notification_bridge",
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
                "global_search": "create_search_bridge",
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

    def bind_action_handlers(self):
        registry = self._bridges.get("action_registry")
        if not registry:
            return
        from ui_qml_bridge.action_registry_binder import ActionRegistryBinder
        binder = ActionRegistryBinder(registry, self._bridges)
        binder.bind_all()

    def __repr__(self) -> str:
        return f"BridgeFactory(bridges={len(self._bridges)})"


def create_all_bridges(container: ServiceContainer) -> dict[str, QObject]:
    factory = BridgeFactory(container)
    return factory.create_all()
