"""Audio Phase 2 repository alignment gate (R11.1 §206).

Proves that an agent is not implementing against the wrong spec copy or a
locked phase: canonical spec/state/baseline/AGENTS presence, unique anchors,
state-vs-spec path agreement, phase mutability, closed dependencies and a
baseline commit that is an ancestor of HEAD. Emits a reproducible receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SPEC_REL = Path("docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md")
STATE_REL = Path("docs/audio/phase2/PHASE2_STATE.json")
BASELINE_REL = Path("docs/audio/phase2/audio_phase2_baseline.json")
AGENTS_REL = Path("AGENTS.md")
PHASE_IDS = tuple(f"AP2-F{index:02d}" for index in range(16))
MUTABLE_STATES = {"READY", "ACTIVE", "VERIFYING"}
AGENT_BEGIN = "<!-- MICHI_AUDIO_PHASE2_AGENT_CONTRACT_BEGIN -->"
AGENT_END = "<!-- MICHI_AUDIO_PHASE2_AGENT_CONTRACT_END -->"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail("STOP_PHASE2_STATE_INVALID", f"{path}: {exc}")


def phase_dependencies(spec_text: str, phase: str) -> tuple[str, ...]:
    begin = f"<!-- MICHI_PHASE2:PHASE:{phase}:BEGIN -->"
    end = f"<!-- MICHI_PHASE2:PHASE:{phase}:END -->"
    if spec_text.count(begin) != 1 or spec_text.count(end) != 1:
        fail("STOP_PHASE_ANCHOR_INVALID", phase)
    block = spec_text.split(begin, 1)[1].split(end, 1)[0]
    match = re.search(r"^DEPENDENCIES:\s*(.+)$", block, re.MULTILINE)
    if match is None:
        return ()
    return tuple(re.findall(r"AP2-F\d{2}", match.group(1)))


def verify(repo: Path, phase: str, require_mutable: bool) -> dict[str, object]:
    spec = repo / SPEC_REL
    state_path = repo / STATE_REL
    baseline_path = repo / BASELINE_REL
    agents_path = repo / AGENTS_REL
    if phase not in PHASE_IDS:
        fail("STOP_PHASE_UNKNOWN", phase)
    for path in (spec, state_path, baseline_path, agents_path):
        if not path.is_file():
            fail("STOP_PHASE2_REQUIRED_FILE_MISSING", str(path))

    spec_text = spec.read_text(encoding="utf-8")

    def anchor_count(anchor: str) -> int:
        return len(re.findall(rf"^{re.escape(anchor)}$", spec_text, re.MULTILINE))

    if anchor_count("<!-- MICHI_PHASE2:BOOTSTRAP:BEGIN -->") != 1:
        fail("STOP_SPEC_BOOTSTRAP_ANCHOR_INVALID", "BEGIN")
    if anchor_count("<!-- MICHI_PHASE2:BOOTSTRAP:END -->") != 1:
        fail("STOP_SPEC_BOOTSTRAP_ANCHOR_INVALID", "END")
    if anchor_count("<!-- MICHI_PHASE2:PHASE_INDEX:BEGIN -->") != 1:
        fail("STOP_PHASE_INDEX_ANCHOR_INVALID", "BEGIN")
    if anchor_count("<!-- MICHI_PHASE2:PHASE_INDEX:END -->") != 1:
        fail("STOP_PHASE_INDEX_ANCHOR_INVALID", "END")

    for phase_id in PHASE_IDS:
        if anchor_count(f"<!-- MICHI_PHASE2:PHASE:{phase_id}:BEGIN -->") != 1:
            fail("STOP_PHASE_ANCHOR_INVALID", f"{phase_id}:BEGIN")
        if anchor_count(f"<!-- MICHI_PHASE2:PHASE:{phase_id}:END -->") != 1:
            fail("STOP_PHASE_ANCHOR_INVALID", f"{phase_id}:END")

    agents_text = agents_path.read_text(encoding="utf-8")
    if agents_text.count(AGENT_BEGIN) != 1 or agents_text.count(AGENT_END) != 1:
        fail("STOP_AGENT_CONTRACT_MISSING", "AGENTS.md")

    state = load_json(state_path)
    baseline = load_json(baseline_path)
    state_spec = state.get("spec", {}).get("path")
    if state_spec != str(SPEC_REL):
        fail("STOP_SPEC_PATH_DRIFT", repr(state_spec))

    phase_states = state.get("phases", {})
    status = phase_states.get(phase)
    if status is None:
        fail("STOP_PHASE_STATE_MISSING", phase)
    if require_mutable and status not in MUTABLE_STATES:
        fail("STOP_PHASE_NOT_MUTABLE", f"{phase}={status}")

    for dependency in phase_dependencies(spec_text, phase):
        if phase_states.get(dependency) != "CLOSED":
            fail(
                "STOP_ENTRY_GATE_UNSATISFIED",
                f"{phase} requires {dependency}=CLOSED",
            )

    baseline_commit = baseline.get("git_commit") or state.get("baseline", {}).get(
        "git_commit"
    )
    if not baseline_commit:
        fail("STOP_BASELINE_MANIFEST_INVALID", "git_commit missing")
    head = run_git(repo, "rev-parse", "HEAD")
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "merge-base",
                "--is-ancestor",
                baseline_commit,
                head,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        fail(
            "STOP_BASELINE_DRIFT",
            f"baseline {baseline_commit} is not ancestor of {head}",
        )

    return {
        "phase": phase,
        "phase_state": status,
        "spec_path": str(SPEC_REL),
        "spec_sha256": sha256(spec),
        "baseline_commit": baseline_commit,
        "repo_head": head,
        "dependencies": phase_dependencies(spec_text, phase),
        "verdict": "GO",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verify_audio_phase2_repository_alignment")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--require-mutable", action="store_true")
    args = parser.parse_args(argv)
    receipt = verify(Path(args.repo).resolve(), args.phase, args.require_mutable)
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
