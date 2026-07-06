"""BridgeFactory — creates bridges once, injects dependencies, registers availability.

Does not open databases, construct backends, or start services.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from ui_qml_bridge.service_bundle import ServiceBundle

if TYPE_CHECKING:
    from ui_qml_bridge.navigation_bridge import NavigationBridge

logger = logging.getLogger("michi.bridge_factory")


class BridgeFactory(QObject):
    """Creates each bridge exactly once with injected dependencies."""

    def __init__(self, services: ServiceBundle, navigation_bridge: NavigationBridge | None = None, parent=None):
        super().__init__(parent)
        self._services = services
        self._nav = navigation_bridge
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
            self._bridges["app"] = AppBridge()
        return self._bridges["app"]

    def create_navigation_bridge(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        if "navigation" not in self._bridges:
            nav = NavigationBridge()
            self._bridges["navigation"] = nav
            self._nav = nav
        return self._bridges["navigation"]

    def create_theme_bridge(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        if "theme" not in self._bridges:
            self._bridges["theme"] = ThemeBridge()
        return self._bridges["theme"]

    def create_library_bridge(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from ui_qml_bridge.query_executor import QueryExecutor
        if "library" not in self._bridges:
            qs = LibraryQueryService(self._services.db) if self._services.db else None
            qe = QueryExecutor(worker_manager=self._services.worker_manager, parent=self)
            self._bridges["library"] = LibraryBridge(
                db=self._services.db,
                search_engine=self._services.search_engine,
                playback_ctrl=self._services.player_service,
                query_service=qs,
                query_executor=qe,
                worker_manager=self._services.worker_manager,
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
                playback_ctrl=self._services.player_service,
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
                navigation_bridge=self._nav,
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

    def create_playlists_bridge(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        if "playlists" not in self._bridges:
            from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
            sel = SelectionContextBridge()
            self._bridges["selection_context"] = sel
            self._bridges["playlists"] = PlaylistsBridge(
                db=self._services.db,
                selection_context=sel,
                player_service=self._services.player_service,
            )
        self._register_capability("playlists", "db")
        return self._bridges["playlists"]

    def create_settings_bridge(self):
        from ui_qml_bridge.settings_bridge import SettingsBridge
        if "settings" not in self._bridges:
            self._bridges["settings"] = SettingsBridge()
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
            )
        self._register_capability("audio_lab", "db_connection")
        return self._bridges["audio_lab"]

    def create_metadata_bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        if "metadata" not in self._bridges:
            self._bridges["metadata"] = MetadataBridge()
        return self._bridges["metadata"]

    def create_smart_tagging_bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        if "smart_tagging" not in self._bridges:
            br = SmartTaggingBridge()
            if self._services.smart_tagging_service:
                br.set_service(self._services.smart_tagging_service)
            self._bridges["smart_tagging"] = br
        return self._bridges["smart_tagging"]

    def create_disc_lab_bridge(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        if "disc_lab" not in self._bridges:
            self._bridges["disc_lab"] = DiscLabBridge(
                disc_detection_service=self._services.disc_service,
            )
        self._register_capability("disc_lab", "disc_service")
        return self._bridges["disc_lab"]

    def create_library_doctor_bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        if "library_doctor" not in self._bridges:
            self._bridges["library_doctor"] = LibraryDoctorBridge(
                db=self._services.db,
            )
        self._register_capability("library_doctor", "db")
        return self._bridges["library_doctor"]

    def create_michi_ai_bridge(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        if "michi_ai" not in self._bridges:
            self._bridges["michi_ai"] = MichiAIBridge()
        return self._bridges["michi_ai"]

    def create_cover_bridge(self):
        if "cover" not in self._bridges:
            pass  # cover_bridge is registered as QML type, not context property
        return self._bridges.get("cover")

    def create_notification_bridge(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        if "notification" not in self._bridges:
            self._bridges["notification"] = NotificationBridge()
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

    def create_command_palette_bridge(self):
        if "command_palette" not in self._bridges:
            from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
            registry = self.get_action_registry()
            self._bridges["command_palette"] = CommandPaletteBridge(
                action_registry=registry,
                navigation_bridge=self._nav or self.get("navigation"),
                nowplaying_bridge=self.get("nowplaying"),
            )
        return self._bridges["command_palette"]

    def create_global_search_bridge(self):
        if "global_search" not in self._bridges:
            from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
            self._bridges["global_search"] = GlobalSearchBridge(
                db=self._services.db,
                search_engine=self._services.search_engine,
            )
        return self._bridges["global_search"]

    def create_cover_provider_bridge(self):
        if "cover_provider" not in self._bridges:
            from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
            self._bridges["cover_provider"] = CoverProviderBridge(db=self._services.db)
        return self._bridges["cover_provider"]

    def create_job_bridge(self):
        if "job_bridge" not in self._bridges:
            from ui_qml_bridge.job_bridge import JobBridge
            self._bridges["job_bridge"] = JobBridge(
                worker_manager=self._services.worker_manager,
                db=self._services.db,
                library_bridge=self.get("library"),
            )
        return self._bridges["job_bridge"]

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

    def create_all(self) -> dict[str, QObject]:
        """Create all bridges and return dict of name->bridge."""
        self.create_navigation_bridge()
        self.create_app_bridge()
        self.create_theme_bridge()
        self.create_library_bridge()
        self.create_playback_bridge()
        self.create_nowplaying_bridge()
        self.create_mix_bridge()
        self.create_lyrics_bridge()
        self.create_connections_bridge()
        self.create_home_audio_bridge()
        self.create_devices_bridge()
        self.create_radio_bridge()
        self.create_playlists_bridge()
        self.create_settings_bridge()
        self.create_eq_bridge()
        self.create_audio_lab_bridge()
        self.create_metadata_bridge()
        self.create_smart_tagging_bridge()
        self.create_disc_lab_bridge()
        self.create_library_doctor_bridge()
        self.create_michi_ai_bridge()
        self.create_notification_bridge()
        self.create_route_registry_bridge()
        self.create_app_state_bridge()
        self.create_diagnostics_bridge()
        self.create_action_registry_bridge()
        self.create_command_palette_bridge()
        self.create_global_search_bridge()
        self.create_cover_provider_bridge()
        self.create_job_bridge()
        self.create_desktop_bridge()
        self.create_page_state_store()
        return self._bridges

    def __repr__(self) -> str:
        return f"BridgeFactory(bridges={len(self._bridges)}, capabilities={self._capabilities})"
