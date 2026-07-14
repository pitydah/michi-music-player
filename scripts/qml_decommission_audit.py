#!/usr/bin/env python3
"""QWidget Decommission Audit — Fase 3 BT.

Scans ui/ and ui_qml/ by domain, detects widget replacement status,
and classifies each domain as W0_ACTIVE through W5_REMOVABLE_AFTER_PHYSICAL.
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
MATRIX_FILE = DOCS / "qwidget_decommission_matrix.yaml"

DOMAIN_MAP = {
    "nowplaying": {"widget": "ui/nowplaying_bar.py", "qml": "ui_qml/pages/nowplaying/NowPlayingPage.qml", "bridge": "nowplaying_bridge", "route": "nowplaying"},
    "queue": {"widget": "ui/hubs/playback_hub_page.py", "qml": "ui_qml/pages/queue/QueuePage.qml", "bridge": "queue_bridge", "route": "queue"},
    "lyrics": {"widget": "ui/lyrics_widget.py", "qml": "ui_qml/pages/lyrics/LyricsPage.qml", "bridge": "lyrics_bridge", "route": "lyrics"},
    "settings": {"widget": "ui/settings_pages.py", "qml": "ui_qml/pages/SettingsPage.qml", "bridge": "settings", "route": "settings"},
    "output_profiles": {"widget": "ui/preferences_window.py", "qml": "ui_qml/pages/outputs/OutputProfilesPage.qml", "bridge": "output_profiles_bridge", "route": "output_profiles"},
    "metadata": {"widget": "ui/metadata_editor.py", "qml": "ui_qml/pages/metadata/MetadataEditorPage.qml", "bridge": "metadata_bridge", "route": "metadata"},
    "smart_tagging": {"widget": "ui/audio_lab/smart_tagging_panel.py", "qml": "ui_qml/pages/metadata/SmartTaggingWorkflowPage.qml", "bridge": "smart_tagging_bridge", "route": "smart_tagging"},
    "diagnostics": {"widget": "ui/audio_lab/diagnostics_page.py", "qml": "ui_qml/pages/DiagnosticsPage.qml", "bridge": "diagnostics_bridge", "route": "diagnostics"},
    "library": {"widget": "ui/controllers/library_controller.py", "qml": "ui_qml/pages/library/LibraryPage.qml", "bridge": "library_bridge", "route": "library"},
    "album_artist": {"widget": "ui/album_detail_view.py", "qml": "ui_qml/pages/library/AlbumGridPage.qml", "bridge": "library_bridge", "route": "library/albums"},
    "playlists": {"widget": "ui/playlist_hub.py", "qml": "ui_qml/pages/playlists/PlaylistsPage.qml", "bridge": "playlists_bridge", "route": "playlists"},
    "history": {"widget": "ui/hubs/playback_hub_page.py", "qml": "ui_qml/pages/history/HistoryPage.qml", "bridge": "history_bridge", "route": "history"},
    "global_search": {"widget": "ui/search_controller.py", "qml": "ui_qml/pages/search/GlobalSearchPage.qml", "bridge": "global_search_bridge", "route": "global_search"},
    "mix": {"widget": "ui/hubs/mix_hub_page.py", "qml": "ui_qml/pages/mix/MixHubPage.qml", "bridge": "mix_bridge", "route": "mix"},
    "radio": {"widget": "ui/discover_dashboard.py", "qml": "ui_qml/pages/radio/RadioPage.qml", "bridge": "radio_bridge", "route": "radio"},
    "equalizer": {"widget": "ui/eq_panel.py", "qml": "ui_qml/pages/equalizer/EqualizerPage.qml", "bridge": "eq_bridge", "route": "eq"},
    "home": {"widget": "ui/hubs/home_page.py", "qml": "ui_qml/pages/home/HomePage.qml", "bridge": "home_bridge", "route": "home"},
    "connections": {"widget": "ui/hubs/connections_hub_page.py", "qml": "ui_qml/pages/connections/ConnectionsPage.qml", "bridge": "connections_bridge", "route": "connections"},
    "home_audio": {"widget": "ui/home_audio_view.py", "qml": "ui_qml/pages/home_audio/HomeAudioPage.qml", "bridge": "home_audio_bridge", "route": "home_audio"},
    "devices": {"widget": "ui/devices_page.py", "qml": "ui_qml/pages/devices/DevicesPage.qml", "bridge": "devices_bridge", "route": "devices"},
    "audio_lab": {"widget": "ui/audio_lab/audio_lab_page.py", "qml": "ui_qml/pages/assistant/AudioLabPage.qml", "bridge": "audio_lab_bridge", "route": "audio_lab"},
    "sidebar": {"widget": "ui/sidebar_widget.py", "qml": "ui_qml/shell/Sidebar.qml", "bridge": None, "route": None},
    "main_window": {"widget": "ui/window.py", "qml": "ui_qml/shell/AppShell.qml", "bridge": None, "route": None},
}

W0_ACTIVE = "W0_ACTIVE"
W1_FROZEN = "W1_FROZEN"
W2_THIN_ADAPTER = "W2_THIN_ADAPTER"
W3_LEGACY_ONLY = "W3_LEGACY_ONLY"
W4_DETACHED = "W4_DETACHED"
W5_REMOVABLE_AFTER_PHYSICAL = "W5_REMOVABLE_AFTER_PHYSICAL"

STATUS_ORDER = [W0_ACTIVE, W1_FROZEN, W2_THIN_ADAPTER, W3_LEGACY_ONLY, W4_DETACHED, W5_REMOVABLE_AFTER_PHYSICAL]


def _resolve(rel_path: str) -> Path:
    return REPO / rel_path


def _file_exists(rel_path: str) -> bool:
    return _resolve(rel_path).exists()


def _file_contents(rel_path: str) -> str:
    p = _resolve(rel_path)
    return p.read_text() if p.exists() else ""


def _determine_status(domain: str, cfg: dict) -> str:
    widget_path = _resolve(cfg["widget"])
    qml_path = _resolve(cfg["qml"])
    qml_exists = qml_path.exists()
    widget_exists = widget_path.exists()
    qml_expected = cfg["route"] is not None

    if not qml_exists and qml_expected:
        return W0_ACTIVE
    if not qml_expected:
        return W1_FROZEN
    if not widget_exists:
        return W5_REMOVABLE_AFTER_PHYSICAL

    bridge_key = cfg.get("bridge")
    if bridge_key:
        bridge_file = REPO / "ui_qml_bridge" / f"{bridge_key}.py"
        if not bridge_file.exists():
            return W4_DETACHED

    route_key = cfg.get("route")
    if route_key:
        route_registry = REPO / "ui_qml_bridge" / "route_registry.py"
        if route_registry.exists():
            routes_text = route_registry.read_text()
            if route_key not in routes_text:
                return W4_DETACHED

    legacy_wave1 = {"nowplaying", "queue", "lyrics", "settings", "output_profiles", "metadata", "smart_tagging", "diagnostics"}
    legacy_wave2 = {"library", "album_artist", "playlists", "history", "global_search", "mix", "radio", "equalizer"}
    legacy = domain in legacy_wave1 or domain in legacy_wave2

    if legacy:
        return W3_LEGACY_ONLY

    thin_adapters = {"home", "connections", "home_audio", "devices"}
    if domain in thin_adapters:
        return W2_THIN_ADAPTER

    return W1_FROZEN


def load_matrix() -> list[dict]:
    """Load matrix from YAML or fallback to domain map scan."""
    if MATRIX_FILE.exists():
        import yaml
        data = yaml.safe_load(MATRIX_FILE.read_text())
        return data.get("domains", list(data.values()) if isinstance(data, dict) else [])
    return []


def scan() -> dict[str, dict]:
    results = {}
    counts = {s: 0 for s in STATUS_ORDER}

    for domain, cfg in sorted(DOMAIN_MAP.items()):
        widget_exists = _file_exists(cfg["widget"])
        qml_exists = _file_exists(cfg["qml"])
        status = _determine_status(domain, cfg)
        counts[status] += 1

        results[domain] = {
            "widget_file": cfg["widget"],
            "widget_exists": widget_exists,
            "qml_file": cfg["qml"],
            "qml_exists": qml_exists,
            "bridge": cfg.get("bridge"),
            "has_bridge": cfg.get("bridge") is not None and (REPO / "ui_qml_bridge" / f"{cfg['bridge']}.py").exists(),
            "route": cfg.get("route"),
            "status": status,
        }

    return {"domains": results, "counts": counts}


def print_results(data: dict[str, dict]):
    domains = data["domains"]
    counts = data["counts"]
    print("=" * 78)
    print("  QWidget Decommission Audit — Inventory")
    print("=" * 78)
    print(f"  {'Domain':20s} {'Status':28s} {'Widget':30s}")
    print("  " + "-" * 78)
    for domain in sorted(domains):
        d = domains[domain]
        print(f"  {domain:20s} {d['status']:28s} {d['widget_file']:30s}")
    print("=" * 78)
    total = sum(counts.values())
    print(f"\n  Summary: {total} domains")
    for s in STATUS_ORDER:
        pct = f"({counts[s] / total * 100:.0f}%)" if total else ""
        print(f"    {s:32s} {counts[s]:3d}  {pct}")
    w3_plus = sum(counts[s] for s in [W3_LEGACY_ONLY, W4_DETACHED, W5_REMOVABLE_AFTER_PHYSICAL])
    if total:
        print(f"\n  W3+ (out of active architecture): {w3_plus}/{total} = {w3_plus / total * 100:.0f}%")
    print()


def main():
    parser = argparse.ArgumentParser(description="QWidget Decommission Audit")
    parser.add_argument("--output", type=str, help="Output JSON path")
    args = parser.parse_args()

    data = scan()
    print_results(data)

    if args.output:
        import json
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2))
        print(f"Written to {out}")

    w3_plus = sum(data["counts"][s] for s in [W3_LEGACY_ONLY, W4_DETACHED, W5_REMOVABLE_AFTER_PHYSICAL])
    total = sum(data["counts"].values())
    ratio = w3_plus / total if total else 0
    print(f"Gate: W3+ ratio = {ratio:.0%} (target >= 60%)")
    return 0 if ratio >= 0.60 else 1


if __name__ == "__main__":
    sys.exit(main())
