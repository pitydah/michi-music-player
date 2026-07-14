"""Tests for qml_decommission_audit.py — QWidget decommission matrix audit."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "scripts" / "qml_decommission_audit.py"
MATRIX = REPO / "docs" / "qwidget_decommission_matrix.yaml"


@pytest.fixture
def audit_result():
    """Run the decommission audit script and capture JSON output."""
    out = REPO / "artifacts" / ".test_decommission_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(out)],
        cwd=REPO, capture_output=True, text=True, timeout=30,
    )
    data = json.loads(out.read_text()) if out.exists() else {}
    out.unlink(missing_ok=True)
    return data, result


class TestDecommissionAuditScript:
    def test_script_executes(self, audit_result):
        data, result = audit_result
        assert result.returncode in (0, 1), f"Script failed: {result.stderr}"
        assert "domains" in data, "Missing 'domains' key in output"

    def test_all_domains_covered(self, audit_result):
        data, _ = audit_result
        domains = data.get("domains", {})
        expected = {"nowplaying", "queue", "lyrics", "settings", "output_profiles",
                    "metadata", "smart_tagging", "diagnostics", "library",
                    "album_artist", "playlists", "history", "global_search",
                    "mix", "radio", "equalizer", "home", "connections",
                    "home_audio", "devices", "audio_lab", "sidebar", "main_window"}
        missing = expected - set(domains.keys())
        assert not missing, f"Missing domains: {missing}"

    def test_status_is_valid(self, audit_result):
        data, _ = audit_result
        valid = {"W0_ACTIVE", "W1_FROZEN", "W2_THIN_ADAPTER", "W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"}
        for domain, info in data.get("domains", {}).items():
            assert info["status"] in valid, f"{domain}: invalid status {info['status']}"

    def test_counts_sum_to_domains(self, audit_result):
        data, _ = audit_result
        counts = data.get("counts", {})
        total = sum(counts.values())
        assert total == len(data.get("domains", {})), f"Count sum {total} != domains {len(data['domains'])}"

    def test_wave1_domains_are_w3_or_higher(self, audit_result):
        data, _ = audit_result
        wave1 = {"nowplaying", "queue", "lyrics", "settings", "output_profiles",
                 "metadata", "smart_tagging", "diagnostics"}
        for domain in wave1:
            status = data["domains"][domain]["status"]
            assert status in {"W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"}, \
                f"{domain} should be W3+ but is {status}"

    def test_wave2_domains_are_w3_or_higher(self, audit_result):
        data, _ = audit_result
        wave2 = {"library", "album_artist", "playlists", "history",
                 "global_search", "mix", "radio", "equalizer"}
        for domain in wave2:
            status = data["domains"][domain]["status"]
            assert status in {"W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"}, \
                f"{domain} should be W3+ but is {status}"

    def test_w3_plus_ratio_meets_target(self, audit_result):
        data, _ = audit_result
        counts = data.get("counts", {})
        w3_plus = sum(counts.get(s, 0) for s in ("W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"))
        total = sum(counts.values())
        ratio = w3_plus / total if total else 0
        assert ratio >= 0.60, f"W3+ ratio {ratio:.0%} < 60% target"

    def test_matrix_yaml_exists(self):
        assert MATRIX.exists(), "qwidget_decommission_matrix.yaml not found"

    def test_matrix_yaml_is_valid(self):
        import yaml
        text = MATRIX.read_text()
        data = yaml.safe_load(text)
        assert "domains" in data, "Missing 'domains' in YAML"

    def test_matrix_yaml_has_no_w0_active(self):
        import yaml
        data = yaml.safe_load(MATRIX.read_text())
        domains = data.get("domains", {})
        # Data might have dict values
        if isinstance(domains, dict):
            for name, info in domains.items():
                if isinstance(info, dict):
                    assert info.get("status") != "W0_ACTIVE", f"{name} is W0_ACTIVE"

    def test_bridge_registration_consistency(self, audit_result):
        data, _ = audit_result
        br = REPO / "ui_qml_bridge" / "bridge_factory.py"
        bf_text = br.read_text()
        for domain, info in data.get("domains", {}).items():
            bridge = info.get("bridge")
            if bridge and info["status"] not in ("W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"):
                create_method = f"create_{bridge}_bridge"
                assert create_method in bf_text or f"create_{bridge}" in bf_text, \
                    f"{domain}: bridge method {create_method} not in bridge_factory.py"
