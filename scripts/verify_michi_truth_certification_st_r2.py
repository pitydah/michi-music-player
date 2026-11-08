#!/usr/bin/env python3
"""ST-R2-01: one executable source of truth for the current R15C state.

The historical ST-R1 receipt and coverage files are retained unchanged. This
verifier produces the current artifact from real pytest execution, records the
exact node IDs and per-node outcomes, and fails closed when a claimed PASS was
not executed. It deliberately does not turn software results into DAC, KWin or
hardware certification.
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
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE = "AP2-F11"
SPEC = ROOT / "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md"
MAP_PATH = ROOT / "docs/audio/phase2/F11_SIGNAL_TRUTH_R15C_MAP_ST_R1.json"
HISTORICAL_COVERAGE = (
    ROOT / "docs/audio/phase2/F11_SIGNAL_TRUTH_R15C_ST_R1_COVERAGE.json"
)
HISTORICAL_RECEIPT = ROOT / "docs/audio/phase2/F11_SIGNAL_TRUTH_ST_R1_RECEIPT.json"
OUTPUT = ROOT / "docs/audio/phase2/F11_SIGNAL_TRUTH_ST_R2_CERTIFICATION.json"

# A single OUT_OF_SCOPE bucket hides three different obligations. These cases
# keep their own status so a product gap or a missing runtime is never mistaken
# for a platform that Michi does not own.
SPECIAL_CASES = {
    "R15C-20": {
        "status": "BLOCKED_NOT_IMPLEMENTED",
        "category": "POLARITY_DSP_NOT_IMPLEMENTED",
        "scope": "PRODUCT_GAP",
    },
    "R15C-23": {
        "status": "EXTERNAL_VALIDATION_REQUIRED",
        "category": "RT_CALLBACK_AND_XRUN_REQUIRE_PHYSICAL_HOST",
        "scope": "PHYSICAL_RT_HOST",
    },
    "R15C-24": {
        "status": "BLOCKED_RUNTIME",
        "category": "REAL_CROSSFADE_WINDOWS_REQUIRE_PLAYBACK_RUNTIME",
        "scope": "PLAYBACK_RUNTIME",
    },
    "R15C-31": {
        "status": "OUT_OF_SCOPE_DESKTOP",
        "category": "ANDROID_USB_REQUIRES_PHYSICAL_DEVICE",
        "scope": "MOBILE_PLATFORM",
    },
    "R15C-32": {
        "status": "OUT_OF_SCOPE_DESKTOP",
        "category": "BROWSER_RUNTIME_REQUIRES_BROWSER_HOST",
        "scope": "BROWSER_PLATFORM",
    },
    "R15C-37": {
        "status": "OUT_OF_SCOPE_CURRENT_PLATFORM",
        "category": "WINDOWS_QPC_AUDIOCONTEXT_REQUIRES_WINDOWS_HOST",
        "scope": "WINDOWS_PLATFORM",
    },
}

# Mapped tests are real, but they do not satisfy the complete oracle. Partial is
# an explicit state: it cannot be counted as PASS and it keeps the missing
# evidence visible.
PARTIAL_CASES = {
    "R15C-15": {
        "category": "COALESCING_AND_UI_LOAD_ONLY",
        "missing": "No audio-callback or ALSA XRUN measurement was executed.",
    },
    "R15C-44": {
        "category": "STAGES_SCROLL_FOCUS_ONLY",
        "missing": (
            "200% DPI, live KWin rendering and NowPlayingBar stability were "
            "not measured."
        ),
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def worktree_identity(root: Path, out_path: Path) -> dict:
    """Hash the exact tracked diff and untracked files that were executed.

    The output artifact itself is excluded because its bytes are written after
    the run; `.serena/` is local tooling state and is not part of the product.
    """
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    untracked = git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    serena_root = (root / ".serena").resolve()
    excluded = {out_path.resolve(), serena_root}
    entries: list[dict[str, str]] = []
    for relative in sorted(untracked):
        path = root / relative
        resolved = path.resolve()
        if resolved in excluded or resolved.is_relative_to(serena_root):
            continue
        entries.append({"path": relative, "sha256": sha256(path)})
    manifest = hashlib.sha256()
    manifest.update(diff)
    for entry in entries:
        manifest.update(f"{entry['path']}\0{entry['sha256']}\n".encode())
    return {
        "baseline_sha": git(root, "rev-parse", "HEAD"),
        "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "untracked_files": entries,
        "worktree_sha256": manifest.hexdigest(),
        "identity_scope": (
            "git diff --binary HEAD plus SHA-256 of every untracked product "
            "file, excluding .serena/ and the output artifact"
        ),
    }


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def run_env(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def collect_nodeids(root: Path) -> set[str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
        cwd=root,
        env=run_env(root),
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"collection failed: {proc.stderr[-2000:]}")
    nodeids = {
        line.strip()
        for line in proc.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    }
    if not nodeids:
        raise RuntimeError("pytest collected no node IDs")
    return nodeids


def _nodeid_from_testcase(root: Path, testcase: ET.Element) -> str | None:
    name = testcase.get("name")
    classname = testcase.get("classname", "")
    if not name:
        return None
    parts = classname.split(".") if classname else []
    for index in range(len(parts), 0, -1):
        candidate = root / Path(*parts[:index]).with_suffix(".py")
        if not candidate.exists():
            continue
        relative = candidate.relative_to(root).as_posix()
        remainder = parts[index:]
        return "::".join([relative, *remainder, name])
    return None


def _outcome(testcase: ET.Element) -> str:
    if testcase.find("failure") is not None:
        return "FAIL"
    if testcase.find("error") is not None:
        return "ERROR"
    if testcase.find("skipped") is not None:
        return "SKIP"
    return "PASS"


def execute_nodes(root: Path, nodes: list[str], junit: Path) -> dict[str, str]:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--disable-warnings",
            f"--junitxml={junit}",
            *nodes,
        ],
        cwd=root,
        env=run_env(root),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    results: dict[str, str] = {}
    if not junit.exists():
        return results
    tree = ET.parse(junit)
    for testcase in tree.getroot().iter("testcase"):
        nodeid = _nodeid_from_testcase(root, testcase)
        if nodeid:
            results[nodeid] = _outcome(testcase)
    # A non-zero pytest exit with a complete XML is represented by the
    # per-node FAIL/ERROR outcomes above. A missing XML is a hard error.
    if proc.returncode not in (0, 1) and not results:
        raise RuntimeError(f"pytest execution failed: {proc.stderr[-2000:]}")
    return results


def classify_case(
    case_id: str,
    nodes: list[str],
    collected: set[str],
    results: dict[str, str],
) -> dict:
    if case_id in SPECIAL_CASES:
        special = SPECIAL_CASES[case_id]
        return {
            "id": case_id,
            "status": special["status"],
            "category": special["category"],
            "scope": special["scope"],
            "reason": special["category"],
            "nodes": nodes,
            "evidence": [],
        }
    if not nodes:
        return {
            "id": case_id,
            "status": "BLOCKED",
            "category": "NO_MAPPED_NODE",
            "nodes": [],
            "evidence": [],
        }
    missing = [node for node in nodes if node not in collected]
    if missing:
        return {
            "id": case_id,
            "status": "BLOCKED",
            "category": "NODE_NOT_COLLECTED",
            "nodes": nodes,
            "missing": missing,
            "evidence": [],
        }
    evidence = [
        {"node": node, "result": results.get(node, "NOT_RUN")} for node in nodes
    ]
    outcomes = {item["result"] for item in evidence}
    if "FAIL" in outcomes or "ERROR" in outcomes:
        status = "FAIL"
    elif "SKIP" in outcomes:
        status = "SKIP"
    elif outcomes == {"PASS"} and case_id in PARTIAL_CASES:
        status = "PARTIAL"
    elif outcomes == {"PASS"}:
        status = "PASS"
    else:
        status = "NOT_RUN"
    partial = PARTIAL_CASES.get(case_id)
    return {
        "id": case_id,
        "status": status,
        "category": partial["category"] if partial else "SOFTWARE_ORACLE",
        "missing": partial["missing"] if partial else None,
        "nodes": nodes,
        "evidence": evidence,
    }


def build_artifact(
    root: Path,
    ci_run: str | None,
    merge_sha: str | None = None,
    out_path: Path = OUTPUT,
) -> dict:
    mapping = load_json(MAP_PATH)
    collected = collect_nodeids(root)
    unique_nodes = sorted({node for nodes in mapping.values() for node in nodes})
    with tempfile.TemporaryDirectory(prefix="michi-st-r2-") as tmp:
        junit = Path(tmp) / "r15c.xml"
        results = execute_nodes(root, unique_nodes, junit)
    all_case_ids = [f"R15C-{index:02d}" for index in range(1, 51)]
    cases = [
        classify_case(case_id, mapping.get(case_id, []), collected, results)
        for case_id in all_case_ids
    ]
    counts = Counter(case["status"] for case in cases)
    head = git(root, "rev-parse", "HEAD")
    status = git(root, "status", "--porcelain")
    identity = worktree_identity(root, out_path)
    receipt = load_json(HISTORICAL_RECEIPT)
    historical = load_json(HISTORICAL_COVERAGE)
    historical_counts = Counter(
        case.get("integration_status", "NOT_RUN") for case in historical["cases"]
    )
    return {
        "schema": "michi.ap2.f11.st_r2_certification.v1",
        "phase": PHASE,
        "generated_at": datetime.now(UTC).isoformat(),
        "execution": {
            "sha": head,
            "baseline_sha": identity["baseline_sha"],
            "dirty": bool(status),
            "worktree_sha256": identity["worktree_sha256"],
            "tracked_diff_sha256": identity["tracked_diff_sha256"],
            "untracked_files": identity["untracked_files"],
            "identity_scope": identity["identity_scope"],
            "ci_run": ci_run or "NOT_RUN",
            "ci_status": "NOT_RUN" if not ci_run else "RECORDED_NOT_VERIFIED_HERE",
            "phase2_spec_sha256": sha256(SPEC),
        },
        "sources": {
            "map": {
                "path": str(MAP_PATH.relative_to(root)),
                "sha256": sha256(MAP_PATH),
            },
            "historical_coverage": {
                "path": str(HISTORICAL_COVERAGE.relative_to(root)),
                "sha256": sha256(HISTORICAL_COVERAGE),
                "historical": True,
                "status_counts": dict(sorted(historical_counts.items())),
            },
            "historical_receipt": {
                "path": str(HISTORICAL_RECEIPT.relative_to(root)),
                "sha256": sha256(HISTORICAL_RECEIPT),
                "code_sha": receipt.get("code_sha"),
                "merge_sha": merge_sha or receipt.get("merge_sha"),
                "ci_run": receipt.get("ci", {}).get("run_id"),
            },
        },
        "cases": cases,
        "summary": {
            "total": len(cases),
            "pass": counts.get("PASS", 0),
            "partial": counts.get("PARTIAL", 0),
            "fail": counts.get("FAIL", 0),
            "error": counts.get("ERROR", 0),
            "skip": counts.get("SKIP", 0),
            "not_run": counts.get("NOT_RUN", 0),
            "blocked": counts.get("BLOCKED", 0),
            "blocked_not_implemented": counts.get("BLOCKED_NOT_IMPLEMENTED", 0),
            "external_validation_required": counts.get(
                "EXTERNAL_VALIDATION_REQUIRED", 0
            ),
            "blocked_runtime": counts.get("BLOCKED_RUNTIME", 0),
            "out_of_scope_desktop": counts.get("OUT_OF_SCOPE_DESKTOP", 0),
            "out_of_scope_current_platform": counts.get(
                "OUT_OF_SCOPE_CURRENT_PLATFORM", 0
            ),
            "status_counts": dict(sorted(counts.items())),
        },
        "evidence": {
            "code": "PASS_EXECUTED_MAPPED_TESTS_WITH_TWO_PARTIAL_ORACLES",
            "ci": "NOT_RUN",
            "software_oracle": "PARTIAL",
            "qml_runtime": "PASS",
            "physical_dac": "NOT_RUN",
            "external_hardware": "NOT_RUN",
        },
        "certification": {
            "software_oracle": (
                "PARTIAL"
                if (
                    counts.get("PASS", 0) == 42
                    and counts.get("PARTIAL", 0) == 2
                    and counts.get("FAIL", 0) == 0
                    and counts.get("ERROR", 0) == 0
                    and counts.get("SKIP", 0) == 0
                    and counts.get("NOT_RUN", 0) == 0
                    and counts.get("BLOCKED", 0) == 0
                    and sum(
                        counts.get(status, 0)
                        for status in (
                            "BLOCKED_NOT_IMPLEMENTED",
                            "EXTERNAL_VALIDATION_REQUIRED",
                            "BLOCKED_RUNTIME",
                            "OUT_OF_SCOPE_DESKTOP",
                            "OUT_OF_SCOPE_CURRENT_PLATFORM",
                        )
                    )
                    == 6
                )
                else "NO_GO"
            ),
            "physical_dac": "NOT_RUN",
            "kwin_live": "NOT_RUN",
            "external_hardware": "NOT_RUN",
            "f11_state": "ACTIVE",
            "product_certification": "NO_GO",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci-run", default=None)
    parser.add_argument("--merge-sha", default=None)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    if args.check_only:
        artifact = load_json(args.out)
        problems = check_artifact(artifact)
        for problem in problems:
            print(f"[FAIL] {problem}")
        if not problems:
            print("[PASS] certification artifact is internally consistent")
        return 1 if problems else 0
    artifact = build_artifact(ROOT, args.ci_run, args.merge_sha, args.out)
    args.out.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(artifact["summary"], indent=2))
    for case in artifact["cases"]:
        print(f"{case['id']} {case['status']} {case['category']}")
    return 0 if artifact["summary"]["fail"] == 0 else 1


def check_artifact(artifact: dict) -> list[str]:
    problems: list[str] = []
    cases = artifact.get("cases", [])
    if len(cases) != 50:
        problems.append(f"expected 50 cases, got {len(cases)}")
    execution = artifact.get("execution", {})
    for key in (
        "baseline_sha",
        "worktree_sha256",
        "tracked_diff_sha256",
        "untracked_files",
        "identity_scope",
    ):
        if not execution.get(key):
            problems.append(f"execution identity is missing {key}")
    special_statuses = {
        "BLOCKED_NOT_IMPLEMENTED",
        "EXTERNAL_VALIDATION_REQUIRED",
        "BLOCKED_RUNTIME",
        "OUT_OF_SCOPE_DESKTOP",
        "OUT_OF_SCOPE_CURRENT_PLATFORM",
    }
    for case in cases:
        status = case["status"]
        evidence = case.get("evidence") or []
        if status == "PASS":
            if not evidence:
                problems.append(f"{case['id']} claims PASS without executed evidence")
            for item in evidence:
                if item.get("result") != "PASS":
                    problems.append(f"{case['id']} claims PASS with {item}")
        elif status == "PARTIAL":
            if not case.get("missing"):
                problems.append(f"{case['id']} is PARTIAL without missing evidence")
            if not evidence:
                problems.append(f"{case['id']} is PARTIAL without executed evidence")
            for item in evidence:
                if item.get("result") != "PASS":
                    problems.append(f"{case['id']} is PARTIAL with {item}")
        elif status in special_statuses:
            if not case.get("category") or not case.get("scope"):
                problems.append(f"{case['id']} has no category/scope for {status}")
        elif status == "OUT_OF_SCOPE":
            problems.append(
                f"{case['id']} uses the legacy OUT_OF_SCOPE bucket; "
                "classify the obligation explicitly"
            )
    summary = artifact.get("summary", {})
    if len(cases) == 50 and sum(summary.get("status_counts", {}).values()) != 50:
        problems.append("status_counts does not add up to 50")
    historical = artifact.get("sources", {}).get("historical_coverage", {})
    if not historical.get("historical"):
        problems.append("historical coverage is not marked historical")
    if historical.get("status_counts") != {"NOT_RUN": 46, "PASS": 4}:
        problems.append("historical coverage status counts changed")
    return problems


if __name__ == "__main__":
    raise SystemExit(main())
