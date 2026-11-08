"""A43: exact-patch guards and rejection tests; product Qt/DAC gates are separate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_michi_truth_a43_package import (  # noqa: E402
    compare_tree,
    parse_patch,
    verify_migrated_package,
)
from verify_michi_truth_product_integration import run_integration  # noqa: E402


def _patch(path: Path, *, broken: bool = False) -> None:
    required = [
        "scripts/migrate_michi_truth_names_a41.py",
        "scripts/verify_michi_truth_product_integration.py",
        "src/michi/application/signal_truth_frame.py",
        "tests/audio_phase2/test_signal_truth_frame_a42.py",
    ] + [f"tests/audio_phase2/extra_{n}.py" for n in range(25)]
    if broken:
        required[-1] = required[0]
    text = "".join(
        f"diff --git a/{p} b/{p}\nnew file mode 100644\n"
        f"--- /dev/null\n+++ b/{p}\n@@ -0,0 +1 @@\n+x\n"
        for p in required
    )
    path.write_text(text)


def test_manifest_requires_whole_cumulative_and_unique_paths(tmp_path):
    patch = tmp_path / "good.patch"
    _patch(patch)
    assert len(parse_patch(patch)) == 29
    _patch(patch, broken=True)
    with pytest.raises(ValueError, match="OVERLAPPING"):
        parse_patch(patch)


@pytest.mark.parametrize(
    "bad", ["../outside", ".git/config", "src/../outside", "image.png"]
)
def test_patch_cannot_touch_unapproved_paths(tmp_path, bad):
    patch = tmp_path / "bad.patch"
    _patch(patch)
    patch.write_text(patch.read_text().replace("tests/audio_phase2/extra_1.py", bad))
    with pytest.raises(ValueError, match="PATH_REFUSED"):
        parse_patch(patch)


def test_absent_and_unbounded_patch_refused(tmp_path):
    with pytest.raises(ValueError):
        parse_patch(tmp_path / "missing.patch")
    huge = tmp_path / "large.patch"
    huge.write_bytes(b"x" * (8_000_001))
    with pytest.raises(ValueError):
        parse_patch(huge)


def test_post_migration_comparison_detects_content_and_new_files(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for root in a, b:
        (root / "src").mkdir(parents=True)
        (root / "src" / "test.py").write_text("truth = 1\n")
    assert compare_tree(a, b) == ()
    (b / "src" / "test.py").write_text("truth = 2\n")
    assert any("CONTENT_DRIFT" in x for x in compare_tree(a, b))
    (b / "src" / "test.py").write_text("truth = 1\n")
    (b / "src" / "rogue.py").write_text("x=1\n")
    assert any("UNEXPECTED" in x for x in compare_tree(a, b))


def test_rejects_sparse_checkout_before_local_clone(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("unrelated\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    patch = tmp_path / "candidate.patch"
    _patch(patch)
    result = verify_migrated_package(tmp_path, patch)
    assert result.status == "REFUSED"
    assert "A43_HEAD_NOT_PINNED" in result.issues


def test_a39_runner_does_not_apply_patch_when_verify_migrated(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("unmodified\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    patch = tmp_path / "candidate.patch"
    _patch(patch)
    receipt = run_integration(tmp_path, patch, verify_migrated=True)
    assert receipt["status"] == "STOP_NO_MUTATION"
    assert receipt["patch_applied"] is False
    assert (tmp_path / "README.md").read_text() == "unmodified\n"


def test_contract_keeps_migration_separate_from_remote_actions():
    body = (ROOT / "scripts/verify_michi_truth_a43_package.py").read_text()
    assert "local" in body and "clone" in body
    assert '"push"' not in body
    assert '"commit"' not in body
    assert '"pull"' not in body
    assert '"remote"' not in body


def test_bad_sha256_pin_refuses_without_writing(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("original\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    patch = tmp_path / "candidate.patch"
    _patch(patch)
    receipt = run_integration(
        tmp_path, patch, apply=True, expected_patch_sha256="0" * 64
    )
    assert receipt["status"] == "STOP_NO_MUTATION"
    assert any(
        c["id"] == "PATCH_SHA256_PIN" and c["status"] == "FAIL"
        for c in receipt["checks"]
    )
    assert (tmp_path / "README.md").read_text() == "original\n"
