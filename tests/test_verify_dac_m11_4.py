"""Contract tests for the DAC-V35-100 aggregate verifier."""

from __future__ import annotations

import json
from zipfile import ZipFile

from scripts import verify_dac_m11_4 as verifier


def test_verifier_manifest_covers_every_required_gate_family() -> None:
    gate_ids = {gate.gate_id for gate in verifier.TEST_GATES}
    assert gate_ids == {
        "repository-alignment",
        "dac-domain-runtime",
        "engine-audioport-regressions",
        "playback-regressions",
        "persistence-provenance",
        "dac-qml-runtime",
        "full-regression-suite",
    }


def test_verdict_report_has_canonical_shape(tmp_path, monkeypatch) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "ARTIFACTS", artifacts)
    result = verifier.GateResult("gate", "description", (), "PASS", 0, 0.1, None, "ok")

    verifier._write_reports("a" * 40, [result])

    report = json.loads((artifacts / "dac_m11_4_verdict.json").read_text())
    assert report["schema_version"] == 1
    assert report["commit"] == "a" * 40
    assert report["spec_revision"] == "V3.5"
    assert report["automated_verdict"] == "GO"
    assert report["physical_verdict"] == "NOT_RUN"
    assert report["gates"][0]["status"] == "PASS"


def test_wheel_gate_requires_dac_python_and_qml_members(tmp_path) -> None:
    wheel = tmp_path / "michi.whl"
    with ZipFile(wheel, "w") as archive:
        for member in verifier.REQUIRED_DAC_WHEEL_MEMBERS:
            archive.writestr(member, "")

    assert verifier._wheel_members_gate(wheel)[0] is True

    missing = tmp_path / "missing.whl"
    with ZipFile(missing, "w") as archive:
        archive.writestr("michi/__init__.py", "")
    ok, detail = verifier._wheel_members_gate(missing)
    assert ok is False
    assert "AudioOutputSettingsSection.qml" in detail


def test_built_wheel_requires_one_artifact_from_this_output_directory(
    tmp_path,
) -> None:
    assert verifier._built_wheel(tmp_path) is None
    first = tmp_path / "first.whl"
    first.write_bytes(b"first")
    assert verifier._built_wheel(tmp_path) == first
    (tmp_path / "second.whl").write_bytes(b"second")
    assert verifier._built_wheel(tmp_path) is None


def test_alignment_artifact_must_be_current_and_aligned(tmp_path, monkeypatch) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    monkeypatch.setattr(verifier, "ARTIFACTS", artifacts)
    path = artifacts / "dac_repository_alignment.json"
    path.write_text(json.dumps({"commit": "old", "aligned": True}))
    assert verifier._alignment_artifact_gate("current")[0] is False

    path.write_text(json.dumps({"commit": "current", "aligned": False}))
    assert verifier._alignment_artifact_gate("current")[0] is False

    path.write_text(json.dumps({"commit": "current", "aligned": True}))
    assert verifier._alignment_artifact_gate("current")[0] is True


def test_repository_static_invariants_are_currently_satisfied() -> None:
    ok, detail = verifier._static_invariants()
    assert ok, detail


def test_dirty_worktree_cannot_receive_commit_bound_go(monkeypatch) -> None:
    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda *args, **kwargs: verifier.subprocess.CompletedProcess(
            args[0], 0, stdout=" M changed.py\n", stderr=""
        ),
    )
    ok, detail = verifier._working_tree_gate()
    assert ok is False
    assert "dirty" in detail
