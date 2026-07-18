"""Canonical mapping from QML context property names to BridgeFactory bridge keys.

Single declarative CONTEXT_BINDINGS table.
Each entry: bridge_class, context_name, required_services, optional_services, routes, lifecycle_owner.
"""
from __future__ import annotations

from dataclasses import dataclass

from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.app_bridge import AppBridge
from ui_qml_bridge.app_state_bridge import AppStateBridge
from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
from ui_qml_bridge.capability_bridge import CapabilityBridge
from ui_qml_bridge.confirmation_bridge import ConfirmationBridge
from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge
from ui_qml_bridge.connections_bridge import ConnectionsBridge
from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge
from ui_qml_bridge.desktop_bridge import DesktopBridge
from ui_qml_bridge.devices_bridge import DevicesBridge
from ui_qml_bridge.mobile_sync_bridge import MobileSyncBridge
from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
from ui_qml_bridge.eq_bridge import EqBridge
from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
from ui_qml_bridge.history_bridge import HistoryBridge
from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
from ui_qml_bridge.home_bridge import HomeBridge
from ui_qml_bridge.job_bridge import JobBridge
from ui_qml_bridge.library_bridge import LibraryBridge
from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
from ui_qml_bridge.lyrics_bridge import LyricsBridge
from ui_qml_bridge.metadata_bridge import MetadataBridge
from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
from ui_qml_bridge.mix_bridge import MixBridge
from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.notification_bridge import NotificationBridge
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
from ui_qml_bridge.page_state_store import PageStateStore
from ui_qml_bridge.physical_audio_bridge import PhysicalAudioBridge
from ui_qml_bridge.playback_bridge import PlaybackBridge
from ui_qml_bridge.playlists_bridge import PlaylistsBridge
from ui_qml_bridge.queue_bridge import QueueBridge
from ui_qml_bridge.radio_bridge import RadioBridge
from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
from ui_qml_bridge.runtime_quality_bridge import RuntimeQualityBridge
from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
from ui_qml_bridge.theme_bridge import ThemeBridge


@dataclass
class ContextBinding:
    bridge_class: type
    context_name: str
    required_services: tuple[str, ...] = ()
    optional_services: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    lifecycle_owner: str = "factory"


