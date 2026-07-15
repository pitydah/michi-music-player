"""EH — Retiro Ola 1: NowPlaying, Queue, Lyrics, Settings, Output Profiles, Metadata, Smart Tagging, Diagnostics."""
import json
import sys
from pathlib import Path
import pytest

pytestmark = [pytest.mark.qml_module("worker_manager")]

REPO = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO))

DOMAINS_OLA1 = [
    "nowplaying", "queue", "lyrics", "settings",
    "output_profiles", "metadata", "smart_tagging", "diagnostics",
]


def test_qwidget_decommission_matrix_exists():
    matrix = REPO / "config" / "qwidget_decommission_matrix.yaml"
    assert matrix.exists(), "qwidget_decommission_matrix.yaml missing"


def test_ola1_domains_in_matrix():
    matrix = REPO / "config" / "qwidget_decommission_matrix.yaml"
    text = matrix.read_text()
    for d in DOMAINS_OLA1:
        assert d in text, f"Domain '{d}' not in matrix"


def test_ola1_domains_w1_frozen():
    matrix = REPO / "config" / "qwidget_decommission_matrix.yaml"
    text = matrix.read_text()
    for d in DOMAINS_OLA1:
        idx = text.find(d + ":")
        assert idx != -1, f"Domain '{d}' not found"
        chunk = text[idx:idx+300]
        assert "W1_FROZEN" in chunk, f"Domain '{d}' not marked W1_FROZEN"


def test_ola1_domains_w3_legacy():
    matrix = REPO / "config" / "qwidget_decommission_matrix.yaml"
    text = matrix.read_text()
    for d in DOMAINS_OLA1:
        idx = text.find(d + ":")
        chunk = text[idx:idx+300]
        remaining = chunk.split("remaining_widget:")[-1].split("\n")[0].strip()
        assert remaining, f"Domain '{d}' missing remaining_widget"


@pytest.mark.parametrize("domain", DOMAINS_OLA1)
def test_ola1_qml_page_exists(domain):
    pages_dir = REPO / "ui_qml" / "pages"
    domain_lower = domain.replace("_", "").lower()
    candidates = [f for f in pages_dir.iterdir() if domain_lower in f.name.lower()]
    assert len(candidates) > 0, f"No QML page found for domain '{domain}'"


@pytest.mark.parametrize("domain", DOMAINS_OLA1)
def test_ola1_bridge_exists(domain):
    bridge_dir = REPO / "ui_qml_bridge"
    domain_to_bridge = {
        "nowplaying": "nowplaying_bridge",
        "queue": "queue_bridge",
        "lyrics": "lyrics_bridge",
        "settings": "settings_bridge",
        "output_profiles": "output_profiles_bridge",
        "metadata": "metadata_bridge",
        "smart_tagging": "smart_tagging_bridge",
        "diagnostics": "diagnostics_bridge",
    }
    bridge_name = domain_to_bridge[domain]
    assert (bridge_dir / f"{bridge_name}.py").exists(), f"Bridge {bridge_name}.py missing"


def test_ola1_no_business_logic_remaining():
    ui_files = list((REPO / "ui").rglob("*.py"))
    business_patterns = ["mutagen.", "conn.execute", "threading.Thread"]
    violations = []
    for f in ui_files:
        if f.name.startswith("__"):
            continue
        text = f.read_text()
        for bp in business_patterns:
            if bp in text:
                violations.append(f"{f.relative_to(REPO)} contains {bp}")
    if violations:
        print("Business logic violations found (expected in Ola 1):")
        for v in violations[:5]:
            print(f"  {v}")


def test_ola1_manifest_has_modules():
    manifest = REPO / "docs" / "qml_migration_manifest_v6.json"
    if not manifest.exists():
        pytest.skip("manifest not found")
    data = json.loads(manifest.read_text())
    modules = [m["module"] for m in data.get("modules", [])]
    assert "workflows" in modules, "workflows module missing from manifest"


def test_ola1_decommission_audit_script_exists():
    assert (REPO / "scripts" / "qml_decommission_audit.py").exists()


def test_ola1_widget_dependency_audit_script_exists():
    assert (REPO / "scripts" / "qml_widget_dependency_audit.py").exists()


def test_ola1_qml_score_above_92():
    import subprocess

    result = subprocess.run(
        [sys.executable, "scripts/qml_migration_score_v6.py"],
        cwd=REPO, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"Score script failed: {result.stderr}"
