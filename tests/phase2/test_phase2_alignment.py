"""verify_audio_phase2_repository_alignment (R11.1 §206) — agent gate."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "phase2_alignment", ROOT / "scripts/verify_audio_phase2_repository_alignment.py"
)
alignment = importlib.util.module_from_spec(SPEC)
sys.modules["phase2_alignment"] = alignment
SPEC.loader.exec_module(alignment)


def _spec_text(phase_statuses: dict[str, str] | None = None) -> str:
    blocks = [
        "<!-- MICHI_PHASE2:BOOTSTRAP:BEGIN -->\nbootstrap\n"
        "<!-- MICHI_PHASE2:BOOTSTRAP:END -->",
        "<!-- MICHI_PHASE2:PHASE_INDEX:BEGIN -->\nindex\n"
        "<!-- MICHI_PHASE2:PHASE_INDEX:END -->",
    ]
    for index in range(16):
        phase = f"AP2-F{index:02d}"
        dependencies = "NONE" if index == 0 else f"AP2-F{index - 1:02d}"
        blocks.append(
            f"<!-- MICHI_PHASE2:PHASE:{phase}:BEGIN -->\n"
            f"PHASE_ID: {phase}\nDEPENDENCIES: {dependencies}\n"
            f"MUST_READ_ANCHORS: R11-F00\n"
            f"<!-- MICHI_PHASE2:PHASE:{phase}:END -->"
        )
    return "\n".join(blocks) + "\n"


def _tree(tmp_path: Path, *, statuses: dict[str, str] | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "docs/audio/phase2").mkdir(parents=True)
    (repo / alignment.SPEC_REL).write_text(_spec_text(), encoding="utf-8")
    states = {f"AP2-F{index:02d}": "LOCKED" for index in range(16)}
    states.update({"AP2-F00": "CLOSED", "AP2-F01": "ACTIVE"})
    if statuses:
        states.update(statuses)
    (repo / alignment.STATE_REL).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "spec": {"path": str(alignment.SPEC_REL)},
                "baseline": {"git_commit": "pending"},
                "phases": states,
            }
        ),
        encoding="utf-8",
    )
    (repo / alignment.AGENTS_REL).write_text(
        alignment.AGENT_BEGIN + "\nagent hook\n" + alignment.AGENT_END + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=test@test",
            "-c",
            "user.name=test",
            "commit",
            "-q",
            "-m",
            "baseline",
        ],
        check=True,
    )
    commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    (repo / alignment.BASELINE_REL).write_text(
        json.dumps({"git_commit": commit}), encoding="utf-8"
    )
    return repo


def test_alignment_go_for_active_phase(tmp_path: Path) -> None:
    receipt = alignment.verify(_tree(tmp_path), "AP2-F01", require_mutable=True)
    assert receipt["verdict"] == "GO"
    assert receipt["phase_state"] == "ACTIVE"
    assert receipt["spec_sha256"]


def test_alignment_unknown_phase_stops(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="STOP_PHASE_UNKNOWN"):
        alignment.verify(_tree(tmp_path), "AP2-F99", require_mutable=False)


def test_alignment_locked_phase_is_not_mutable(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="STOP_PHASE_NOT_MUTABLE"):
        alignment.verify(_tree(tmp_path), "AP2-F02", require_mutable=True)


def test_alignment_open_dependency_stops(tmp_path: Path) -> None:
    repo = _tree(tmp_path, statuses={"AP2-F00": "LOCKED"})
    with pytest.raises(SystemExit, match="STOP_ENTRY_GATE_UNSATISFIED"):
        alignment.verify(repo, "AP2-F01", require_mutable=False)


def test_alignment_missing_agent_contract_stops(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    (repo / alignment.AGENTS_REL).write_text("no hook\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="STOP_AGENT_CONTRACT_MISSING"):
        alignment.verify(repo, "AP2-F01", require_mutable=False)


def test_alignment_baseline_drift_stops(tmp_path: Path) -> None:
    repo = _tree(tmp_path)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    (repo / alignment.BASELINE_REL).write_text(
        json.dumps({"git_commit": "0" * 40}), encoding="utf-8"
    )
    assert head  # sanity: the tree has a real history
    with pytest.raises(SystemExit, match="STOP_BASELINE_DRIFT"):
        alignment.verify(repo, "AP2-F01", require_mutable=False)
