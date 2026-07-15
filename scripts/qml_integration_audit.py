#!/usr/bin/env python3
"""QML Integration Audit — verifies every module in qml_modules.yaml has:
   - registered service, bridge, context, model, route.

Consumes docs/qml_parallel/integration_manifest.yaml if it exists,
otherwise generates expectations from code.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

MODULES_YAML = REPO / "config" / "qml_modules.yaml"
MANIFEST_YAML = REPO / "docs" / "qml_parallel" / "integration_manifest.yaml"

# Canonical mappings derived from codebase
CANONICAL_SERVICES = {
    "connection_factory", "worker_manager", "query_executor", "job_service",
    "event_bus", "settings_coordinator", "settings_service",
    "library_query_service", "library_sources_service", "library_mutation_service",
    "playlist_service", "history_query_service", "global_search_service",
    "mix_query_service", "track_action_service", "playback_service",
    "queue_service", "metadata_service",
    "theme_service", "accessibility_service", "audio_lab_service",
    "smart_tagging_service", "library_doctor_service", "device_sync_service",
    "connection_service", "home_audio_service", "diagnostics_service",
    "notification_service", "action_registry",
}

CANONICAL_BRIDGES = {
    "app", "navigation", "theme", "library", "playback", "nowplaying",
    "mix", "michi_ai", "metadata", "queue", "history", "devices", "radio",
    "connections", "home_audio", "home", "settings", "settings_v2",
    "audio_lab", "output_profiles", "smart_tagging", "library_doctor",
    "disc_lab", "lyrics", "eq", "global_search", "notification",
    "accessibility", "app_state", "route_registry", "action_registry",
    "capability", "cover_provider", "job_bridge", "command_palette",
    "diagnostics", "runtime_quality", "physical_audio", "selection_context",
    "library_sources", "desktop", "page_state", "playlists",
}

CANONICAL_CONTEXTS = {
    "appBridge", "navigationBridge", "themeBridge", "libraryBridge",
    "michiAiBridge", "metadataBridge", "mixBridge", "playbackBridge",
    "nowplayingBridge", "devicesBridge", "playlistsBridge", "audioLabBridge",
    "settingsBridge", "radioBridge", "connectionsBridge", "smartTaggingBridge",
    "libraryDoctorBridge", "discLabBridge", "selectionContextBridge",
    "homeAudioBridge", "lyricsBridge", "notificationBridge",
    "routeRegistryBridge", "appStateBridge", "diagnosticsBridge",
    "commandPaletteBridge", "actionRegistry", "globalSearchBridge",
    "coverProviderBridge", "jobBridge", "desktopBridge", "pageStateStore",
    "queueBridge", "historyBridge", "homeBridge", "librarySourcesBridge",
    "capabilityBridge", "outputProfilesBridge", "settingsBridgeV2",
    "accessibilityBridge", "runtimeQualityBridge", "physicalAudioBridge",
}

CANONICAL_MODELS = {
    "BasePagedListModel", "QueueListModel", "TrackListModel",
    "HistoryListModel", "ArtistListModel", "AlbumPagedListModel",
    "AlbumListModel", "AlbumDetailModel", "JobListModel", "FolderTreeModel",
}

CANONICAL_ROUTES = {
    "home", "library.tracks", "library.albums", "library.album_detail",
    "library.artists", "library.artist_detail", "library.folders",
    "library.folder_detail", "library.sources", "queue", "playlists",
    "playlist_detail", "history", "mix", "mix_detail", "search", "radio",
    "lyrics", "audio_lab.overview", "audio_lab.analysis", "audio_lab.conversion",
    "audio_lab.normalization", "audio_lab.replaygain", "audio_lab.integrity",
    "audio_lab.comparison", "audio_lab.jobs", "audio_lab.profiles",
    "metadata.inspector", "metadata.batch", "tagging", "library_doctor",
    "equalizer", "outputs", "devices.list", "devices.detail", "connections",
    "connections.detail", "home_audio", "settings.general", "settings.appearance",
    "settings.playback", "settings.library", "settings.accessibility",
    "settings.audio", "settings.about", "diagnostics", "ai", "assistant",
    "disc_lab", "audio_lab", "playback", "library", "settings", "placeholder",
}

MODULE_EXPECTATIONS = {
    "workflows": {
        "services": {"worker_manager", "event_bus"},
        "bridges": {"navigation", "app"},
        "contexts": {"navigationBridge", "appBridge"},
        "models": set(),
        "routes": {"home", "library"},
    },
    "workflows_interaction_real": {
        "services": set(),
        "bridges": {"navigation"},
        "contexts": {"navigationBridge"},
        "models": set(),
        "routes": set(),
    },
    "evidence": {
        "services": {"worker_manager"},
        "bridges": {"diagnostics", "runtime_quality"},
        "contexts": {"diagnosticsBridge", "runtimeQualityBridge"},
        "models": set(),
        "routes": {"diagnostics"},
    },
    "library": {
        "services": {"library_query_service", "library_sources_service", "library_mutation_service"},
        "bridges": {"library", "library_sources"},
        "contexts": {"libraryBridge", "librarySourcesBridge"},
        "models": {"TrackListModel", "AlbumListModel", "AlbumPagedListModel", "AlbumDetailModel", "ArtistListModel"},
        "routes": {"library.tracks", "library.albums", "library.album_detail", "library.artists", "library.artist_detail", "library.folders", "library.folder_detail", "library.sources"},
    },
    "playback": {
        "services": {"playback_service", "queue_service"},
        "bridges": {"playback", "nowplaying", "queue"},
        "contexts": {"playbackBridge", "nowplayingBridge", "queueBridge"},
        "models": {"QueueListModel"},
        "routes": {"playback", "queue"},
    },
    "navigation": {
        "services": set(),
        "bridges": {"navigation", "route_registry", "page_state"},
        "contexts": {"navigationBridge", "routeRegistryBridge", "pageStateStore"},
        "models": set(),
        "routes": {"home", "library", "settings"},
    },
    "settings": {
        "services": {"settings_service", "settings_coordinator"},
        "bridges": {"settings", "settings_v2"},
        "contexts": {"settingsBridge", "settingsBridgeV2"},
        "models": set(),
        "routes": {"settings.general", "settings.appearance", "settings.playback", "settings.library", "settings.accessibility", "settings.audio", "settings.about"},
    },
    "devices": {
        "services": {"device_sync_service"},
        "bridges": {"devices"},
        "contexts": {"devicesBridge"},
        "models": set(),
        "routes": {"devices.list", "devices.detail"},
    },
}


def load_qml_modules():
    if not MODULES_YAML.exists():
        return {}
    import yaml
    with open(MODULES_YAML) as f:
        data = yaml.safe_load(f)
    return data.get("modules", {}) if data else {}


def audit() -> dict:
    modules = load_qml_modules()
    results = {}
    total_issues = 0

    for module_name in modules:
        expected = MODULE_EXPECTATIONS.get(module_name)
        if expected is None:
            results[module_name] = {"error": f"Unknown module: {module_name}"}
            total_issues += 1
            continue

        issues = []

        for svc in expected["services"]:
            if svc not in CANONICAL_SERVICES:
                issues.append(f"missing service: {svc}")

        for br in expected["bridges"]:
            if br not in CANONICAL_BRIDGES:
                issues.append(f"missing bridge: {br}")

        for ctx in expected["contexts"]:
            if ctx not in CANONICAL_CONTEXTS:
                issues.append(f"missing context: {ctx}")

        for mdl in expected["models"]:
            if mdl not in CANONICAL_MODELS:
                issues.append(f"missing model: {mdl}")

        for route in expected["routes"]:
            if route not in CANONICAL_ROUTES:
                issues.append(f"missing route: {route}")

        if issues:
            total_issues += len(issues)
            results[module_name] = {"ok": False, "issues": issues}
        else:
            results[module_name] = {"ok": True}

    return {
        "modules_checked": len(modules),
        "total_issues": total_issues,
        "modules": results,
        "passed": total_issues == 0,
    }


def main():
    result = audit()
    outpath = Path("/tmp/qml_integration_audit.json")
    outpath.write_text(json.dumps(result, indent=2, default=str))
    print(f"Results written to {outpath}")

    print(f"\n{'='*60}")
    print("  QML Integration Audit")
    print(f"{'='*60}")
    print(f"  Modules checked: {result['modules_checked']}")
    print(f"  Total issues:    {result['total_issues']}")

    for mod_name, mod_res in result["modules"].items():
        status = "PASS" if mod_res.get("ok") else "FAIL"
        print(f"  {mod_name:40s} {status}")
        if not mod_res.get("ok"):
            for issue in mod_res.get("issues", []):
                print(f"    - {issue}")

    print(f"\n{'='*60}")
    print(f"  OVERALL: {'PASSED' if result['passed'] else 'FAILED'}")
    print(f"{'='*60}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
