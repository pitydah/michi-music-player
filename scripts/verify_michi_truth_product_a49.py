#!/usr/bin/env python3
"""A49 offline, read-only product-source integration gate (no GitHub writes).

Clones the existing *local* checkout into a temporary directory at the exact
baseline SHA, applies the one cumulative patch ONLY THERE, runs AP2/DAC and
focused tests, and emits a receipt outside the checkout. Never creates commits,
PRs, branches in the source, pushes, or writes the original working tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

REQUIRED = (
    "AGENTS.md",
    "pyproject.toml",
    "src/michi/domain/signal_truth.py",
    "src/michi/application/signal_path_service.py",
    "src/michi/application/audio_processing_service.py",
    "src/michi/application/output_session_service.py",
    "src/michi/presentation/signal_path_bridge.py",
    "src/michi/presentation/qml/player/SignalTruthPopup.qml",
    "scripts/phase2_context.py",
    "scripts/verify_audio_phase2_repository_alignment.py",
    "scripts/verify_dac_repository_alignment.py",
)


def command(argv: list[str], cwd: Path, timeout: int = 180) -> dict[str, object]:
    try:
        run = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=dict(
                os.environ, QT_QPA_PLATFORM="offscreen", PYTHONDONTWRITEBYTECODE="1"
            ),
        )
        return {
            "status": "PASS" if run.returncode == 0 else "FAIL",
            "exit_code": run.returncode,
            "stdout_tail": run.stdout[-1600:],
            "stderr_tail": run.stderr[-1600:],
        }
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "NOT_RUN", "reason": "COMMAND_UNAVAILABLE_OR_TIMEOUT"}


def validate_source(root: Path, sha: str) -> str | None:
    if any(not (root / p).is_file() for p in REQUIRED):
        return "INCOMPLETE_REPOSITORY"
    r = command(["git", "rev-parse", "HEAD"], root, 15)
    if r["status"] != "PASS":
        return "HEAD_UNAVAILABLE"
    if str(r.get("stdout_tail", "")).strip() != sha:
        return "HEAD_MISMATCH"
    return None


def run(argv: list[str] | None = None) -> dict[str, object]:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--patch", type=Path, required=True)
    ap.add_argument("--baseline-sha", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    repo = args.repo.resolve()
    patch = args.patch.resolve()
    baseline = args.baseline_sha
    receipt = {
        "schema": "michi.ap2.f11.a49.offline_product_gate.v1",
        "baseline_sha": baseline,
        "candidate_sha": "UNCOMMITTED_LOCAL_PATCH",
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest()
        if patch.is_file()
        else None,
        "github_mutated": False,
        "original_checkout_mutated": False,
        "physical_dac": "NOT_RUN",
        "kwin": "NOT_RUN",
        "remote_ci_exact_sha": "NOT_RUN",
        "overall": "NO_GO",
        "checks": {},
    }
    blocker = validate_source(repo, baseline)
    if blocker:
        receipt["blocker"] = blocker
    elif not patch.is_file():
        receipt["blocker"] = "PATCH_MISSING"
    else:
        # Root remains unchanged: every test and patch application occurs in a
        # temp local clone, NOT a GitHub branch or a PR.
        with tempfile.TemporaryDirectory(prefix="michi-f11-a49-") as td:
            sandbox = Path(td) / "repo"
            clone = command(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-hardlinks",
                    "--local",
                    str(repo),
                    str(sandbox),
                ],
                Path(td),
                90,
            )
            receipt["checks"]["local_clone"] = clone
            if clone["status"] == "PASS":
                checkout = command(
                    ["git", "checkout", "--quiet", "--detach", baseline], sandbox, 45
                )
                receipt["checks"]["baseline_checkout"] = checkout
                if checkout["status"] == "PASS":
                    check = command(
                        ["git", "apply", "--check", str(patch)], sandbox, 45
                    )
                    receipt["checks"]["git_apply_check"] = check
                    if check["status"] == "PASS":
                        applied = command(["git", "apply", str(patch)], sandbox, 45)
                        receipt["checks"]["git_apply"] = applied
                        if applied["status"] == "PASS":
                            for name, cmd in (
                                (
                                    "phase_context",
                                    [
                                        "python",
                                        "scripts/phase2_context.py",
                                        "--phase",
                                        "AP2-F11",
                                        "--receipt-json",
                                    ],
                                ),
                                (
                                    "ap2_alignment",
                                    [
                                        "python",
                                        "scripts/verify_audio_phase2_repository_alignment.py",
                                        "--phase",
                                        "AP2-F11",
                                    ],
                                ),
                                (
                                    "dac_alignment",
                                    [
                                        "python",
                                        "scripts/verify_dac_repository_alignment.py",
                                    ],
                                ),
                                (
                                    "signal_truth_tests",
                                    [
                                        "python",
                                        "-m",
                                        "pytest",
                                        "-q",
                                        "-p",
                                        "no:cacheprovider",
                                        "tests/audio_phase2/test_signal_truth_concurrency.py",
                                        "tests/audio_phase2/test_michi_truth_a49_owner_metrics.py",
                                    ],
                                ),
                                (
                                    "qt_contract_tests",
                                    [
                                        "python",
                                        "-m",
                                        "pytest",
                                        "-q",
                                        "-p",
                                        "no:cacheprovider",
                                        "tests/test_f11_qml_contract.py",
                                        "tests/test_f11_kwin_visual_contract.py",
                                        "tests/audio_phase2/test_f11_signal_path_bridge.py",
                                    ],
                                ),
                            ):
                                receipt["checks"][name] = command(cmd, sandbox, 240)
                            receipt["checks"]["diff_check"] = command(
                                ["git", "diff", "--check"], sandbox, 45
                            )
                            reverse = command(
                                ["git", "apply", "--reverse", "--check", str(patch)],
                                sandbox,
                                45,
                            )
                            receipt["checks"]["git_reverse_check"] = reverse
                            # Without real Qt/KWin/physical DAC/exact-SHA CI,
                            # always NO-GO.
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    r = run()
    print(
        json.dumps(
            {
                "overall": r["overall"],
                "blocker": r.get("blocker"),
                "checks": {k: v["status"] for k, v in r["checks"].items()},
            }
        )
    )
    raise SystemExit(2 if r["overall"] == "NO_GO" else 0)
