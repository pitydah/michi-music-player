#!/usr/bin/env python3
"""A49: conservative executable R15C product gate, no GitHub mutations.

The 50 research cases are NOT the same as 50 product tests. Only explicit
existing pytest node IDs on a verified local product checkout can pass.
SKIP, missing links, unknown pytest exits, and absent physical receipts do
not count as PASS. Results are always written outside the product root.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

NEEDED = (
    "AGENTS.md",
    "pyproject.toml",
    "src/michi/domain/signal_truth.py",
    "src/michi/application/audio_processing_service.py",
    "src/michi/application/output_session_service.py",
    "src/michi/presentation/signal_path_bridge.py",
    "src/michi/presentation/qml/player/SignalTruthPopup.qml",
)


def checkout_status(
    root: Path, required_sha: str, *, allow_local_patch: bool = False
) -> tuple[bool, str]:
    if any(not (root / path).is_file() for path in NEEDED):
        return False, "INCOMPLETE_PRODUCT_CHECKOUT"
    try:
        h = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, "GIT_HEAD_UNAVAILABLE"
    if h.returncode or not h.stdout.strip():
        return False, "GIT_HEAD_UNAVAILABLE"
    if h.stdout.strip() != required_sha:
        return False, "CHECKOUT_SHA_MISMATCH"
    dirty = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if dirty.returncode:
        return False, "CHECKOUT_STATUS_UNAVAILABLE"
    if dirty.stdout.strip():
        return (
            (True, "LOCAL_PATCH_UNCOMMITTED_NO_CI_SHA")
            if allow_local_patch
            else (False, "DIRTY_CHECKOUT_NOT_AUTHORIZED")
        )
    return True, h.stdout.strip()


def validate_nodes(nodes: object, root: Path) -> tuple[str, ...]:
    if not isinstance(nodes, list) or not nodes:
        return ()
    out = []
    for node in nodes:
        if not isinstance(node, str) or "\x00" in node or not node.startswith("tests/"):
            return ()
        path = node.split("::")[0]
        if (
            ".." in Path(path).parts
            or not path.endswith(".py")
            or not (root / path).is_file()
        ):
            return ()
        out.append(node)
    return tuple(out)


def pytest_gate(root: Path, nodes: tuple[str, ...]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as temp:
        report = Path(temp) / "result.xml"
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONPATH="src")
        try:
            p = subprocess.run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "-q",
                    "--disable-warnings",
                    f"--junitxml={report}",
                    *nodes,
                ],
                cwd=root,
                env=env,
                timeout=240,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired:
            return {"status": "NOT_RUN", "reason": "PYTEST_TIMEOUT"}
        if not report.is_file():
            return {
                "status": "NOT_RUN",
                "reason": "JUNIT_REPORT_MISSING",
                "exit_code": p.returncode,
            }
        try:
            tree = ET.parse(report)
            suites = list(tree.iter("testsuite"))
            if not suites:
                raise ValueError("no testsuite")
            totals = {
                k: sum(int(q.get(k, "0")) for q in suites)
                for k in ("tests", "failures", "errors", "skipped")
            }
        except (ET.ParseError, ValueError):
            return {"status": "NOT_RUN", "reason": "JUNIT_REPORT_INVALID"}
        state = (
            "PASS"
            if p.returncode == 0
            and totals["tests"] > 0
            and totals["failures"] == totals["errors"] == totals["skipped"] == 0
            else "FAIL_OR_SKIP"
        )
        return {"status": state, "exit_code": p.returncode, "counts": totals}


def run(argv: list[str] | None = None) -> dict[str, object]:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--product-root", type=Path, required=True)
    ap.add_argument("--require-head", required=True)
    ap.add_argument("--map", type=Path)
    ap.add_argument("--allow-local-patch", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    root = args.product_root.resolve()
    catalog_path = root / "docs/audio/phase2/F11_SIGNAL_TRUTH_A46_R15C_COVERAGE.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text())
    else:
        # If not present, do not manufacture a case matrix or an outcome.
        catalog = {"cases": [{"id": f"R15C-{i:02d}"} for i in range(1, 51)]}
    cases = catalog["cases"]
    if len(cases) != 50 or len({v.get("id") for v in cases}) != 50:
        raise ValueError("R15C catalog requires 50 unique cases")
    verified, detail = checkout_status(
        root, args.require_head, allow_local_patch=args.allow_local_patch
    )
    mapping = json.loads(args.map.read_text()) if args.map else {}
    if not isinstance(mapping, dict):
        raise ValueError("mapping must be a JSON object")
    rows = []
    for case in cases:
        cid = case["id"]
        nodes = validate_nodes(mapping.get(cid), root) if verified else ()
        if not verified:
            status = {"status": "NOT_RUN", "reason": detail}
        elif not nodes:
            status = {"status": "NOT_RUN", "reason": "NO_VALID_PRODUCT_TEST_MAPPING"}
        else:
            status = pytest_gate(root, nodes)
        rows.append({"case_id": cid, "source_oracle": case.get("oracle"), **status})
    result = {
        "schema": "michi.f11.a49.r15c_product_results.v1",
        "required_sha": args.require_head,
        "checkout_verified": verified,
        "candidate_sha_kind": "LOCAL_WORKTREE_NOT_COMMIT_SHA"
        if args.allow_local_patch
        else "COMMIT",
        "checkout_result": detail,
        "run_in_repository": False,
        "cases": rows,
        "pass": sum(c["status"] == "PASS" for c in rows),
        "not_run": sum(c["status"] == "NOT_RUN" for c in rows),
        "fail_or_skip": sum(c["status"] == "FAIL_OR_SKIP" for c in rows),
        "dac_physical_gate": "NOT_RUN",
        "exact_sha_remote_ci": "NOT_RUN",
        "overall": (
            "SOFTWARE_MAPPING_PASS_PHYSICAL_CI_NOT_RUN"
            if all(c["status"] == "PASS" for c in rows) and verified
            else "NO_GO"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    report = run()
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "checkout_verified",
                    "pass",
                    "not_run",
                    "fail_or_skip",
                    "overall",
                )
            }
        )
    )
    raise SystemExit(2)  # must never certify F11 without physical + remote CI
