"""Contract tests for the DAC-V35-100 aggregate verifier."""

from __future__ import annotations

import json
from zipfile import ZipFile

from scripts import verify_dac_m11_4 as verifier


def test_verifier_manifest_covers_every_required_gate_family() -> None:
    gate_ids = {gate.gate_id for gate in verifier.TEST_GATES}
    assert gate_ids == {
        "repository-alignment",
        "ruff-check",
        "ruff-format",
        "dac-qml-lint",
        "required-test-collection",
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
    assert report["generated_at"] == report["generated_at_utc"]
    assert "test_counts" in report
    assert "skip_classification" in report
    assert "ci" in report


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


def test_missing_required_test_collection_is_no_go() -> None:
    output = "tests/dac/test_v35_100_software_closure.py::test_one\n1 collected\n"
    ok, detail = verifier._required_collection_gate(output)
    assert ok is False
    assert "test_v35_100r1_startup_resume.py" in detail


def test_all_required_modules_are_detected_without_parsing_test_names() -> None:
    assert (
        "tests/dac/test_v35_100r11_source_characterization.py"
        in verifier.REQUIRED_COLLECTED_MODULES
    )
    output = "\n".join(
        f"{path}::test_any" for path in verifier.REQUIRED_COLLECTED_MODULES
    )
    ok, detail = verifier._required_collection_gate(output)
    assert ok is True
    assert "mandatory modules collected" in detail


def test_source_characterization_contract_is_productively_wired() -> None:
    ok, detail = verifier._source_characterization_contract_gate()
    assert ok, detail


def test_mandatory_dac_skip_is_no_go() -> None:
    output = (
        "SKIPPED [1] tests/dac/test_v35_100r1_startup_resume.py:22: "
        "dependency absent\n1 skipped\n"
    )
    ok, detail = verifier._mandatory_skip_gate(output)
    assert ok is False
    assert "mandatory DAC" in detail


def test_mandatory_dac_xfail_without_skip_count_is_no_go() -> None:
    output = (
        "XFAIL tests/dac/test_v35_100r1_startup_resume.py::test_resume "
        "- Direct runtime unavailable\n1 xfailed\n"
    )
    records = verifier._skip_records(output)
    assert records == [
        {
            "kind": "xfail",
            "file": "tests/dac/test_v35_100r1_startup_resume.py",
            "reason": "Direct runtime unavailable",
            "classification": "mandatory_dac_software",
        }
    ]
    assert verifier._mandatory_skip_gate(output)[0] is False


def test_mandatory_dac_xpass_ran_and_does_not_count_as_skip() -> None:
    output = (
        "XPASS tests/dac/test_v35_100r1_startup_resume.py::test_resume "
        "- historical expectation\n1 xpassed\n"
    )
    assert verifier._mandatory_skip_gate(output)[0] is True


def test_unrelated_environmental_skip_is_classified() -> None:
    output = (
        "SKIPPED [1] tests/test_production_container_golden.py:112: "
        "dependency absent: mpd executable not found in PATH\n1 skipped\n"
    )
    records = verifier._skip_records(output)
    assert records == [
        {
            "kind": "skipped",
            "file": "tests/test_production_container_golden.py",
            "reason": "dependency absent: mpd executable not found in PATH",
            "classification": "environmental_optional",
        }
    ]
    assert verifier._mandatory_skip_gate(output)[0] is True


def test_positive_product_claim_leak_is_no_go(tmp_path) -> None:
    product = tmp_path / "src" / "michi"
    product.mkdir(parents=True)
    (product / "claim.qml").write_text('Text { text: "Bit-perfect" }\n')
    ok, detail = verifier._claim_leak_gate(tmp_path)
    assert ok is False
    assert "claim.qml:1" in detail


def test_negative_product_claim_disclaimer_is_allowed(tmp_path) -> None:
    product = tmp_path / "src" / "michi"
    product.mkdir(parents=True)
    (product / "claim.qml").write_text(
        'Text { text: "This is not a bit-perfect certification." }\n'
    )
    assert verifier._claim_leak_gate(tmp_path)[0] is True


def test_unrelated_prior_negation_does_not_mask_positive_claim(tmp_path) -> None:
    product = tmp_path / "src" / "michi"
    product.mkdir(parents=True)
    (product / "claim.qml").write_text(
        '// No fallback is used.\nText { text: "Bit-perfect" }\n'
    )
    ok, detail = verifier._claim_leak_gate(tmp_path)
    assert ok is False
    assert "claim.qml:2" in detail


def _write_status_fixture(root, *, work_package_state: str) -> None:
    (root / "docs" / "dac").mkdir(parents=True)
    (
        root
        / "docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md"
    ).write_text(
        "DAC-V35-100R1.3.1 = CLOSED-AUTOMATED / LOCAL GO; REMOTE PUBLICATION PENDING\n"
        "DAC-V35-110 DO NOT START\n"
        "DAC-V35-130 POST-STABLE ONLY\n"
    )
    (root / "docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md").write_text(
        "IMPLEMENTED / PHYSICAL QUALIFICATION PENDING\nDAC-V35-100R1.3.1\n"
    )
    (root / "docs/STATUS_MATRIX.md").write_text(
        "| M11.4 Audiophile Output & DAC | IMPLEMENTED | DAC-V35-100R1.3.1 |\n"
        f"| M11.4 Audiophile Output & DAC Management | {work_package_state} | R1 |\n"
    )
    (root / "docs/MASTER_ROADMAP_1.0.md").write_text(
        "| M11.4 Audiophile Output/DAC | IMPLEMENTED | DAC-V35-100R1.3.1 |\n"
    )
    (root / "README.md").write_text(
        "DAC-V35-100R1.3.1 PHYSICAL QUALIFICATION PENDING\n"
    )


def test_status_contradiction_is_no_go(tmp_path) -> None:
    _write_status_fixture(tmp_path, work_package_state="DONE")
    ok, detail = verifier._status_consistency_gate(tmp_path)
    assert ok is False
    assert "must not be DONE" in detail


def test_status_consistency_accepts_physical_pending(tmp_path) -> None:
    _write_status_fixture(tmp_path, work_package_state="IN_PROGRESS")
    assert verifier._status_consistency_gate(tmp_path)[0] is True


def test_manifest_requires_140_separate_promotion(tmp_path) -> None:
    manifest = tmp_path / "tests/dac/test_v35_100_software_closure.py"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        '"conditional": ("DAC-V35-120",),\n"post_stable": ("DAC-V35-130",),\n'
    )
    ok, detail = verifier._verification_manifest_gate(tmp_path)
    assert ok is False
    assert "DAC-V35-140" in detail


def test_remote_sha_mismatch_is_no_go() -> None:
    ok, detail = verifier._ci_commit_gate("a" * 40, {"GITHUB_SHA": "b" * 40})
    assert ok is False
    assert "!=" in detail


def test_all_internal_r1_contract_gates_pass_on_repository() -> None:
    collected = "\n".join(verifier.REQUIRED_COLLECTED_MODULES)
    assert verifier._required_collection_gate(collected)[0] is True
    assert verifier._mandatory_skip_gate("")[0] is True
    assert verifier._claim_leak_gate()[0] is True
    assert verifier._verification_manifest_gate()[0] is True


def test_remote_closure_has_full_history_without_activating_real_mpd() -> None:
    workflow = (verifier.ROOT / ".github/workflows/ci.yml").read_text()
    closure_job = workflow.split("  dac-v35-software-closure:", 1)[1]
    assert "fetch-depth: 0" in closure_job
    system_install = closure_job.split(
        "Install Qt, GStreamer, ALSA, and runtime dependencies", 1
    )[1].split("Install project and closure dependencies", 1)[0]
    assert "mpd" not in system_install.replace("\\", " ").split()
