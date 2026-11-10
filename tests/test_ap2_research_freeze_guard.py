from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.verify_ap2_research_freeze import (
    EXCEPTIONS_PATH,
    FreezeError,
    evaluate,
    is_protected,
    load_exceptions,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Freeze Test")
    protected = repo / "src/michi/domain/signal_truth.py"
    protected.parent.mkdir(parents=True)
    protected.write_text("VALUE = 1\n", encoding="utf-8")
    test_file = repo / "tests/test_signal_truth.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_value():\n    assert True\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "baseline")
    return repo, _git(repo, "rev-parse", "HEAD").strip()


def _ledger(repo: Path, entry: dict[str, object]) -> None:
    path = repo / EXCEPTIONS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"exceptions": [entry]}), encoding="utf-8")


def test_protected_surface_is_explicit_and_shared_code_is_not_frozen() -> None:
    assert is_protected("src/michi/domain/signal_truth.py")
    assert is_protected("src/michi/infrastructure/audio_engines/gstreamer.py")
    assert is_protected("src/michi/application/dac_pcm_closure.py")
    assert is_protected("docs/audio/phase2/PHASE2_STATE.json")
    assert is_protected(
        "docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md"
    )
    assert not is_protected("tests/audio_phase2/test_signal_truth_frame_a42.py")
    assert not is_protected("docs/audio/phase2/evidence/run.json")
    assert not is_protected("src/michi/presentation/qml/shell/Sidebar.qml")
    assert not is_protected("src/michi_ecosystem/application/home_backup.py")


def test_productive_ap2_change_fails_without_an_exception(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    (repo / "src/michi/domain/signal_truth.py").write_text(
        "VALUE = 2\n", encoding="utf-8"
    )
    report = evaluate(repo, base)
    assert report["ok"] is False
    assert report["violations"] == ["src/michi/domain/signal_truth.py"]


def test_test_and_evidence_changes_are_allowed(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    (repo / "tests/test_signal_truth.py").write_text(
        "def test_new():\n    assert True\n", encoding="utf-8"
    )
    evidence = repo / "docs/audio/phase2/evidence/run.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    report = evaluate(repo, base)
    assert report["ok"] is True
    assert report["protected_changes"] == []


def test_owner_approved_exception_allows_exactly_that_path(tmp_path: Path) -> None:
    repo, base = _repo(tmp_path)
    _ledger(
        repo,
        {
            "path": "src/michi/domain/signal_truth.py",
            "reason": "Authorized critical playback fix",
            "authorized_by": "owner",
            "authorization": "OWNER_APPROVED",
        },
    )
    (repo / "src/michi/domain/signal_truth.py").write_text(
        "VALUE = 3\n", encoding="utf-8"
    )
    report = evaluate(repo, base)
    assert report["ok"] is True
    assert report["approved_exceptions"] == ["src/michi/domain/signal_truth.py"]


@pytest.mark.parametrize(
    "entry",
    [
        {
            "path": "src/michi/domain/signal_truth.py",
            "reason": "No owner",
            "authorization": "OWNER_APPROVED",
        },
        {
            "path": "src/michi/domain/signal_truth.py",
            "reason": "Wrong authorization",
            "authorized_by": "owner",
            "authorization": "SELF_APPROVED",
        },
        {
            "path": "src/michi/domain/signal_truth.py",
            "reason": "   ",
            "authorized_by": "owner",
            "authorization": "OWNER_APPROVED",
        },
    ],
)
def test_incomplete_exception_never_authorizes_a_change(
    tmp_path: Path, entry: dict[str, object]
) -> None:
    repo, base = _repo(tmp_path)
    _ledger(repo, entry)
    (repo / "src/michi/domain/signal_truth.py").write_text(
        "VALUE = 4\n", encoding="utf-8"
    )
    report = evaluate(repo, base)
    assert report["ok"] is False
    assert report["approved_exceptions"] == []


def test_malformed_exception_ledger_fails_closed(tmp_path: Path) -> None:
    repo, _ = _repo(tmp_path)
    path = repo / EXCEPTIONS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(FreezeError):
        load_exceptions(repo)
