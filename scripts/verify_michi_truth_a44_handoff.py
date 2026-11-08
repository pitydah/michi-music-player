#!/usr/bin/env python3
"""AP2-F11 A44: bounded, read-only evidence ledger for Signal Truth handoff.

Two modes: `init` creates an explicitly incomplete receipt, `evaluate` validates
on-disk evidence against hashes and reports remaining gates. It NEVER executes
commands, changes source files, signs off hardware, or authorizes a release.

The validated receipt is still an *operator claim*, not independent proof of an
ALSA/DAC measurement. Human and canonical AP2/DAC review are mandatory even
when every gate reports PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from verify_michi_truth_a43_package import EXPECTED_HEAD, parse_patch

SCHEMA = "michi.ap2.f11.signal_truth.handoff.v1"
RESULT_SCHEMA = "michi.ap2.f11.signal_truth.handoff_evaluation.v1"
MAX_RECEIPT = 512 * 1024
MAX_EVIDENCE = 8 * 1024 * 1024
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
RUN_ID = re.compile(r"^[a-zA-Z0-9_.:-]{8,96}$")

# Every mandatory gate is explicit; no implicit family skip or silent pass.
GATES: dict[str, str] = {
    "canonical_context": "contract",
    "ap2_alignment": "contract",
    "dac_alignment": "contract",
    "patch_integrity": "integration",
    "post_migration_tree": "integration",
    "python_regressions": "integration",
    "qt_owner_dispatch": "qt",
    "qml_truth_frame": "qt",
    "kwin_a11y_dpr": "visual",
    "privacy_redaction": "privacy",
    "rt_perf_xrun": "performance",
    "rollback_drill": "integration",
    "ci_exact_sha": "ci",
    "pcm_direct": "hardware",
    "pcm_managed": "hardware",
    "native_dsd": "hardware",
    "dop": "hardware",
    "dsd_pcm": "hardware",
}
HARDWARE = frozenset(k for k, kind in GATES.items() if kind == "hardware")
STATUS = frozenset({"PASS", "FAIL", "BLOCKED", "NOT_RUN", "CAPABILITY_UNSUPPORTED"})
BOUNDARIES = frozenset(
    {
        "CANONICAL",
        "LOCAL_TREE",
        "SOFTWARE",
        "QT_OWNER",
        "QML",
        "KWIN",
        "OUTPUT_BOUNDARY",
        "DAC_RECEIVER",
        "CI_EXACT_SHA",
    }
)


@dataclass(frozen=True, slots=True)
class Evaluation:
    decision: str
    issues: tuple[str, ...]
    passed: tuple[str, ...]
    pending: tuple[str, ...]
    patch_sha256: str
    has_hardware_evidence: bool

    def to_json(self) -> dict[str, Any]:
        # Only stable gate codes, not private paths, filenames or log excerpts.
        return {
            "schema": RESULT_SCHEMA,
            "decision": self.decision,
            "issues": list(self.issues),
            "passed": list(self.passed),
            "pending": list(self.pending),
            "patch_sha256": self.patch_sha256,
            "hardware_evidence_claimed": self.has_hardware_evidence,
            "release_authorized": False,
            "repository_modified": False,
        }


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _patch_sha(path: Path, expected_sha256: str) -> str:
    if not isinstance(expected_sha256, str) or not HEX64.fullmatch(expected_sha256):
        raise ValueError("A44_SHA_PIN_INVALID")
    parse_patch(path)  # A43 cumulative manifest / path guard
    actual = _sha(path.read_bytes())
    if actual != expected_sha256:
        raise ValueError("A44_PATCH_HASH_MISMATCH")
    return actual


def initial_receipt(patch: Path, expected_sha256: str) -> dict[str, Any]:
    digest = _patch_sha(patch, expected_sha256)
    return {
        "schema": SCHEMA,
        "phase": "AP2-F11",
        "source_head": EXPECTED_HEAD,
        "candidate_sha": None,
        "patch_sha256": digest,
        "gates": {name: {"status": "NOT_RUN", "evidence": None} for name in GATES},
    }


def _safe_evidence_path(root: Path, name: object) -> Path:
    if (
        not isinstance(name, str)
        or not name
        or len(name) > 240
        or "\\" in name
        or name.startswith(("/", "~"))
        or "\x00" in name
    ):
        raise ValueError("A44_EVIDENCE_PATH_REFUSED")
    parts = name.split("/")
    rel = PurePosixPath(name)
    if (
        rel.is_absolute()
        or not rel.parts
        or any(
            not part or part in (".", "..") or part.startswith(".") for part in parts
        )
    ):
        raise ValueError("A44_EVIDENCE_PATH_REFUSED")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("A44_EVIDENCE_ROOT_INVALID")
    target = root
    for part in rel.parts:
        target /= part
        if target.is_symlink():
            raise ValueError("A44_EVIDENCE_SYMLINK_REFUSED")
    if not target.is_file() or not target.resolve().is_relative_to(root):
        raise ValueError("A44_EVIDENCE_NOT_FOUND")
    if not 0 < target.stat().st_size <= MAX_EVIDENCE:
        raise ValueError("A44_EVIDENCE_SIZE_REFUSED")
    return target


def _read_receipt(path: Path) -> dict[str, Any]:
    if (
        not path.is_file()
        or path.is_symlink()
        or not 0 < path.stat().st_size <= MAX_RECEIPT
    ):
        raise ValueError("A44_RECEIPT_MISSING_OR_UNBOUNDED")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("A44_RECEIPT_JSON_INVALID") from exc
    if not isinstance(data, dict):
        raise ValueError("A44_RECEIPT_STRUCTURE_INVALID")
    return data


def evaluate(
    receipt: dict[str, Any], patch: Path, expected_sha256: str, evidence_root: Path
) -> Evaluation:
    digest = _patch_sha(patch, expected_sha256)
    issues: list[str] = []
    passed: list[str] = []
    pending: list[str] = []
    if receipt.get("schema") != SCHEMA or receipt.get("phase") != "AP2-F11":
        issues.append("A44_RECEIPT_SCHEMA_OR_PHASE_INVALID")
    if receipt.get("source_head") != EXPECTED_HEAD:
        issues.append("A44_SOURCE_HEAD_MISMATCH")
    if receipt.get("patch_sha256") != digest:
        issues.append("A44_RECEIPT_PATCH_HASH_MISMATCH")
    candidate = receipt.get("candidate_sha")
    if candidate is not None and (
        not isinstance(candidate, str) or not SHA40.fullmatch(candidate)
    ):
        issues.append("A44_CANDIDATE_SHA_INVALID")
    rows = receipt.get("gates")
    if not isinstance(rows, dict) or set(rows) != set(GATES):
        issues.append("A44_GATE_MATRIX_INCOMPLETE_OR_UNKNOWN")
        rows = rows if isinstance(rows, dict) else {}
    hardware_pass = False
    for name, kind in GATES.items():
        row = rows.get(name)
        if not isinstance(row, dict) or row.get("status") not in STATUS:
            issues.append(f"A44_GATE_STATUS_INVALID:{name}")
            pending.append(name)
            continue
        state = row["status"]
        if state == "CAPABILITY_UNSUPPORTED" and kind != "hardware":
            issues.append(f"A44_UNSUPPORTED_NON_HARDWARE:{name}")
        if state != "PASS":
            pending.append(name)
            continue
        evidence = row.get("evidence")
        if not isinstance(evidence, dict):
            issues.append(f"A44_POSITIVE_WITHOUT_EVIDENCE:{name}")
            pending.append(name)
            continue
        run_id = evidence.get("run_id")
        checksum = evidence.get("sha256")
        boundary = evidence.get("boundary")
        exit_code = evidence.get("exit_code")
        if (
            not isinstance(run_id, str)
            or not RUN_ID.fullmatch(run_id)
            or not isinstance(checksum, str)
            or not HEX64.fullmatch(checksum)
            or boundary not in BOUNDARIES
            or type(exit_code) is not int
            or exit_code != 0
        ):
            issues.append(f"A44_EVIDENCE_FIELDS_INVALID:{name}")
            pending.append(name)
            continue
        if name in {"native_dsd", "dop"} and boundary != "DAC_RECEIVER":
            issues.append(f"A44_DAC_RECEIVER_NOT_EVIDENCED:{name}")
            pending.append(name)
            continue
        if kind == "hardware" and boundary not in {"OUTPUT_BOUNDARY", "DAC_RECEIVER"}:
            issues.append(f"A44_HARDWARE_BOUNDARY_INVALID:{name}")
            pending.append(name)
            continue
        if name == "ci_exact_sha" and (
            not candidate
            or boundary != "CI_EXACT_SHA"
            or evidence.get("subject_sha") != candidate
        ):
            issues.append("A44_CI_EXACT_SHA_NOT_PROVEN")
            pending.append(name)
            continue
        if name == "qt_owner_dispatch" and boundary != "QT_OWNER":
            issues.append("A44_QT_OWNER_BOUNDARY_INVALID")
            pending.append(name)
            continue
        if name == "qml_truth_frame" and boundary != "QML":
            issues.append("A44_QML_BOUNDARY_INVALID")
            pending.append(name)
            continue
        if name == "kwin_a11y_dpr" and boundary != "KWIN":
            issues.append("A44_KWIN_BOUNDARY_INVALID")
            pending.append(name)
            continue
        try:
            path = _safe_evidence_path(evidence_root, evidence.get("relative_path"))
            if _sha(path.read_bytes()) != checksum:
                raise ValueError("A44_EVIDENCE_HASH_MISMATCH")
        except (ValueError, OSError) as exc:
            code = (
                str(exc) if str(exc).startswith("A44_") else "A44_EVIDENCE_UNREADABLE"
            )
            issues.append(f"{code}:{name}")
            pending.append(name)
            continue
        passed.append(name)
        if kind == "hardware":
            hardware_pass = True
    if issues or len(passed) != len(GATES):
        decision = "NO_GO"
    else:
        # A JSON report is NOT an independent hardware certification,
        # even if every checksum matches. External owner approval is required.
        decision = "HUMAN_CANONICAL_REVIEW_REQUIRED"
    return Evaluation(
        decision,
        tuple(issues[:100]),
        tuple(passed),
        tuple(pending),
        digest,
        hardware_pass,
    )


def _new_private_json(
    destination: Path, obj: dict[str, Any], *, repo: Path | None = None
) -> None:
    target = destination.resolve(strict=False)
    if destination.is_symlink() or destination.parent.is_symlink():
        raise ValueError("A44_OUTPUT_SYMLINK_REFUSED")
    if repo is not None and target.is_relative_to(repo.resolve()):
        raise ValueError("A44_OUTPUT_WITHIN_REPOSITORY_REFUSED")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ValueError("A44_OUTPUT_DIRECTORY_INVALID")
    # Never overwrite a user's existing report or follow a symlink.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(obj, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("init", "evaluate"))
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--patch-sha256", required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == "init":
            if args.receipt is not None or args.evidence_root is not None:
                raise ValueError("A44_INIT_UNEXPECTED_ARGUMENT")
            data = initial_receipt(args.patch, args.patch_sha256)
        else:
            if args.receipt is None or args.evidence_root is None:
                raise ValueError("A44_EVALUATION_ARGUMENTS_MISSING")
            data = evaluate(
                _read_receipt(args.receipt),
                args.patch,
                args.patch_sha256,
                args.evidence_root,
            ).to_json()
        _new_private_json(args.output, data, repo=args.repo)
        print("A44_RECEIPT_INITIALIZED" if args.mode == "init" else data["decision"])
        return (
            0
            if args.mode == "init"
            else (0 if data["decision"] == "HUMAN_CANONICAL_REVIEW_REQUIRED" else 2)
        )
    except (ValueError, OSError) as exc:
        # No traceback and no private filename leak.
        code = str(exc) if str(exc).startswith("A44_") else "A44_UNVERIFIED_ERROR"
        print(code.split(":", 1)[0], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
