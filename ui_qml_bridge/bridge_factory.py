from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from ui_qml_bridge.service_bundle import ServiceBundle

if TYPE_CHECKING:
    from ui_qml_bridge.navigation_bridge import NavigationBridge

logger = logging.getLogger("michi.bridge_factory")


class BridgeFactory(QObject):
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
            self._bridges["app"] = AppBridge(parent=self)
        return self._bridges["app"]

    def create_navigation_bridge(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        if "navigation" not in self._bridges:
            self._bridges["navigation"] = NavigationBridge(parent=self)
            if self._nav:
                self._bridges["navigation"].set_controller_bridge(self._nav)
        return self._bridges["navigation"]

    def create_theme_bridge(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        if "theme" not in self._bridges:
            self._bridges["theme"] = ThemeBridge(parent=self)
        return self._bridges["theme"]

    def create_library_bridge(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        if "library" not in self._bridges:
            self._bridges["library"] = LibraryBridge(
                db=self._services.db,
                search_engine=self._services.search_engine,
                player_service=self._services.player_service,
                parent=self,
            )
            self._register_capability("library", "db")
        return self._bridges["library"]

    def create_playback_bridge(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        if "playback" not in self._bridges:
            np_bridge = self._bridges.get("nowplaying")
            self._bridges["playback"] = PlaybackBridge(
                player_service=self._services.player_service,
                nowplaying_bridge=np_bridge,
                parent=self,
            )
            self._register_capability("playback", "player_service")
        return self._bridges["playback"]

    def create_nowplaying_bridge(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        if "nowplaying" not in self._bridges:
            self._bridges["nowplaying"] = NowPlayingBridge(
                player_service=self._services.player_service,
                parent=self,
            )
            self._register_capability("nowplaying", "player_service")
        return self._bridges["nowplaying"]

    def create_mix_bridge(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        if "mix" not in self._bridges:
            self._bridges["mix"] = MixBridge(
                db=self._services.db,
                player_service=self._services.player_service,
                parent=self,
            )
            self._register_capability("mix", "db")
        return self._bridges["mix"]

    def create_lyrics_bridge(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        if "lyrics" not in self._bridges:
            np_bridge = self._bridges.get("nowplaying")
            self._bridges["lyrics"] = LyricsBridge(
                lyrics_service=self._services.lyrics_service,
                playback_context=np_bridge,
                parent=self,
            )
        return self._bridges["lyrics"]

    def create_connections_bridge(self):
        from ui_qml_bridge.connections_bridge import ConnectionsBridge
        if "connections" not in self._bridges:
            self._bridges["connections"] = ConnectionsBridge(
                michi_link_controller=self._services.michi_link_controller,
                navigation_bridge=self._nav or self._bridges.get("navigation"),
                parent=self,
            )
            self._register_capability("connections", "michi_link_controller")
        return self._bridges["connections"]

    def create_home_audio_bridge(self):
        from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
        if "home_audio" not in self._bridges:
            self._bridges["home_audio"] = HomeAudioBridge(
                home_audio_controller=self._services.home_audio_controller,
                snapcast_controller=self._services.snapcast_controller,
                parent=self,
            )
            self._register_capability("home_audio", "home_audio_controller")
        return self._bridges["home_audio"]

    def create_devices_bridge(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        if "devices" not in self._bridges:
            self._bridges["devices"] = DevicesBridge(
                sync_manager=self._services.sync_manager,
                parent=self,
            )
            self._register_capability("devices", "sync_manager")
        return self._bridges["devices"]

    def create_radio_bridge(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        if "radio" not in self._bridges:
            self._bridges["radio"] = RadioBridge(
                radio_service=self._services.radio_service,
                playback_gateway=self._services.player_service,
                parent=self,
            )
            self._register_capability("radio", "radio_service")
        return self._bridges["radio"]

    def create_playlists_bridge(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
        if "playlists" not in self._bridges:
            if "selection_context" not in self._bridges:
                self._bridges["selection_context"] = SelectionContextBridge(parent=self)
            self._bridges["playlists"] = PlaylistsBridge(
                db=self._services.db,
                player_service=self._services.player_service,
                selection_context=self._bridges["selection_context"],
                parent=self,
            )
            self._register_capability("playlists", "db")
        return self._bridges["playlists"]

    def create_settings_bridge(self):
        from ui_qml_bridge.settings_bridge import SettingsBridge
        if "settings" not in self._bridges:
            self._bridges["settings"] = SettingsBridge(parent=self)
        return self._bridges["settings"]

    def create_eq_bridge(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        if "eq" not in self._bridges:
            self._bridges["eq"] = EqBridge(
                player_service=self._services.player_service,
                parent=self,
            )
            self._register_capability("eq", "player_service")
        return self._bridges["eq"]

    def create_audio_lab_bridge(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        if "audio_lab" not in self._bridges:
            self._bridges["audio_lab"] = AudioLabBridge(
                db_connection=self._services.db_connection,
                parent=self,
            )
            self._register_capability("audio_lab", "db_connection")
        return self._bridges["audio_lab"]

    def create_metadata_bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        if "metadata" not in self._bridges:
            self._bridges["metadata"] = MetadataBridge(
                metadata_service=self._services.metadata_service,
                job_service=self._services.job_service,
                confirmation_service=self._services.confirmation_service,
                parent=self,
            )
        return self._bridges["metadata"]

    def create_smart_tagging_bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        if "smart_tagging" not in self._bridges:
            self._bridges["smart_tagging"] = SmartTaggingBridge(
                library_query_service=self._services.db,
                smart_tagging_service=self._services.smart_tagging_service,
                parent=self,
            )
        return self._bridges["smart_tagging"]

    def create_disc_lab_bridge(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        if "disc_lab" not in self._bridges:
            self._bridges["disc_lab"] = DiscLabBridge(
                disc_service=self._services.disc_service,
                parent=self,
            )
            self._register_capability("disc_lab", "disc_service")
        return self._bridges["disc_lab"]

    def create_library_doctor_bridge(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        if "library_doctor" not in self._bridges:
            self._bridges["library_doctor"] = LibraryDoctorBridge(
                db=self._services.db,
                parent=self,
            )
            self._register_capability("library_doctor", "db")
        return self._bridges["library_doctor"]

    def create_michi_ai_bridge(self):
        from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
        if "michi_ai" not in self._bridges:
            assistant_core = self._services.assistant_core_service
            if assistant_core is None and self._services.registry:
                assistant_core = self._services.registry.ensure_assistant_core()
            self._bridges["michi_ai"] = MichiAIBridge(
                assistant_service=assistant_core,
            )
        return self._bridges["michi_ai"]

    def create_cover_bridge(self):
        return self._bridges.get("cover")

    def create_notification_bridge(self):
        from ui_qml_bridge.notification_bridge import NotificationBridge
        if "notification" not in self._bridges:
            self._bridges["notification"] = NotificationBridge(parent=self)
        return self._bridges["notification"]

    def create_route_registry_bridge(self):
        from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
        if "route_registry" not in self._bridges:
            self._bridges["route_registry"] = RouteRegistryBridge(parent=self)
        return self._bridges["route_registry"]

    def create_app_state_bridge(self):
        from ui_qml_bridge.app_state_bridge import AppStateBridge
        if "app_state" not in self._bridges:
            self._bridges["app_state"] = AppStateBridge(parent=self)
        return self._bridges["app_state"]

    def create_diagnostics_bridge(self):
        from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
        if "diagnostics" not in self._bridges:
            self._bridges["diagnostics"] = DiagnosticsBridge(
                player_service=self._services.player_service,
                db=self._services.db,
                radio_manager=self._services.radio_service,
                sync_manager=self._services.sync_manager,
                parent=self,
            )
            self._register_capability("diagnostics", "db")
        return self._bridges["diagnostics"]

    def get_action_registry(self):
        if self._action_registry is None:
            from ui_qml_bridge.action_registry import ActionRegistry
            self._action_registry = ActionRegistry(parent=self)
        return self._action_registry

    def create_action_registry_bridge(self):
        from ui_qml_bridge.action_registry_bridge import ActionRegistryBridge
        if "action_registry" not in self._bridges:
            self._bridges["action_registry"] = ActionRegistryBridge(
                action_registry=self.get_action_registry(),
                parent=self,
            )
        return self._bridges["action_registry"]

    def create_command_palette_bridge(self):
        from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
        if "command_palette" not in self._bridges:
            self._bridges["command_palette"] = CommandPaletteBridge(
                action_registry=self.get_action_registry(),
                navigation_bridge=self._bridges.get("navigation"),
                nowplaying_bridge=self._bridges.get("nowplaying"),
                parent=self,
            )
        return self._bridges["command_palette"]

    def create_global_search_bridge(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        if "global_search" not in self._bridges:
            self._bridges["global_search"] = GlobalSearchBridge(
                db=self._services.db,
                search_engine=self._services.search_engine,
                parent=self,
            )
        return self._bridges["global_search"]

    def create_cover_provider_bridge(self):
        from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
        if "cover_provider" not in self._bridges:
            self._bridges["cover_provider"] = CoverProviderBridge(
                db=self._services.db,
                parent=self,
            )
        return self._bridges["cover_provider"]

    def create_job_bridge(self):
        from ui_qml_bridge.job_bridge import JobBridge
        if "job" not in self._bridges:
            self._bridges["job"] = JobBridge(
                worker_manager=self._services.worker_manager,
                db=self._services.db,
                library_bridge=self._bridges.get("library"),
                parent=self,
            )
        return self._bridges["job"]

    def create_desktop_bridge(self):
        from ui_qml_bridge.desktop_bridge import DesktopBridge
        if "desktop" not in self._bridges:
            self._bridges["desktop"] = DesktopBridge(parent=self)
        return self._bridges["desktop"]

    def create_page_state_store(self):
        if "page_state" not in self._bridges:
            from ui_qml_bridge.page_state_store import PageStateStore
            self._bridges["page_state"] = PageStateStore(parent=self)
        return self._bridges["page_state"]

    def create_queue_bridge(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        if "queue" not in self._bridges:
            self._bridges["queue"] = QueueBridge(
                player_service=self._services.player_service,
                parent=self,
            )
        return self._bridges["queue"]

    def create_history_bridge(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        if "history" not in self._bridges:
            self._bridges["history"] = HistoryBridge(
                db=self._services.db,
                parent=self,
            )
        return self._bridges["history"]

    def create_home_bridge(self):
        from ui_qml_bridge.home_bridge import HomeBridge
        if "home" not in self._bridges:
            self._bridges["home"] = HomeBridge(parent=self)
        return self._bridges["home"]

    def create_all(self) -> dict[str, QObject]:
        self.create_app_bridge()
        self.create_navigation_bridge()
        self.create_theme_bridge()
        self.create_nowplaying_bridge()
        self.create_playback_bridge()
        self.create_library_bridge()
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
        self.create_queue_bridge()
        self.create_history_bridge()
        self.create_home_bridge()
        return self._bridges
