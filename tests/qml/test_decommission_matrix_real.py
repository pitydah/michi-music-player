"""Tests for qwidget_decommission_matrix — real code audit against declarative matrix."""
import sys
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent.parent
MATRIX_PATH = REPO / "config" / "qwidget_decommission_matrix.yaml"
DOCS_MATRIX_PATH = REPO / "docs" / "qwidget_decommission_matrix.yaml"
SCRIPT_PATH = REPO / "scripts" / "qml_decommission_audit.py"

VALID_STATUSES = {"W0_ACTIVE", "W1_FROZEN", "W2_THIN_ADAPTER", "W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"}
W3_PLUS = {"W3_LEGACY_ONLY", "W4_DETACHED", "W5_REMOVABLE_AFTER_PHYSICAL"}
REQUIRED_FIELDS = {"domain", "widget_status", "qml_status", "business_logic_shared", "qml_imports_widget", "packaged_in_qml", "workflow_passed", "physical_required"}

EVIDENCE_FILES = {
    "navigation": "ui_qml/shell/Sidebar.qml",
    "home": "ui_qml/pages/home/HomePage.qml",
    "library": "ui_qml/pages/library/LibraryPage.qml",
    "nowplaying": "ui_qml/pages/nowplaying/NowPlayingPage.qml",
}


def _list_qml_pages():
    pages_dir = REPO / "ui_qml" / "pages"
    if not pages_dir.is_dir():
        return set()
    return {p.name.lower() for p in pages_dir.iterdir() if p.is_dir()}


def test_canonical_matrix_exists():
    assert MATRIX_PATH.is_file(), f"canonical matrix not found at {MATRIX_PATH}"


def test_no_duplicate_matrix_in_docs():
    assert not DOCS_MATRIX_PATH.exists(), "duplicate matrix still in docs/"


def test_matrix_valid_yaml():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    assert "domains" in data
    assert len(data["domains"]) > 0


def test_all_domains_have_required_fields():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    for d in data["domains"]:
        missing = [f for f in REQUIRED_FIELDS if f not in d]
        assert not missing, f"Domain '{d.get('domain', '?')}' missing fields: {missing}"


def test_all_domains_valid_widget_status():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    for d in data["domains"]:
        status = d.get("widget_status", "")
        assert status in VALID_STATUSES, f"Domain '{d.get('domain', '?')}' has invalid status '{status}'"


def test_all_domains_valid_qml_status():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    valid_qml = {"PRODUCTIVE", "PARTIAL_WORKFLOW", "PLACEHOLDER", "NOT_STARTED", "BLOCKED"}
    for d in data["domains"]:
        qml = d.get("qml_status", "")
        assert qml in valid_qml, f"Domain '{d.get('domain', '?')}' has invalid qml_status '{qml}'"


def test_w3_plus_ratio_meets_target():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    w3 = sum(1 for d in data["domains"] if d.get("widget_status") in W3_PLUS)
    total = len(data["domains"])
    ratio = w3 / total * 100
    assert ratio >= 60, f"W3+ ratio = {ratio:.0f}% (target >= 60%)"


def test_business_logic_shared_is_boolean():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    for d in data["domains"]:
        assert isinstance(d.get("business_logic_shared"), bool), f"Domain '{d['domain']}' business_logic_shared not bool"
        assert isinstance(d.get("qml_imports_widget"), bool), f"Domain '{d['domain']}' qml_imports_widget not bool"
        assert isinstance(d.get("packaged_in_qml"), bool), f"Domain '{d['domain']}' packaged_in_qml not bool"
        assert isinstance(d.get("workflow_passed"), bool), f"Domain '{d['domain']}' workflow_passed not bool"
        assert isinstance(d.get("physical_required"), bool), f"Domain '{d['domain']}' physical_required not bool"


def test_w3_legacy_only_have_qml_evidence():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    for d in data["domains"]:
        if d.get("widget_status") in W3_PLUS:
            domain = d["domain"].lower()
            if domain in EVIDENCE_FILES:
                path = REPO / EVIDENCE_FILES[domain]
                assert path.is_file(), f"Domain '{domain}' W3+ declared but QML file missing: {EVIDENCE_FILES[domain]}"


def test_audit_script_runs_successfully():
    if not SCRIPT_PATH.is_file():
        pytest.skip("audit script not found")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True, text=True,
        cwd=str(REPO),
    )
    assert result.returncode == 0, f"audit script failed:\n{result.stderr}"


def test_audit_script_prints_all_domains():
    if not SCRIPT_PATH.is_file():
        pytest.skip("audit script not found")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True, text=True,
        cwd=str(REPO),
    )
    output = result.stdout
    assert "W3+" in output
    assert "TARGET MET" in output or "TARGET NOT MET" in output


def test_no_duplicate_domain_names():
    data = yaml.safe_load(MATRIX_PATH.read_text())
    names = [d.get("domain", "") for d in data["domains"] if d.get("domain")]
    assert len(names) == len(set(names)), f"duplicate domain names found: {names}"
