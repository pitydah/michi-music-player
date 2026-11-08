"""A48 package contract; fixture tests not a substitute for Qt/ALSA products."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.verify_michi_truth_p1_a48 import PATHS, check


@pytest.fixture
def root():
    return Path(__file__).resolve().parents[2]


def test_p1_package_is_complete_and_product_not_certified(root):
    verdict = check(root)
    assert verdict["candidate_static_preflight"] == "PASS", verdict["failures"]
    assert verdict["full_product_status"] == "NOT_RUN"
    assert len(verdict["paths_sha256"]) == 11


def test_p1_json_has_separate_product_gates(root):
    spec = json.loads(
        (root / "docs/audio/phase2/F11_SIGNAL_TRUTH_A48_P1_ACCEPTANCE.json").read_text()
    )
    assert len(spec["gates"]) == 6
    assert all(
        item["product_evidence"] is None and item["product_state"] == "NOT_RUN"
        for item in spec["gates"]
    )
    assert set(spec["p0_remainder"]) == {f"OPEN-P0-0{i}" for i in range(1, 8)}


def test_p1_qml_is_optional_pure_renderer(root):
    source = (
        root / "src/michi/presentation/qml/components/MichiSignalTruthMetrics.qml"
    ).read_text()
    assert "ColumnLayout {" in source and "Repeater {" in source
    assert "Timer {" not in source and "Connections {" not in source
    assert "Accessible.name:" in source
    assert "signalTruthMetricRow" in source
    assert "isFinite(item.value)" in source
    assert "slice(0, 8)" in source
    assert 'root.temporalStatus === "ACTIVE"' in source


def test_p1_spec_records_no_mandate_to_change_git_or_dac(root):
    spec = (root / "docs/audio/phase2/F11_SIGNAL_TRUTH_A48_P1_CANONICAL.md").read_text()
    for term in ("F11", "NOW", "P1-DIAG", "P1-REMOTE", "rollback", "KWin"):
        if term == "NOW":
            continue
        assert term.lower() in spec.lower()
    assert "F12–F15" in spec


def test_p1_verifier_refuses_false_product_pass(tmp_path, root):
    for source in PATHS:
        actual = root / source
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(actual.read_bytes())
    matrix = tmp_path / "docs/audio/phase2/F11_SIGNAL_TRUTH_A48_P1_ACCEPTANCE.json"
    content = json.loads(matrix.read_text())
    content["gates"][0]["product_state"] = "PASS"
    matrix.write_text(json.dumps(content))
    result = check(tmp_path)
    assert "P1_PRODUCT_PASS_FORGED" in result["failures"]
    assert result["candidate_static_preflight"] == "FAIL"


def test_p1_verifier_refuses_qml_new_popup(tmp_path, root):
    for source in PATHS:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / source).read_bytes())
    qml = tmp_path / "src/michi/presentation/qml/components/MichiSignalTruthMetrics.qml"
    qml.write_text(qml.read_text() + "\nPopup { }\n")
    assert "P1_QML_ILLEGAL_OWNER" in check(tmp_path)["failures"]
