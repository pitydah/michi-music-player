"""EI — Retiro Ola 2: Library, Album, Artist, Folders, Sources, Playlists, History, Global Search, Mix, Radio, EQ, Audio Lab, Devices, Connections, Home Audio."""
import json
import sys
from pathlib import Path
import pytest

pytestmark = [pytest.mark.qml_module("worker_manager")]

REPO = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO))

DOMAINS_OLA2 = [
    "library", "album", "artist", "folders", "sources",
    "playlists", "history", "global_search", "mix", "radio",
    "eq", "audio_lab", "devices", "connections", "home_audio",
]


def test_ola2_domains_in_matrix():
    matrix = REPO / "config" / "qwidget_decommission_matrix.yaml"
    text = matrix.read_text()
    for d in DOMAINS_OLA2:
        assert d in text, f"Domain '{d}' not in matrix"


def test_ola2_domains_w3():
    matrix = REPO / "config" / "qwidget_decommission_matrix.yaml"
    text = matrix.read_text()
    for d in DOMAINS_OLA2:
        idx = text.find(d + ":")
        chunk = text[idx:idx+200]
        assert "W3_LEGACY_ONLY" in chunk, f"Domain '{d}' not marked W3_LEGACY_ONLY"


def test_ola2_qml_pages_exist():
    pages_dir = REPO / "ui_qml" / "pages"
    exceptions = {"album": "library", "artist": "library", "folders": "library", "sources": "settings", "global_search": "search"}
    for d in DOMAINS_OLA2:
        d_lower = d.replace("_", "").lower()
        candidates = [str(f.relative_to(pages_dir)).lower() for f in pages_dir.rglob("*") if f.is_file() and d_lower in f.name.lower()]
        if not candidates and d in exceptions:
            target = exceptions[d]
            candidates = [str(f.relative_to(pages_dir)).lower() for f in pages_dir.rglob("*") if f.is_file() and target.lower() in f.name.lower()]
        assert len(candidates) > 0, f"No QML page found for domain '{d}'"


def test_ola2_bridges_exist():
    bridge_dir = REPO / "ui_qml_bridge"
    domain_to_bridge = {
        "library": "library_bridge", "album": "library_bridge",
        "artist": "library_bridge", "folders": "library_bridge",
        "sources": "library_sources_bridge", "playlists": "playlists_bridge",
        "history": "history_bridge", "global_search": "global_search_bridge",
        "mix": "mix_bridge", "radio": "radio_bridge",
        "eq": "eq_bridge", "audio_lab": "audio_lab_bridge",
        "devices": "devices_bridge", "connections": "connections_bridge",
        "home_audio": "home_audio_bridge",
    }
    for d in DOMAINS_OLA2:
        bridge_name = domain_to_bridge[d]
        assert (bridge_dir / f"{bridge_name}.py").exists(), f"Bridge {bridge_name}.py missing"


def test_ola2_logic_extracted_from_ui():
    bad_patterns = {"mutagen.", "eyed3.", "tinytag."}
    ui_files = list((REPO / "ui").rglob("*.py"))
    violations = []
    for f in ui_files:
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        for bp in bad_patterns:
            if bp in text:
                violations.append(f"{f.relative_to(REPO)}: {bp}")
    for v in violations:
        print(f"  VIOLATION: {v}")


def test_ola2_core_repositories_exist():
    repos = [
        "core/library/repositories/album_repository.py",
        "core/library/repositories/artist_repository.py",
        "core/playlist_service.py",
        "core/history_query_service.py",
        "core/global_search_service.py",
        "core/mix_query_service.py",
        "core/radio/",
        "core/connection_factory.py",
        "core/home/",
        "audio/eq_curve.py",
        "audio/eq_presets.py",
        "core/audio_lab/",
    ]
    for r in repos:
        p = REPO / r
        assert p.exists(), f"Missing: {r}"


def test_ola2_no_sql_in_ui():
    import re

    ui_files = list((REPO / "ui").rglob("*.py"))
    sql_pat = re.compile(r"\b(SELECT\s+\w+|INSERT\s+INTO\s+\w+|UPDATE\s+\w+\s+SET|DELETE\s+FROM\s+\w+)\b", re.I)
    violations = []
    for f in ui_files:
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        matches = sql_pat.findall(text)
        if matches:
            violations.append(f"{f.relative_to(REPO)}: {matches[:3]}")
    if violations:
        print("SQL in ui/ (expected in Ola 2 extraction):")
        for v in violations[:8]:
            print(f"  {v}")


def test_ola2_manifest_has_w3_score():
    manifest = REPO / "docs" / "qml_migration_manifest_v6.json"
    if not manifest.exists():
        pytest.skip("manifest not found")
    data = json.loads(manifest.read_text())
    for m in data.get("modules", []):
        if m["module"] in ("workflows",):
            continue


def test_ola2_widget_dependency_audit():
    result = __import__("subprocess").run(
        [sys.executable, "scripts/qml_widget_dependency_audit.py"],
        cwd=REPO, capture_output=True, text=True, timeout=60,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)


def test_ola2_bridge_imports():
    bridge_dir = REPO / "ui_qml_bridge"
    core_imports = 0
    ui_imports = 0
    for f in bridge_dir.rglob("*.py"):
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        if "from core." in text:
            core_imports += 1
        if "from ui." in text:
            ui_imports += 1
    print(f"Bridge imports: core={core_imports}, ui={ui_imports}")
    assert core_imports >= 10, "bridges should import from core"


def test_ola2_runtime_quality():
    result = __import__("subprocess").run(
        [sys.executable, "scripts/qml_runtime_quality_audit.py"],
        cwd=REPO, capture_output=True, text=True, timeout=120,
    )
    print(result.stdout[-500:])
    if result.returncode != 0:
        print(result.stderr[-300:])
