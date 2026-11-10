#!/usr/bin/env python3
"""Verify that the Audio Phase 2 research freeze is still effective.

The freeze protects productive AP2 signal-truth, DSP, DAC and output files while
leaving tests, evidence and documentation available for read-only research.
An intentional critical correction must be declared in the exception ledger
with an explicit owner authorization; it is never inferred from a commit alone.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

AP2_FREEZE_BASELINE = "d2385fea2bd0a229ff8bce24000dcd07e895e0c1"
EXCEPTIONS_PATH = "docs/audio/phase2/AP2_RESEARCH_FREEZE_EXCEPTIONS.json"

PROTECTED_PATTERNS = (
    "src/michi/domain/signal_truth*.py",
    "src/michi/domain/truth_graph.py",
    "src/michi/application/signal_path_service.py",
    "src/michi/application/signal_truth*.py",
    "src/michi/application/audio_processing_service.py",
    "src/michi/application/output_session_service.py",
    "src/michi/application/dac_*.py",
    "src/michi/presentation/signal_path_bridge.py",
    "src/michi/presentation/qml/player/SignalTruthPopup.qml",
    "src/michi/presentation/qml/components/MichiSignal*.qml",
    "src/michi/presentation/qml/components/MichiAudioRouteIcon.qml",
    "src/michi/presentation/qml/components/Dac*.qml",
    "src/michi/infrastructure/audio_engines/**",
    "src/michi/infrastructure/audio_devices/**",
    "src/michi/infrastructure/audio_output/**",
    "src/michi/infrastructure/audio_processing/**",
    "docs/audio/phase2/PHASE2_STATE.json",
    "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md",
    "docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md",
)

ALLOWED_PREFIXES = ("tests/", "docs/audio/phase2/evidence/", "artifacts/")


class FreezeError(RuntimeError):
    """The freeze could not be evaluated safely."""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FreezeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def is_protected(path: str) -> bool:
    """Return whether a repository path belongs to the frozen productive surface."""

    normalized = path.replace("\\", "/")
    if normalized.startswith(ALLOWED_PREFIXES):
        return False
    return any(
        fnmatch.fnmatchcase(normalized, pattern) for pattern in PROTECTED_PATTERNS
    )


def changed_paths(repo: Path, base: str) -> list[str]:
    """Tracked and untracked paths changed relative to the freeze baseline."""

    _git(repo, "cat-file", "-e", f"{base}^{{commit}}")
    tracked = _git(repo, "diff", "--name-only", base, "--").splitlines()
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({path for path in (*tracked, *untracked) if path})


def load_exceptions(repo: Path) -> dict[str, dict[str, object]]:
    """Load the owner-approved exception ledger, if it exists."""

    path = repo / EXCEPTIONS_PATH
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FreezeError(f"invalid exception ledger: {exc}") from exc
    entries = payload.get("exceptions", [])
    if not isinstance(entries, list):
        raise FreezeError("exception ledger must contain an exceptions list")
    result: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise FreezeError("exception entries must be objects")
        target = entry.get("path")
        if not isinstance(target, str) or not target:
            raise FreezeError("exception entries need a path")
        result[target.replace("\\", "/")] = entry
    return result


def approved_exception(entry: dict[str, object] | None) -> bool:
    """An exception is valid only with explicit owner authorization and a reason."""

    if not entry:
        return False
    return (
        entry.get("authorization") == "OWNER_APPROVED"
        and isinstance(entry.get("authorized_by"), str)
        and bool(entry["authorized_by"].strip())
        and isinstance(entry.get("reason"), str)
        and bool(entry["reason"].strip())
    )


def evaluate(repo: Path, base: str = AP2_FREEZE_BASELINE) -> dict[str, object]:
    """Evaluate the freeze without mutating the repository."""

    repo = repo.resolve()
    exceptions = load_exceptions(repo)
    violations: list[str] = []
    approved: list[str] = []
    for path in changed_paths(repo, base):
        if not is_protected(path):
            continue
        entry = exceptions.get(path)
        if approved_exception(entry):
            approved.append(path)
        else:
            violations.append(path)
    return {
        "schema": "michi.ap2.research_freeze.v1",
        "base": base,
        "protected_changes": sorted(set(approved) | set(violations)),
        "approved_exceptions": approved,
        "violations": violations,
        "ok": not violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--base", default=AP2_FREEZE_BASELINE)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(Path(args.repo), args.base)
    except FreezeError as exc:
        print(
            f"[FAIL] AP2 research freeze could not be evaluated: {exc}", file=sys.stderr
        )
        return 2
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["violations"]:
        print("[FAIL] AP2 research freeze violations:", file=sys.stderr)
        for path in report["violations"]:
            print(f"  - {path}", file=sys.stderr)
        print(
            "Add an OWNER_APPROVED entry to the exception ledger only when the "
            "correction was explicitly authorized.",
            file=sys.stderr,
        )
        return 1
    count = len(report["protected_changes"])
    print(f"[PASS] AP2 research freeze is effective ({count} approved changes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
