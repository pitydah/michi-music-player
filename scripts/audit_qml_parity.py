#!/usr/bin/env python3
"""Audit QML page parity: route, page, bridge, states, test coverage."""
import json
import re
import sys
from pathlib import Path

UI_QML = Path(__file__).resolve().parent.parent / "ui_qml"
PAGES_DIR = UI_QML / "pages"
BRIDGE_DIR = Path(__file__).resolve().parent.parent / "ui_qml_bridge"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

ROUTES = {
    "home": "pages/home/HomePage.qml",
    "library": "pages/library/LibraryPage.qml",
    "mix": "pages/mix/MixHubPage.qml",
    "playback": "pages/PlaybackPage.qml",
    "connections": "pages/connections/ConnectionsPage.qml",
    "radio": "pages/radio/RadioPage.qml",
    "playlists": "pages/playlists/PlaylistsPage.qml",
    "home_audio": "pages/home_audio/HomeAudioPage.qml",
    "assistant": "pages/assistant/AssistantPage.qml",
    "audio_lab": "pages/audio_lab/AudioLabOverviewPage.qml",
    "settings": "pages/SettingsPage.qml",
    "devices": "pages/devices/DevicesPage.qml",
    "eq": "pages/EqPage.qml",
    "diagnostics": "pages/DiagnosticsPage.qml",
    "nowplaying": "pages/nowplaying/NowPlayingPage.qml",
    "queue": "pages/queue/QueuePage.qml",
    "history": "pages/history/HistoryPage.qml",
    "library_doctor": "pages/library_doctor/LibraryDoctorPage.qml",
}


def check_page_states(qml_path):
    if not qml_path.exists():
        return {"status": "MISSING", "states": [], "bridge": None, "issues": ["File not found"]}

    content = qml_path.read_text()
    states = []
    bridge = None
    issues = []

    if re.search(r'\bstate(?:Loading|Ready|Error|Empty|Unavailable|Degraded)\b', content):
        states.append("has_states")
    if re.search(r'\bstateLoading\b', content) or "LOADING" in content:
        states.append("loading")
    if re.search(r'\bstateReady\b', content) or "READY" in content:
        states.append("ready")
    if re.search(r'\bstateError\b', content) or "ERROR" in content:
        states.append("error")
    if re.search(r'\bstateEmpty\b', content) or "EMPTY" in content:
        states.append("empty")
    if re.search(r'\bstateUnavailable\b', content) or "UNAVAILABLE" in content:
        states.append("unavailable")
    if re.search(r'\bstateDegraded\b', content) or "DEGRADED" in content:
        states.append("degraded")

    bridge_match = re.search(r'(?:property\s+var\s+(\w+Bridge)|(\w+bridge))', content)
    if bridge_match:
        bridge = bridge_match.group(1) or bridge_match.group(2)

    has_empty = "EmptyState" in content or "stateEmpty" in content or "EMPTY" in content
    has_error = "ErrorState" in content or "stateError" in content or "ERROR" in content
    has_loading = "LoadingState" in content or "stateLoading" in content or "BusyIndicator" in content or "LOADING" in content

    if not has_empty:
        issues.append("No empty state")
    if not has_error:
        issues.append("No error state")
    if not has_loading:
        issues.append("No loading state")

    return {"status": "FUNCTIONAL" if states else "SHELL", "states": states, "bridge": bridge, "issues": issues}


def main():
    report = []
    for route, page_path in sorted(ROUTES.items()):
        qml_path = PROJECT_ROOT / "ui_qml" / page_path
        info = check_page_states(qml_path)
        report.append({
            "route": route,
            "page": page_path,
            "file_exists": qml_path.exists(),
            **info,
        })

    print(json.dumps(report, indent=2))

    total = len(report)
    functional = sum(1 for r in report if r["status"] == "FUNCTIONAL")
    missing = sum(1 for r in report if r["status"] == "MISSING")
    shell = sum(1 for r in report if r["status"] == "SHELL")

    print(f"\nSummary: {total} routes, {functional} functional, {shell} shell, {missing} missing")

    if shell > 0 or missing > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
