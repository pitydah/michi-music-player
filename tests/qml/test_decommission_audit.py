"""Test QWidget decommission audit — matrix validity, W3+ ratio."""
import subprocess
import sys
import yaml
from pathlib import Path


MATRIX_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "qwidget_decommission_matrix.yaml"


def test_matrix_exists():
    assert MATRIX_PATH.exists()


def test_matrix_is_valid_yaml():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    assert "domains" in data
    assert len(data["domains"]) > 0


def test_all_domains_have_widget_status():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    valid_statuses = {"W0_ACTIVE", "W1_FROZEN", "W2_THIN_ADAPTER", "W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"}
    for d in data["domains"]:
        assert d.get("widget_status") in valid_statuses, f"{d['domain']} has invalid status {d.get('widget_status')}"


def test_w3_plus_ratio_meets_target():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    w3_plus = sum(1 for d in data["domains"] if d.get("widget_status") in ("W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"))
    total = len(data["domains"])
    ratio = w3_plus / total * 100
    assert ratio >= 60, f"W3+ ratio is {ratio:.0f}% (target: >= 60%)"


def test_decommission_audit_script_runs():
    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "qml_decommission_audit.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "TARGET MET" in result.stdout or "W3+" in result.stdout