CONTEXT_BINDINGS: list[ContextBinding] = [
    ContextBinding(NavigationBridge,    "navigationBridge"),
    ContextBinding(AppBridge,           "appBridge",       required_services=("connection_factory", "playback_service"), optional_services=("device_sync_service", "home_audio_service", "radio_service")),
    ContextBinding(ThemeBridge,         "themeBridge",    required_services=("settings_coordinator",)),
    ContextBinding(NotificationBridge,  "notificationBridge", required_services=("notification_service", "action_registry"), optional_services=("diagnostics_service",)),
    ContextBinding(AccessibilityBridge, "accessibilityBridge", optional_services=("playback_service", "settings_coordinator")),
    ContextBinding(AppStateBridge,      "appStateBridge"),
    ContextBinding(RouteRegistryBridge, "routeRegistryBridge"),
    ContextBinding(ActionRegistry,      "actionRegistry"),
    ContextBinding(CapabilityBridge,    "capabilityBridge"),
    ContextBinding(ConfirmationBridge,  "confirmationBridge", required_services=("confirmation_service",)),
    ContextBinding(JobBridge,           "jobBridge",       required_services=("worker_manager", "connection_factory")),
    ContextBinding(SelectionContextBridge, "selectionContextBridge"),
    ContextBinding(LibraryBridge,       "libraryBridge",   required_services=("connection_factory", "worker_manager", "global_search_service", "library_query_service", "query_executor", "track_action_service"), optional_services=("playback_service",)),
    ContextBinding(PlaybackBridge,      "playbackBridge",  required_services=("playback_service",)),
    ContextBinding(NowPlayingBridge,    "nowplayingBridge", required_services=("playback_service", "worker_manager")),
    ContextBinding(QueueBridge,         "queueBridge",     required_services=("playback_service",)),
    ContextBinding(HistoryBridge,       "historyBridge",   required_services=("connection_factory",), optional_services=("history_query_service", "query_executor", "playback_service")),
    ContextBinding(MixBridge,           "mixBridge",       required_services=("mix_query_service", "job_service", "playlist_service", "playback_service", "queue_service")),
    ContextBinding(LyricsBridge,        "lyricsBridge",    required_services=("worker_manager",)),
    ContextBinding(GlobalSearchBridge,  "globalSearchBridge", required_services=("global_search_service", "query_executor")),
    ContextBinding(SettingsBridgeV2,    "settingsBridge",  required_services=("settings_service",)),
    ContextBinding(SettingsBridgeV2,    "settingsBridgeV2", required_services=("settings_service",)),
    ContextBinding(OutputProfilesBridge,"outputProfilesBridge", required_services=("playback_service",)),
    ContextBinding(EqBridge,            "eqBridge",        required_services=("playback_service",)),
    ContextBinding(ConnectionsBridge,   "connectionsBridge", optional_services=("connection_service",)),
    ContextBinding(HomeAudioBridge,     "homeAudioBridge", required_services=("home_audio_service",)),
    ContextBinding(DevicesBridge,       "devicesBridge",   required_services=("device_sync_service", "job_service")),
    ContextBinding(MobileSyncBridge,    "mobileSyncBridge", optional_services=("mobile_sync_service",)),
    ContextBinding(RadioBridge,         "radioBridge",     required_services=("playback_service",), optional_services=("radio_service",)),
    ContextBinding(LibrarySourcesBridge,"librarySourcesBridge", required_services=("library_sources_service",)),
    ContextBinding(HomeBridge,          "homeBridge",      required_services=("connection_factory", "playback_service", "library_sources_service")),
    ContextBinding(AudioLabBridge,      "audioLabBridge",  required_services=("worker_manager",), optional_services=("audio_lab_service", "job_service", "process_controller")),
    ContextBinding(MetadataBridge,      "metadataBridge",  required_services=("worker_manager",), optional_services=("metadata_service", "job_service")),
    ContextBinding(SmartTaggingBridge,  "smartTaggingBridge", required_services=("worker_manager", "library_query_service"), optional_services=("smart_tagging_service",)),
    ContextBinding(LibraryDoctorBridge, "libraryDoctorBridge", required_services=("connection_factory", "worker_manager")),
    ContextBinding(MichiAIBridge,       "michiAiBridge",   required_services=("device_sync_service", "job_service")),
    ContextBinding(DiagnosticsBridge,   "diagnosticsBridge", required_services=("playback_service", "connection_factory", "worker_manager", "query_executor"), optional_services=("radio_service", "device_sync_service")),
    ContextBinding(RuntimeQualityBridge,"runtimeQualityBridge"),
    ContextBinding(PhysicalAudioBridge, "physicalAudioBridge"),
    ContextBinding(CommandPaletteBridge,"commandPaletteBridge"),
    ContextBinding(CoverProviderBridge, "coverProviderBridge"),
    ContextBinding(DesktopBridge,       "desktopBridge"),
    ContextBinding(PageStateStore,      "pageStateStore"),
    ContextBinding(PlaylistsBridge,     "playlistsBridge", required_services=("connection_factory",), optional_services=("playback_service", "playlist_service")),
]

def _camel_to_snake(name: str) -> str:
    result = ""
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            result += "_" + ch.lower()
        else:
            result += ch.lower()
    return result


_EXPLICIT_BRIDGE_KEYS: dict[str, str] = {
    "settingsBridgeV2": "settings_v2",
    "actionRegistry": "action_registry",
    "jobBridge": "job_bridge",
    "pageStateStore": "page_state",
    "confirmationBridge": "confirmation",
}


QML_CONTEXT_BINDINGS: dict[str, str] = {}
for b in CONTEXT_BINDINGS:
    key = b.context_name
    if key in _EXPLICIT_BRIDGE_KEYS:
        val = _EXPLICIT_BRIDGE_KEYS[key]
    elif key.endswith("Bridge"):
        val = _camel_to_snake(key[: -len("Bridge")])
    elif key.endswith("Store"):
        val = _camel_to_snake(key[: -len("Store")])
    else:
        val = key.lower()
    QML_CONTEXT_BINDINGS[key] = val
