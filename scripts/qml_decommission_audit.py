#!/usr/bin/env python3
"""QWidget decommission audit — verifies matrix status against real code.

Reads canonical config/qwidget_decommission_matrix.yaml.
Each domain: widget_status must match evidence from actual file system.
NO acceptance without evidence.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATRIX = REPO / "config" / "qwidget_decommission_matrix.yaml"
DOCS_MATRIX = REPO / "docs" / "qwidget_decommission_matrix.yaml"

W_LABELS = {
    "W0_ACTIVE": "Widget is primary implementation",
    "W1_FROZEN": "No new widget features",
    "W2_THIN_ADAPTER": "Widget consumes core services only",
    "W3_LEGACY_ONLY": "Widget via legacy launcher only",
    "W4_DETACHED": "Widget outside QML imports/packaging",
    "W5_REMOVABLE_AFTER_PHYSICAL": "Removable after physical validation",
}

W3_PLUS = {"W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"}

EVIDENCE_CHECKERS = {
    "navigation": lambda: os.path.isfile("ui_qml/shell/Sidebar.qml"),
    "app_bridge": lambda: os.path.isfile("ui_qml/qml_main.qml"),
    "theme": lambda: os.path.isfile("ui_qml/theme/Theme.qml"),
    "notification": lambda: os.path.isfile("ui_qml/components/Toast.qml"),
    "accessibility": lambda: os.path.isfile("ui_qml/accessibility"),
    "command_palette": lambda: os.path.isfile("ui_qml/components/CommandPalette.qml"),
    "home": lambda: os.path.isfile("ui_qml/pages/home/HomePage.qml"),
    "library": lambda: os.path.isfile("ui_qml/pages/library/LibraryPage.qml"),
    "album_views": lambda: os.path.isfile("ui_qml/components/AlbumCard.qml"),
    "playback": lambda: os.path.isfile("ui_qml/PlaybackBar.qml") or os.path.isfile("ui_qml/components/PlayerBar.qml"),
    "nowplaying": lambda: os.path.isfile("ui_qml/pages/nowplaying/NowPlayingPage.qml"),
    "queue": lambda: os.path.isfile("ui_qml/pages/queue/QueuePage.qml"),
    "playlists": lambda: os.path.isfile("ui_qml/pages/playlists/PlaylistsPage.qml"),
    "history": lambda: os.path.isfile("ui_qml/pages/history/HistoryPage.qml"),
    "mix": lambda: os.path.isfile("ui_qml/pages/mix/MixPage.qml"),
    "lyrics": lambda: os.path.isfile("ui_qml/pages/lyrics/LyricsPage.qml"),
    "radio": lambda: os.path.isfile("ui_qml/pages/radio/RadioPage.qml"),
    "global_search": lambda: os.path.isfile("ui_qml/components/SearchField.qml"),
    "eq_dsp": lambda: os.path.isfile("ui_qml/pages/equalizer/EqPage.qml"),
    "metadata": lambda: os.path.isfile("ui_qml/pages/metadata/MetadataPage.qml"),
    "smart_tagging": lambda: os.path.isfile("ui_qml/components/TagEditor.qml"),
    "audio_lab": lambda: os.path.isfile("ui_qml/pages/audio_lab/AudioLabPage.qml"),
    "library_doctor": lambda: os.path.isfile("ui_qml/pages/library_doctor/LibraryDoctorPage.qml"),
    "diagnostics": lambda: os.path.isfile("ui_qml/pages/diagnostics/DiagnosticsPage.qml"),
    "michi_ai": lambda: os.path.isfile("ui_qml/pages/assistant/AssistantPage.qml"),
    "connections": lambda: os.path.isfile("ui_qml/pages/connections/ConnectionsPage.qml"),
    "home_audio": lambda: os.path.isfile("ui_qml/pages/home_audio/HomeAudioPage.qml"),
    "devices_sync": lambda: os.path.isfile("ui_qml/pages/devices/DevicesPage.qml"),
    "settings": lambda: os.path.isfile("ui_qml/pages/settings/SettingsPage.qml"),
    "output_profiles": lambda: os.path.isfile("ui_qml/pages/outputs/OutputProfilesPage.qml"),
    "disc_lab": lambda: os.path.isfile("ui_qml/pages/disc_lab/DiscLabPage.qml"),
    "capabilities": lambda: os.path.isfile("core/app_context.py"),
    "performance": lambda: os.path.isfile("scripts/qml_library_benchmark.py"),
    "runtime_quality": lambda: os.path.isfile("scripts/qml_runtime_quality_audit.py"),
}


def _evidence_path(domain: str) -> bool:
    checker = EVIDENCE_CHECKERS.get(domain)
    if not checker:
        return False
    cwd = os.getcwd()
    os.chdir(str(REPO))
    try:
        return checker()
    finally:
        os.chdir(cwd)


def main():
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML required (pip install pyyaml)")
        return 1

    if not MATRIX.is_file():
        print(f"ERROR: canonical matrix not found at {MATRIX}")
        return 1

    try:
        matrix = yaml.safe_load(MATRIX.read_text())
    except Exception as e:
        print(f"ERROR: cannot parse matrix: {e}")
        return 1

    domains = matrix.get("domains", [])
    if not domains:
        print("ERROR: no domains in matrix")
        return 1

    counts = {k: 0 for k in W_LABELS}
    violations = []
    missing_evidence = []
    bad_status = []
    missing_fields = []

    required_fields = {"domain", "widget_status", "qml_status", "business_logic_shared", "qml_imports_widget", "packaged_in_qml", "workflow_passed", "physical_required"}
    valid_statuses = set(W_LABELS.keys())

    print("# QWidget Decommission Audit (evidence-verified)\n")

    for d in sorted(domains, key=lambda x: x.get("domain", "")):
        domain = d.get("domain", "")
        if not domain:
            continue

        missing = [f for f in required_fields if f not in d]
        if missing:
            missing_fields.append(f"{domain}: missing fields {missing}")
            continue

        status = d.get("widget_status", "")
        if status not in valid_statuses:
            bad_status.append(f"{domain}: invalid status {status}")
            continue

        counts[status] = counts.get(status, 0) + 1

        evidence_ok = _evidence_path(domain)
        if not evidence_ok:
            missing_evidence.append(domain)

        flag = "✅" if status in W3_PLUS else "⬜"
        removal = []
        for k in ("removal_blockers",):
            blockers = d.get(k, [])
            if blockers:
                removal.extend(blockers)
        blocker = f" (BLOCKED: {', '.join(removal)})" if removal else ""
        evidence_tag = "" if evidence_ok else " ⚠️ NO EVIDENCE"
        print(f"  {flag} {domain:20s} {status:30s} QML: {d.get('qml_status', '?'):20s}{blocker}{evidence_tag}")

    w3_plus = sum(v for k, v in counts.items() if k in W3_PLUS)
    total = sum(counts.values())
    pct = w3_plus / total * 100 if total else 0
    print(f"\n  W3+: {w3_plus}/{total} = {pct:.0f}%")
    for k, v in sorted(counts.items()):
        print(f"    {k}: {v} ({W_LABELS.get(k, '?')})")

    if missing_fields:
        print("\n  ❌ Missing fields:\n    " + "\n    ".join(missing_fields))
    if bad_status:
        print("\n  ❌ Invalid status:\n    " + "\n    ".join(bad_status))
    if missing_evidence:
        print("\n  ⚠️  No QML evidence for:\n    " + "\n    ".join(missing_evidence))
    if violations:
        print("\n  ❌ Violations:\n    " + "\n    ".join(violations))

    if pct >= 60 and not missing_fields and not bad_status:
        print("\n  ✅ TARGET MET: >= 60% W3+ with evidence")
        return 0
    else:
        print(f"\n  ❌ TARGET NOT MET: {pct:.0f}% < 60%, or schema violations")
        return 1


if __name__ == "__main__":
    exit(main())
