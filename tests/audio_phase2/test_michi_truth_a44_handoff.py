"""A44 handoff tests: synthetic receipts, no product DAC/Qt/CI assertion."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_michi_truth_a44_handoff import (  # noqa: E402
    EXPECTED_HEAD,
    GATES,
    SCHEMA,
    _new_private_json,
    _read_receipt,
    _safe_evidence_path,
    evaluate,
    initial_receipt,
    main,
)


def _patch(tmp_path):
    patch = tmp_path / "candidate.patch"
    paths = [
        "scripts/migrate_michi_truth_names_a41.py",
        "scripts/verify_michi_truth_product_integration.py",
        "src/michi/application/signal_truth_frame.py",
        "tests/audio_phase2/test_signal_truth_frame_a42.py",
    ] + [f"tests/audio_phase2/a44_dummy_{i}.py" for i in range(25)]
    patch.write_text(
        "".join(
            f"diff --git a/{p} b/{p}\nnew file mode 100644\n"
            f"--- /dev/null\n+++ b/{p}\n@@ -0,0 +1 @@\n+x\n"
            for p in paths
        ),
        encoding="utf-8",
    )
    return patch, hashlib.sha256(patch.read_bytes()).hexdigest()


def _base(tmp_path):
    patch, digest = _patch(tmp_path)
    root = tmp_path / "proofs"
    root.mkdir()
    return patch, digest, root, initial_receipt(patch, digest)


def _pass(
    receipt, root, name, *, boundary="SOFTWARE", content=b"receipt\n", subject_sha=None
):
    file = root / f"{name}.txt"
    file.write_bytes(content)
    row = {
        "status": "PASS",
        "evidence": {
            "run_id": f"run_{name}_2026",
            "exit_code": 0,
            "sha256": hashlib.sha256(content).hexdigest(),
            "boundary": boundary,
            "relative_path": file.name,
        },
    }
    if subject_sha is not None:
        row["evidence"]["subject_sha"] = subject_sha
    receipt["gates"][name] = row
    return file


def test_init_is_fail_closed_for_every_gate(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    assert receipt["schema"] == SCHEMA
    assert receipt["source_head"] == EXPECTED_HEAD
    assert set(receipt["gates"]) == set(GATES)
    assert all(
        g["status"] == "NOT_RUN" and g["evidence"] is None
        for g in receipt["gates"].values()
    )
    result = evaluate(receipt, patch, digest, root)
    assert result.decision == "NO_GO"
    assert len(result.pending) == len(GATES)
    assert not result.has_hardware_evidence


def test_init_refuses_wrong_sha_without_mutation(tmp_path):
    patch, _, root, receipt = _base(tmp_path)
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        initial_receipt(patch, "0" * 64)
    with pytest.raises(ValueError, match="SHA_PIN_INVALID"):
        initial_receipt(patch, "not_sha")


def test_changed_patch_is_rejected(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    patch.write_text(patch.read_text() + "junk\n")
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        evaluate(receipt, patch, digest, root)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("schema", "other", "SCHEMA_OR_PHASE"),
        ("phase", "AP2-F12", "SCHEMA_OR_PHASE"),
        ("source_head", "1" * 40, "SOURCE_HEAD_MISMATCH"),
        ("patch_sha256", "2" * 64, "RECEIPT_PATCH_HASH_MISMATCH"),
        ("candidate_sha", "bad", "CANDIDATE_SHA_INVALID"),
    ],
)
def test_receipt_header_fence(tmp_path, field, value, code):
    patch, digest, root, receipt = _base(tmp_path)
    receipt[field] = value
    result = evaluate(receipt, patch, digest, root)
    assert result.decision == "NO_GO"
    assert any(code in code_value for code_value in result.issues)


def test_no_silent_optional_or_unknown_gates(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    receipt["gates"].pop("dop")
    receipt["gates"]["bypass_proof"] = {"status": "PASS"}
    result = evaluate(receipt, patch, digest, root)
    assert "A44_GATE_MATRIX_INCOMPLETE_OR_UNKNOWN" in result.issues
    assert "dop" in result.pending


def test_positive_cannot_be_declared_without_artifact(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    receipt["gates"]["python_regressions"] = {"status": "PASS", "evidence": None}
    result = evaluate(receipt, patch, digest, root)
    assert "A44_POSITIVE_WITHOUT_EVIDENCE:python_regressions" in result.issues


def test_software_evidence_hash_is_verified(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    file = _pass(receipt, root, "python_regressions")
    assert "python_regressions" in evaluate(receipt, patch, digest, root).passed
    file.write_bytes(b"modified without updating hash")
    result = evaluate(receipt, patch, digest, root)
    assert "A44_EVIDENCE_HASH_MISMATCH:python_regressions" in result.issues
    assert "python_regressions" not in result.passed


@pytest.mark.parametrize(
    "bad",
    [
        "../outside",
        "/etc/passwd",
        "./private.txt",
        ".hidden",
        "proofs/../file",
        "~/user",
        "file\\hidden",
        "",
        "a/../../other",
    ],
)
def test_path_traversal_and_hidden_proofs_refused(tmp_path, bad):
    root = tmp_path / "proofs"
    root.mkdir()
    with pytest.raises(ValueError, match="EVIDENCE_PATH_REFUSED"):
        _safe_evidence_path(root, bad)


def test_symlink_evidence_refused(tmp_path):
    root = tmp_path / "proofs"
    root.mkdir()
    target = tmp_path / "target.txt"
    target.write_text("evidence")
    (root / "linked.txt").symlink_to(target)
    with pytest.raises(ValueError, match="SYMLINK_REFUSED"):
        _safe_evidence_path(root, "linked.txt")


def test_oversized_evidence_refused(tmp_path):
    root = tmp_path / "proofs"
    root.mkdir()
    (root / "oversized.txt").write_bytes(b"a" * (8 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="SIZE_REFUSED"):
        _safe_evidence_path(root, "oversized.txt")


def test_nonzero_exit_code_cannot_pass(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    _pass(receipt, root, "python_regressions")
    receipt["gates"]["python_regressions"]["evidence"]["exit_code"] = 1
    assert (
        "A44_EVIDENCE_FIELDS_INVALID:python_regressions"
        in evaluate(receipt, patch, digest, root).issues
    )


@pytest.mark.parametrize(
    "gate,boundary",
    [
        ("native_dsd", "OUTPUT_BOUNDARY"),
        ("dop", "OUTPUT_BOUNDARY"),
        ("pcm_direct", "QT_OWNER"),
        ("qt_owner_dispatch", "SOFTWARE"),
        ("qml_truth_frame", "SOFTWARE"),
        ("kwin_a11y_dpr", "QML"),
    ],
)
def test_hardware_and_ui_boundaries_are_not_interchangeable(tmp_path, gate, boundary):
    patch, digest, root, receipt = _base(tmp_path)
    _pass(receipt, root, gate, boundary=boundary)
    result = evaluate(receipt, patch, digest, root)
    assert gate in result.pending
    assert any(
        gate in code
        or (gate == "qt_owner_dispatch" and "QT_OWNER_BOUNDARY" in code)
        or (gate == "qml_truth_frame" and "QML_BOUNDARY" in code)
        or (gate == "kwin_a11y_dpr" and "KWIN_BOUNDARY" in code)
        for code in result.issues
    )


def test_physical_proof_accepted_as_claim_but_not_closed(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    _pass(receipt, root, "native_dsd", boundary="DAC_RECEIVER")
    result = evaluate(receipt, patch, digest, root)
    assert "native_dsd" in result.passed
    assert result.has_hardware_evidence
    assert result.decision == "NO_GO"


def test_unsupported_family_cannot_be_silently_skipped(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    receipt["gates"]["dop"] = {"status": "CAPABILITY_UNSUPPORTED", "evidence": None}
    result = evaluate(receipt, patch, digest, root)
    assert "dop" in result.pending and result.decision == "NO_GO"


def test_unsupported_nonhardware_is_invalid(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    receipt["gates"]["python_regressions"] = {"status": "CAPABILITY_UNSUPPORTED"}
    assert (
        "A44_UNSUPPORTED_NON_HARDWARE:python_regressions"
        in evaluate(receipt, patch, digest, root).issues
    )


def test_exact_ci_cannot_claim_previous_commit(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    receipt["candidate_sha"] = "a" * 40
    _pass(receipt, root, "ci_exact_sha", boundary="CI_EXACT_SHA", subject_sha="b" * 40)
    assert (
        "A44_CI_EXACT_SHA_NOT_PROVEN" in evaluate(receipt, patch, digest, root).issues
    )
    receipt["gates"]["ci_exact_sha"]["evidence"]["subject_sha"] = "a" * 40
    assert "ci_exact_sha" in evaluate(receipt, patch, digest, root).passed


def test_all_synthetic_evidence_never_auto_certifies_release(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    receipt["candidate_sha"] = "a" * 40
    for name in GATES:
        boundary = {
            "native_dsd": "DAC_RECEIVER",
            "dop": "DAC_RECEIVER",
            "pcm_direct": "OUTPUT_BOUNDARY",
            "pcm_managed": "OUTPUT_BOUNDARY",
            "dsd_pcm": "OUTPUT_BOUNDARY",
            "qt_owner_dispatch": "QT_OWNER",
            "qml_truth_frame": "QML",
            "kwin_a11y_dpr": "KWIN",
            "ci_exact_sha": "CI_EXACT_SHA",
        }.get(name, "SOFTWARE")
        _pass(
            receipt,
            root,
            name,
            boundary=boundary,
            subject_sha="a" * 40 if name == "ci_exact_sha" else None,
        )
    result = evaluate(receipt, patch, digest, root)
    assert result.issues == ()
    assert len(result.passed) == len(GATES)
    assert result.decision == "HUMAN_CANONICAL_REVIEW_REQUIRED"
    assert result.to_json()["release_authorized"] is False
    assert result.to_json()["repository_modified"] is False


def test_receipt_loader_rejects_bad_and_too_large_json(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text("not json")
    with pytest.raises(ValueError, match="JSON_INVALID"):
        _read_receipt(path)
    path.write_text(json.dumps(["array"]))
    with pytest.raises(ValueError, match="STRUCTURE_INVALID"):
        _read_receipt(path)
    path.write_bytes(b"a" * (512 * 1024 + 1))
    with pytest.raises(ValueError, match="UNBOUNDED"):
        _read_receipt(path)


def test_private_write_no_overwrite_and_no_repo_mutation(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    dest = tmp_path / "out.json"
    _new_private_json(dest, {"ok": True}, repo=repo)
    assert json.loads(dest.read_text()) == {"ok": True}
    with pytest.raises(FileExistsError):
        _new_private_json(dest, {"ok": False}, repo=repo)
    with pytest.raises(ValueError, match="WITHIN_REPOSITORY"):
        _new_private_json(repo / "receipt.json", {}, repo=repo)
    assert list(repo.iterdir()) == []


def test_cli_init_and_evaluate_are_explicitly_incomplete(tmp_path):
    patch, digest, root, receipt = _base(tmp_path)
    repo = tmp_path / "checkout"
    repo.mkdir()
    output = tmp_path / "initial.json"
    code = main(
        [
            "init",
            "--patch",
            str(patch),
            "--patch-sha256",
            digest,
            "--repo",
            str(repo),
            "--output",
            str(output),
        ]
    )
    assert code == 0
    assert json.loads(output.read_text())["gates"]["dop"]["status"] == "NOT_RUN"
    status = tmp_path / "status.json"
    code = main(
        [
            "evaluate",
            "--patch",
            str(patch),
            "--patch-sha256",
            digest,
            "--repo",
            str(repo),
            "--receipt",
            str(output),
            "--evidence-root",
            str(root),
            "--output",
            str(status),
        ]
    )
    assert code == 2
    assert json.loads(status.read_text())["decision"] == "NO_GO"
    assert list(repo.iterdir()) == []


def test_no_git_remote_or_implicit_audio_control():
    text = (ROOT / "scripts/verify_michi_truth_a44_handoff.py").read_text()
    assert "subprocess." not in text and "requests." not in text
    assert "git push" not in text and "git commit" not in text
    assert 'release_authorized": False' in text


def test_a39_driver_importable_as_script_package_without_scripts_pythonpath(
    tmp_path,
):
    # Real repo pytest often imports scripts.foo with only project root + src
    # on sys.path.
    env = __import__("os").environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    run = subprocess.run(
        [sys.executable, "-c", "import scripts.verify_michi_truth_product_integration"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
