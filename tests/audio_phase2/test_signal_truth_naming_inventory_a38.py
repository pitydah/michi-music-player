"""ST-NAME-001 baseline inventory and strict-gate unit tests (stdlib)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "audit_michi_signal_truth_naming.py"
)


def _git(repo: Path, *args: str):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )


def _repo(tmp_path: Path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "dummy.py").write_text('NAME = "Michi Signal Truth"\n')
    _git(tmp_path, "add", "src/dummy.py")
    return tmp_path


def _run(repo: Path, *options: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), *options],
        capture_output=True,
        text=True,
        check=False,
    )


def test_clean_repo_inventory_and_enforce(tmp_path):
    repo = _repo(tmp_path)
    actual = _run(repo, "--enforce")
    assert actual.returncode == 0
    assert json.loads(actual.stdout)["result"] == "CLEAN"


def test_inventory_reports_old_product_content_but_does_not_block_work(tmp_path):
    repo = _repo(tmp_path)
    forbidden = "Signal" + "Path"
    (repo / "src" / "dummy.py").write_text('x = "' + forbidden + '"\n')
    _git(repo, "add", "src/dummy.py")
    actual = _run(repo)
    report = json.loads(actual.stdout)
    assert actual.returncode == 0  # audit mode never hides findings
    assert report["result"] == "MIGRATION_REQUIRED"
    assert {x["line"] for x in report["hits"] if x["kind"] == "PRODUCT_CONTENT"} == {1}
    assert _run(repo, "--enforce").returncode == 1


def test_old_file_name_and_canonical_bible_are_independent_findings(tmp_path):
    repo = _repo(tmp_path)
    old_name = "signal" + "_" + "path"
    (repo / "src" / f"{old_name}.py").write_text("# old\n")
    bible = repo / "docs" / "audio"
    bible.mkdir(parents=True)
    f = bible / ("MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_" + "PATH_MEGA_PLAN.md")
    f.write_text("# spec\n")
    _git(repo, "add", ".")
    report = json.loads(_run(repo).stdout)
    assert report["result"] == "MIGRATION_REQUIRED"
    assert any(x["kind"] == "PRODUCT_PATH" for x in report["hits"])
    assert any(x["kind"] == "CANONICAL_DOCUMENT_RELOCATION" for x in report["hits"])


def test_historical_docs_are_not_scanned_as_product_contents(tmp_path):
    repo = _repo(tmp_path)
    docs = repo / "docs" / "research"
    docs.mkdir(parents=True)
    (docs / "external.md").write_text("Roon " + "Signal" + " Path research\n")
    _git(repo, "add", ".")
    actual = _run(repo, "--enforce")
    assert actual.returncode == 0
    assert json.loads(actual.stdout)["result"] == "CLEAN"


def test_broken_tracked_symlink_rejected_even_in_non_enforce_mode(tmp_path):
    repo = _repo(tmp_path)
    path = repo / "src" / "broken.py"
    path.symlink_to(repo / "no-file")
    _git(repo, "add", ".")
    report = _run(repo)
    assert report.returncode == 2
    assert json.loads(report.stdout)["result"] == "ERROR"
