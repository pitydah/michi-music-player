"""A39 production-guard tests; NOT a replacement for full checkout gates."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# The new standalone runner is available via repo/scripts after applying A39.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.verify_michi_truth_product_integration import (  # noqa: E402
    BASE_BLOBS,
    Check,
    eligible,
    junit_summary,
    run_integration,
    validate_checkout,
)


def test_blob_pin_manifest_has_exact_recorder_and_owner():
    assert BASE_BLOBS["src/michi/domain/signal_truth.py"] == (
        "8859d9c6519807f20551a0f5650b40bcd277465a"
    )
    assert "src/michi/application/output_session_service.py" in BASE_BLOBS


def test_no_negative_check_is_eligible():
    assert eligible([Check("A", "PASS"), Check("B", "PASS")])
    assert not eligible([])
    assert not eligible([Check("A", "PASS"), Check("B", "FAIL")])
    assert not eligible([Check("A", "PASS"), Check("B", "NOT_RUN")])


def test_junit_requires_nonempty_suite(tmp_path: Path):
    file = tmp_path / "empty.xml"
    file.write_text('<testsuite tests="0" failures="0" errors="0" skipped="0"/>')
    assert junit_summary(file) is None


def test_junit_counts_skips_even_when_suite_exit_zero(tmp_path: Path):
    file = tmp_path / "suite.xml"
    file.write_text(
        '<testsuites><testsuite tests="3" failures="0" errors="0" '
        'skipped="1" /></testsuites>'
    )
    assert junit_summary(file) == {"tests": 3, "failures": 0, "errors": 0, "skipped": 1}


def test_junit_invalid_xml_fails_closed(tmp_path: Path):
    file = tmp_path / "bad.xml"
    file.write_text("<oops")
    assert junit_summary(file) is None


def test_sparse_git_checkout_is_never_product_checkout(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "AGENTS.md").write_text("fixture only")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    checks = validate_checkout(tmp_path)
    assert not eligible(checks)
    assert next(item for item in checks if item.key == "FULL_CHECKOUT").status == "FAIL"


def test_runner_refuses_to_apply_when_head_differs(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("before\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    patch = tmp_path.parent / "candidate.patch"
    patch.write_text("not a valid diff")
    receipt = run_integration(tmp_path, patch, apply=True)
    assert receipt["status"] == "STOP_NO_MUTATION"
    assert receipt["patch_applied"] is False
    assert (tmp_path / "README.md").read_text() == "before\n"
    assert Path(receipt["receipt_path"]).is_file()
    assert all(
        check["id"] != "PATCH_APPLIED" or check["status"] == "NOT_RUN"
        for check in receipt["checks"]
    )


def test_missing_candidate_patch_is_never_success(tmp_path: Path):
    check = run_integration(tmp_path, tmp_path / "missing.patch", apply=False)
    assert check["status"] == "STOP_NO_MUTATION"
    assert check["patch_sha256"] is None


def test_no_remote_mutation_capabilities_in_runner_source():
    source = (ROOT / "scripts/verify_michi_truth_product_integration.py").read_text()
    assert "git apply" not in source  # command is constructed, not shell string
    assert '"push"' not in source
    assert '"commit"' not in source
    assert '"merge"' not in source
    assert "--junitxml" in source
    assert "--apply" in source


def test_verify_applied_on_sparse_tree_cannot_upgrade_receipt(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "AGENTS.md").write_text("fixture")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    patch = tmp_path.parent / "fake.patch"
    patch.write_text("synthetic patch\n")
    receipt = run_integration(tmp_path, patch, verify_applied=True)
    assert receipt["status"] == "STOP_NO_MUTATION"
    assert receipt["patch_applied"] is False
    assert any(
        c["id"] == "FULL_CHECKOUT" and c["status"] == "FAIL" for c in receipt["checks"]
    )
