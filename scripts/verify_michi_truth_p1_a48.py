#!/usr/bin/env python3
"""A48 package-only static verifier. 0 exit means P1 files coherent, NOT product GO.

No repository mutation, network request, GitHub integration or DAC proof.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

PATHS = (
    "src/michi/application/signal_truth_p1_ui.py",
    "src/michi/application/signal_truth_p1_metrics.py",
    "src/michi/application/signal_truth_p1_scheduler.py",
    "src/michi/application/signal_truth_p1_diagnostics.py",
    "src/michi/application/signal_truth_p1_capabilities.py",
    "src/michi/application/signal_truth_p1_remote_receipts.py",
    "src/michi/presentation/qml/components/MichiSignalTruthMetrics.qml",
    "tests/audio_phase2/test_michi_truth_p1_a48.py",
    "tests/audio_phase2/test_michi_truth_p1_package_a48.py",
    "docs/audio/phase2/F11_SIGNAL_TRUTH_A48_P1_CANONICAL.md",
    "docs/audio/phase2/F11_SIGNAL_TRUTH_A48_P1_ACCEPTANCE.json",
)
GATES = ("P1-UI", "P1-METRICS", "P1-PERF", "P1-DIAG", "P1-DSP", "P1-REMOTE")


def check(root: Path) -> dict[str, object]:
    failures = []
    digests = {}
    for path in PATHS:
        file = root / path
        if not file.is_file() or file.is_symlink():
            failures.append(f"MISSING_OR_LINK:{path}")
            continue
        raw = file.read_bytes()
        if len(raw) > 120000:
            failures.append(f"OVERSIZE:{path}")
        digests[path] = hashlib.sha256(raw).hexdigest()
        if path.endswith(".py"):
            try:
                ast.parse(raw.decode("utf-8"), filename=path)
            except (SyntaxError, UnicodeDecodeError):
                failures.append(f"INVALID_PYTHON:{path}")
    matrix = root / "docs/audio/phase2/F11_SIGNAL_TRUTH_A48_P1_ACCEPTANCE.json"
    if matrix.exists():
        try:
            x = json.loads(matrix.read_text(encoding="utf-8"))
            gates = x["gates"]
            if (
                x.get("schema") != "michi.ap2.f11.signal_truth.p1_acceptance.a48.v1"
                or len(gates) != 6
            ):
                failures.append("P1_SCHEMA_OR_GATE_COUNT")
            ids = [g["gate_id"] for g in gates]
            if tuple(ids) != GATES:
                failures.append("P1_GATE_ORDER")
            if any(
                g.get("product_state") != "NOT_RUN"
                or g.get("product_evidence") is not None
                for g in gates
            ):
                failures.append("P1_PRODUCT_PASS_FORGED")
            if any(g.get("candidate_state") != "SYNTHETIC_PASS" for g in gates):
                failures.append("P1_SYNTHETIC_STATE_MISSING")
            if any(x.get("assertions", {}).values()):
                failures.append("P1_FORGED_PRODUCT_SUCCESS")
            if any(v != "NOT_RUN_PRODUCT" for v in x.get("p0_remainder", {}).values()):
                failures.append("P0_LEDGER_TAMPERED")
            if set(x.get("r15c_related", {})) != {
                "R15C-39",
                "R15C-44",
                "R15C-45",
                "R15C-46",
                "R15C-47",
            }:
                failures.append("P1_R15C_COVERAGE_MISSING")
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            failures.append("P1_MATRIX_INVALID")
    qml = root / PATHS[6]
    if qml.exists():
        s = qml.read_text(encoding="utf-8")
        if "Popup {" in s or "Timer {" in s or "AudioProcessingService" in s:
            failures.append("P1_QML_ILLEGAL_OWNER")
        if (
            "Repeater {" not in s
            or "Accessible.name:" not in s
            or "Not observed" not in s
        ):
            failures.append("P1_QML_A11Y_OR_UNCERTAINTY")
    return {
        "schema": "michi.ap2.f11.signal_truth.a48.preflight.v1",
        "candidate_static_preflight": "PASS" if not failures else "FAIL",
        "full_product_status": "NOT_RUN",
        "github_mutation": False,
        "failures": failures,
        "paths_sha256": digests,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    verdict = check(args.repo.resolve())
    output = json.dumps(verdict, ensure_ascii=False, sort_keys=True, indent=2)
    if args.out:
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0 if verdict["candidate_static_preflight"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
