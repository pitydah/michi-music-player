"""DAC-V35-110 — field evidence schema v2 gates (the REAL harness)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[2] / "scripts" / "dac_r110_field_suite.py"


def _harness_source() -> str:
    return HARNESS.read_text(encoding="utf-8")


def test_fs110_01_harness_emits_schema_v2() -> None:
    source = _harness_source()
    assert '"schema_version": 2,' in source
    assert '"schema_version": 1,' not in source


def test_fs110_02_observations_use_nested_namespaces() -> None:
    source = _harness_source()
    for namespace in (
        '"source": _source_section(',
        '"request": {',
        '"playback": {',
        '"output": {',
        '"plan": captured.get("plan")',
        '"signal_truth": captured.get("signal_truth_diagnostics")',
        '"receipt": {',
    ):
        assert namespace in source, namespace
    # The flat anti-pattern that let runtime values overwrite fixture truth.
    assert 'entry = dict(report["fixtures"][key])' not in source
    assert "entry.update(_capture(" not in source


def test_fs110_03_source_fields_are_immutable_fixture_truth() -> None:
    source = _harness_source()
    section = source.split("def _source_section(", 1)[1].split("def _capture(", 1)[0]
    for field in (
        '"path"',
        '"sha256"',
        '"rate_hz"',
        '"channels"',
        '"significant_bits"',
        '"seconds"',
        '"amplitude"',
    ):
        assert field in section, field
    # Nothing in the source section may read a captured runtime value.
    assert "captured" not in section


def test_fs110_04_execution_sha_is_derived_not_hand_entered() -> None:
    source = _harness_source()
    assert "def _execution_git_head()" in source
    assert '"execution_git_head": _execution_git_head(),' in source


def test_fs110_05_device_locator_is_validated_before_the_run() -> None:
    source = _harness_source()
    assert "def _validate_device(" in source
    assert "_validate_device(container," in source
    # A mismatch aborts instead of silently running against a stale card.
    section = source.split("def _validate_device(", 1)[1].split("def ", 1)[0]
    assert "SystemExit" in section


def test_fs110_05b_environment_fingerprint_is_device_bound() -> None:
    source = _harness_source()
    assert "default_environment_fingerprint()" not in source
    assert "current_environment_context(args.device_id)" in source
    assert "current_environment_fingerprint(" in source
    assert "complete_for_current_evidence" in source
    assert '"environment_context": None,' in source
    assert '"environment_fingerprint": None,' in source


def test_fs110_06_signal_truth_comes_from_the_domain_authority() -> None:
    source = _harness_source()
    assert "signal_truth_snapshot_diagnostics" in source
    # No parallel classifier inside the harness.
    assert "SignalTruthRecorder()" not in source


def test_fs110_07_harness_compiles() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(HARNESS)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_fs110_08_historical_v1_evidence_is_not_rewritten() -> None:
    """Historical schema-v1 packages stay exactly as captured."""
    root = Path(__file__).resolve().parents[2] / "evidence" / "dac-v35-110"
    historical = sorted(path for path in root.glob("2026-09-24-*") if path.is_dir())
    assert historical, "historical evidence must remain present"
    for package in historical:
        for matrix in package.glob("*_matrix.json"):
            payload = json.loads(matrix.read_text(encoding="utf-8"))
            assert payload.get("schema_version") == 1, matrix
