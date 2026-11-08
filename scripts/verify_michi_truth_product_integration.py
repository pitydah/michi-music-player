#!/usr/bin/env python3
"""AP2-F11: apply a candidate only to the exact full PR245 checkout.

This utility is intentionally stricter than a generic installer. It makes
no commits and never changes Git remotes, audio settings, or phase state.
The receipt cannot confer AP2/DAC or physical qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.verify_michi_truth_a43_package import (
        _load_migrator,
        verify_migrated_package,
    )
except ModuleNotFoundError:
    # Direct CLI invocation puts scripts/ (not its parent) on sys.path.
    from verify_michi_truth_a43_package import _load_migrator, verify_migrated_package

PR245_HEAD = "d32228fbcc49c4f107e4295b1a70e31fde4d9b07"
# These are Git blob SHA-1s read from GitHub at the exact PR245 HEAD.
# Avoid using synthetic/anchor-only preimages to claim product integration.
BASE_BLOBS = {
    "AGENTS.md": "c420ac7f989912f5b0ac911c1f3e2b84a1829bc2",
    "src/michi/application/output_session_service.py": (
        "db3228bdc9d385fb46f022a22a714ca92e0dc158"
    ),
    "src/michi/bootstrap/__init__.py": "bf6b63179cb1d33ba195ddc56d68afc17381163e",
    "src/michi/presentation/qml/player/SignalTruthPopup.qml": (
        "3ad6080b48d3f953a21b4d353592255d48f0db33"
    ),
    "src/michi/domain/signal_truth.py": "8859d9c6519807f20551a0f5650b40bcd277465a",
    "docs/audio/phase2/PHASE2_STATE.json": "f658cd4c6d5612525f7578e7e6662ee3f5ddbf57",
}
NECESSARY = (
    "AGENTS.md",
    "pyproject.toml",
    "src/michi/application/output_session_service.py",
    "src/michi/domain/signal_truth.py",
    "docs/audio/phase2/PHASE2_STATE.json",
    "scripts/phase2_context.py",
    "scripts/verify_audio_phase2_repository_alignment.py",
    "scripts/verify_dac_repository_alignment.py",
)
TEST_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("F03_REAL", ("tests/audio_phase2/test_signal_truth_semantic_gate_a38.py",)),
    ("F03_BASELINE", ("tests/audio_phase2/test_signal_path_service.py",)),
    ("OUTPUT_OWNER", ("tests/audio_phase2/test_signal_truth_output_owner_a37.py",)),
    (
        "RECORDER_CAUSAL",
        (
            "tests/audio_phase2/test_signal_truth_real_recorder_c6_a35.py",
            "tests/audio_phase2/test_signal_truth_delivery_a26.py",
            "tests/audio_phase2/test_signal_truth_a37_fallback.py",
        ),
    ),
    ("QT_BRIDGE", ("tests/audio_phase2/test_f11_signal_path_bridge.py",)),
    ("OWNER_DISPATCH", ("tests/audio_phase2/test_processing_owner_dispatch.py",)),
    ("RECORDER_RACE", ("tests/audio_phase2/test_signal_truth_concurrency.py",)),
    ("QML_CONTRACT", ("tests/test_f11_qml_contract.py",)),
    (
        "TRUTH_FRAME_A42",
        (
            "tests/audio_phase2/test_signal_truth_frame_a42.py",
            "tests/audio_phase2/test_signal_truth_frame_integration_a42.py",
        ),
    ),
    ("A43_PATCH_GUARDS", ("tests/audio_phase2/test_michi_truth_a43_package.py",)),
    ("A44_HANDOFF", ("tests/audio_phase2/test_michi_truth_a44_handoff.py",)),
    (
        "A46_DYNAMIC_STAGES",
        ("tests/audio_phase2/test_signal_truth_dynamic_stages_a46.py",),
    ),
    ("A46_R15C_MATRIX", ("tests/audio_phase2/test_michi_truth_r15c_matrix_a46.py",)),
    ("A47_P0_CONTRACT", ("tests/audio_phase2/test_michi_truth_p0_contract_a47.py",)),
)


@dataclass(frozen=True)
class Check:
    key: str
    status: str
    detail: str = ""

    def to_json(self) -> dict[str, str]:
        return {"id": self.key, "status": self.status, "detail": self.detail}


def command(
    cwd: Path, args: Sequence[str], *, timeout: int = 90, log_path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        run = subprocess.run(
            list(args),
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(args, 124, "", "command failed or timed out")
    if log_path is not None:
        log_path.write_text(
            run.stdout + "\n--- STDERR ---\n" + run.stderr, encoding="utf-8"
        )
    return run


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return command(cwd, ("git", *args))


def validate_checkout(
    repo: Path, *, expected_head: str = PR245_HEAD, already_patched: bool = False
) -> list[Check]:
    """Reject synthetic trees; verify baseline HEAD for already patched sources."""
    result: list[Check] = []
    head = git(repo, "rev-parse", "HEAD")
    actual_head = head.stdout.strip()
    result.append(
        Check(
            "EXACT_SHA",
            "PASS" if head.returncode == 0 and actual_head == expected_head else "FAIL",
            actual_head[:40],
        )
    )
    if not already_patched:
        status = git(repo, "status", "--porcelain", "--untracked-files=normal")
        result.append(
            Check(
                "WORKTREE_CLEAN",
                "PASS"
                if status.returncode == 0 and not status.stdout.strip()
                else "FAIL",
            )
        )
    tracked = git(repo, "ls-files", "-z")
    entries = {p for p in tracked.stdout.split("\0") if p}
    # Full PR245 tree has 1593 tracked blobs; 1000 is deliberately conservative.
    result.append(
        Check(
            "FULL_CHECKOUT",
            "PASS"
            if tracked.returncode == 0
            and len(entries) >= 1000
            and all(p in entries for p in NECESSARY)
            else "FAIL",
            f"tracked={len(entries)}",
        )
    )
    for path, expected_blob in BASE_BLOBS.items():
        if path not in entries or not (repo / path).is_file():
            result.append(Check("BLOB:" + path, "FAIL", "missing"))
            continue
        digest = (
            git(repo, "rev-parse", "HEAD:" + path)
            if already_patched
            else git(repo, "hash-object", "--", path)
        )
        valid = digest.returncode == 0 and digest.stdout.strip() == expected_blob
        result.append(
            Check(
                "BLOB:" + path, "PASS" if valid else "FAIL", digest.stdout.strip()[:40]
            )
        )
    return result


def junit_summary(path: Path) -> dict[str, int] | None:
    try:
        xml = ET.parse(path).getroot()
        suites = [xml] if xml.tag == "testsuite" else list(xml.iter("testsuite"))
        if not suites:
            return None
        result = {
            key: sum(int(s.attrib.get(key, "0")) for s in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        if result["tests"] == 0:
            return None
        return result
    except (ET.ParseError, ValueError, OSError):
        return None


def execute_gates(
    repo: Path,
    artifact_dir: Path,
    *,
    migrated: bool = False,
    expected_head: str = PR245_HEAD,
) -> list[Check]:
    """No synthetic PASS: only checks running on the full live checkout count."""
    py = sys.executable
    cmds: list[tuple[str, tuple[str, ...], int]] = [
        (
            "AP2_CONTEXT",
            (py, "scripts/phase2_context.py", "--phase", "AP2-F11", "--receipt-json"),
            60,
        ),
        (
            "AP2_ALIGNMENT",
            (
                py,
                "scripts/verify_audio_phase2_repository_alignment.py",
                "--phase",
                "AP2-F11",
            ),
            120,
        ),
        ("DAC_ALIGNMENT", (py, "scripts/verify_dac_repository_alignment.py"), 120),
        ("PATCH_WHITESPACE", ("git", "diff", "--check"), 30),
        (
            "PYTHON_COMPILE",
            (
                py,
                "-m",
                "compileall",
                "-q",
                "src/michi/application",
                "src/michi/domain",
                "src/michi/presentation",
            ),
            120,
        ),
    ]
    checks: list[Check] = []
    for key, args, timeout in cmds:
        run = command(repo, args, timeout=timeout, log_path=artifact_dir / f"{key}.log")
        checks.append(
            Check(
                key, "PASS" if run.returncode == 0 else "FAIL", f"exit={run.returncode}"
            )
        )
    groups = TEST_GROUPS
    if migrated:
        renamed = {
            "tests/audio_phase2/test_signal_path_service.py": (
                "tests/audio_phase2/test_signal_truth_projection_service.py"
            ),
            "tests/audio_phase2/test_f11_signal_path_bridge.py": (
                "tests/audio_phase2/test_f11_signal_truth_bridge.py"
            ),
        }
        groups = tuple(
            (key, tuple(renamed.get(p, p) for p in paths)) for key, paths in TEST_GROUPS
        )
        # The auditor's git ls-files inventory is pre-stage. A41 verify scans
        # actual renamed worktree paths without modifying the Git index.
        gate = command(
            repo,
            (
                py,
                "scripts/migrate_michi_truth_names_a41.py",
                "--repo",
                str(repo),
                "--mode",
                "verify",
            ),
            timeout=45,
            log_path=artifact_dir / "MIGRATED_NAMING.log",
        )
        checks.append(
            Check(
                "MIGRATED_NAMING",
                "PASS" if gate.returncode == 0 else "FAIL",
                f"exit={gate.returncode}",
            )
        )
    for key, paths in groups:
        xml_path = artifact_dir / f"{key}.xml"
        run = command(
            repo,
            (py, "-m", "pytest", "-q", "-ra", "--junitxml", str(xml_path), *paths),
            timeout=180,
            log_path=artifact_dir / f"{key}.log",
        )
        counts = junit_summary(xml_path)
        ok = (
            run.returncode == 0
            and counts is not None
            and counts["skipped"] == 0
            and not (counts["errors"] or counts["failures"])
        )
        checks.append(
            Check(
                key, "PASS" if ok else "FAIL", f"exit={run.returncode}; junit={counts}"
            )
        )
    head = git(repo, "rev-parse", "HEAD")
    checks.append(
        Check(
            "HEAD_UNCHANGED",
            "PASS"
            if head.returncode == 0 and head.stdout.strip() == expected_head
            else "FAIL",
        )
    )
    for key, relative in (
        ("GOVERNANCE_AGENTS", "AGENTS.md"),
        ("GOVERNANCE_PHASE_STATE", "docs/audio/phase2/PHASE2_STATE.json"),
    ):
        if migrated:
            # Only the approved name substitution may change governance
            # references. In particular, the phase state's historical hash
            # is preserved instead of rewriting an AP2 release receipt.
            try:
                _replace = _load_migrator(
                    repo / "scripts/migrate_michi_truth_names_a41.py"
                )._replace
                baseline = git(repo, "show", "HEAD:" + relative)
                expected = _replace(baseline.stdout, relative)
                passed = (
                    baseline.returncode == 0
                    and (repo / relative).read_text(encoding="utf-8") == expected
                )
            except (OSError, UnicodeError, ValueError, ImportError):
                passed = False
        else:
            digest = git(repo, "hash-object", "--", relative)
            passed = (
                digest.returncode == 0 and digest.stdout.strip() == BASE_BLOBS[relative]
            )
        checks.append(Check(key, "PASS" if passed else "FAIL"))
    return checks


def eligible(checks: Sequence[Check]) -> bool:
    return bool(checks) and all(x.status == "PASS" for x in checks)


def run_integration(
    repo: Path,
    patch: Path,
    *,
    apply: bool = False,
    verify_applied: bool = False,
    verify_migrated: bool = False,
    expected_head: str = PR245_HEAD,
    output: Path | None = None,
    expected_patch_sha256: str | None = None,
) -> dict:
    repo, patch = repo.resolve(), patch.resolve()
    temp = Path(tempfile.mkdtemp(prefix="michi_truth_a39_"))
    os.chmod(temp, 0o700)
    if int(apply) + int(verify_applied) + int(verify_migrated) > 1:
        raise ValueError("choose one of --apply / --verify-applied / --verify-migrated")
    checks = validate_checkout(
        repo,
        expected_head=expected_head,
        already_patched=verify_applied or verify_migrated,
    )
    patch_digest = (
        hashlib.sha256(patch.read_bytes()).hexdigest() if patch.is_file() else None
    )
    if expected_patch_sha256 is not None:
        valid_hash = (
            len(expected_patch_sha256) == 64
            and all(c in "0123456789abcdef" for c in expected_patch_sha256)
            and patch_digest == expected_patch_sha256
        )
        checks.append(Check("PATCH_SHA256_PIN", "PASS" if valid_hash else "FAIL"))
    if eligible(checks) and patch.is_file():
        if verify_migrated:
            mirrored = verify_migrated_package(repo, patch, expected_head=expected_head)
            checks.append(
                Check(
                    "A43_MIGRATED_MIRROR",
                    "PASS"
                    if mirrored.status == "MATCHED_PENDING_PRODUCT_GATES"
                    else "FAIL",
                    ";".join(mirrored.issues)
                    if mirrored.issues
                    else f"checked={mirrored.checked_files}",
                )
            )
        else:
            probe = (
                git(repo, "apply", "--reverse", "--check", str(patch))
                if verify_applied
                else git(repo, "apply", "--check", str(patch))
            )
            checks.append(
                Check(
                    "PATCH_REVERSE_CHECK" if verify_applied else "PATCH_PRECHECK",
                    "PASS" if probe.returncode == 0 else "FAIL",
                    f"exit={probe.returncode}",
                )
            )
    else:
        checks.append(Check("PATCH_PRECHECK", "NOT_RUN", "checkout or patch invalid"))
    applied = False
    if verify_migrated and eligible(checks):
        applied = True
        checks.append(
            Check("PATCH_APPLIED", "PASS", "full local mirror matches renamed worktree")
        )
        checks.extend(
            execute_gates(repo, temp, migrated=True, expected_head=expected_head)
        )
    elif verify_applied and eligible(checks):
        applied = True  # Reverse-check proves the exact diff exists in worktree.
        checks.append(Check("PATCH_APPLIED", "PASS", "reverse-check on checkout"))
        checks.extend(execute_gates(repo, temp, expected_head=expected_head))
    elif apply and eligible(checks):
        result = git(repo, "apply", str(patch))
        applied = result.returncode == 0
        checks.append(
            Check(
                "PATCH_APPLIED",
                "PASS" if applied else "FAIL",
                f"exit={result.returncode}",
            )
        )
        if applied:
            checks.extend(execute_gates(repo, temp, expected_head=expected_head))
    else:
        checks.append(Check("PATCH_APPLIED", "NOT_RUN", "dry run or refusal"))
    state = (
        "SOFTWARE_INTEGRATION_CANDIDATE"
        if applied and eligible(checks)
        else "PATCH_APPLIED_GATES_BLOCKED"
        if applied
        else "PREFLIGHT_OK_NO_MUTATION"
        if eligible(checks[:-1])
        else "STOP_NO_MUTATION"
    )
    receipt = {
        "schema": "michi.signal_truth.a43.integration_receipt.v1",
        "status": state,
        "base_expected_head": expected_head,
        "patch_sha256": patch_digest,
        "patch_applied": applied,
        "verification_scope": (
            "FULL_LOCAL_POST_MIGRATION"
            if applied and verify_migrated
            else "FULL_LOCAL_CHECKOUT"
            if applied
            else "PREFLIGHT_ONLY"
        ),
        "physical_dac_verified": False,
        "qt_kwin_visual_verified": False,
        "github_commit_created": False,
        "github_ci_verified": False,
        "tests_required_without_skips": True,
        "checks": [x.to_json() for x in checks],
        "log_directory": str(temp),
    }
    receipt_path = output.resolve() if output is not None else temp / "receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    receipt["receipt_path"] = str(receipt_path)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--expected-head", default=PR245_HEAD)
    parser.add_argument(
        "--apply", action="store_true", help="Modify ONLY local checkout"
    )
    parser.add_argument(
        "--verify-applied",
        action="store_true",
        help="Verify a patch already applied BEFORE the A41 naming migration",
    )
    parser.add_argument(
        "--verify-migrated",
        action="store_true",
        help="Read-only full LOCAL mirror after approved A41 naming migration",
    )
    parser.add_argument(
        "--patch-sha256",
        default=None,
        help="Refuse a candidate whose SHA-256 differs from the Drive handoff",
    )
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    result = run_integration(
        args.repo,
        args.patch,
        apply=args.apply,
        verify_applied=args.verify_applied,
        verify_migrated=args.verify_migrated,
        expected_head=args.expected_head,
        output=args.receipt,
        expected_patch_sha256=args.patch_sha256,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "patch_applied": result["patch_applied"],
                "checks": result["checks"],
                "receipt_path": result["receipt_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return (
        0
        if result["status"]
        in ("PREFLIGHT_OK_NO_MUTATION", "SOFTWARE_INTEGRATION_CANDIDATE")
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
