#!/usr/bin/env python3
"""QML Manifest V6 Generator — dimensions with weights from config, scored per module."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
CONFIG_FILE = REPO / "config" / "qml_migration_dimensions.json"
EVIDENCE_FILE = ARTIFACTS / "qml-evidence-v6.json"
MANIFEST_PATH = REPO / "docs" / "qml_migration_manifest_v6.json"

KNOWN_DIMENSIONS = [
    "route_load", "qml_instance", "model_data", "service_wiring",
    "read", "primary_action", "secondary_actions", "write",
    "error_contract", "async_execution", "real_cancellation",
    "persistence", "integration", "vertical_workflow",
    "performance", "accessibility",
]

MODULE_STATUS_ORDER = [
    "NOT_IMPLEMENTED", "SCAFFOLDED", "COMPILES", "READ_ONLY",
    "PARTIAL_WORKFLOW", "PRODUCTIVE", "PARITY",
]


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


def load_evidence() -> dict:
    if not EVIDENCE_FILE.exists():
        return {"testcases": [], "marked_tests": []}
    return json.loads(EVIDENCE_FILE.read_text())


def build_dimension_status(
    dim: str,
    module_name: str,
    testcases: list,
    marked_tests: list,
    weight: int,
) -> dict:
    dim_tests = []
    for mt in marked_tests:
        if mt.get("dimension") != dim:
            continue
        if mt.get("module") != module_name:
            continue
        matched = False
        mt_nodeid = mt.get("nodeid", "")
        for tc in testcases:
            tc_nodeid = tc.get("nodeid", "")
            if tc_nodeid == mt_nodeid:
                dim_tests.append(tc)
                matched = True
                break
            combined = f"{tc.get('classname', '')}::{tc.get('name', '')}"
            if combined == mt_nodeid:
                dim_tests.append(tc)
                matched = True
                break
        if not matched:
            dim_tests.append({
                "name": mt.get("function", ""),
                "classname": mt.get("file", ""),
                "nodeid": mt_nodeid,
                "time": 0,
                "failure": None,
                "skipped": False,
                "suite": "",
                "_unmatched": True,
            })

    if not dim_tests:
        return {"status": "NOT_APPLICABLE", "tests": [], "weight": weight, "reason": ""}

    failures = [t for t in dim_tests if t.get("failure")]
    skips = [t for t in dim_tests if t.get("skipped") and not t.get("failure")]
    passed = [t for t in dim_tests if not t.get("failure") and not t.get("skipped") and not t.get("_unmatched")]

    if failures:
        return {
            "status": "FAILED",
            "tests": dim_tests,
            "weight": weight,
            "reason": f"{len(failures)} test(s) failed",
        }
    if any(t.get("_unmatched") for t in dim_tests):
        return {
            "status": "MISSING",
            "tests": dim_tests,
            "weight": weight,
            "reason": "No JUnit evidence for marked test",
        }
    if skips and not passed:
        return {
            "status": "MISSING",
            "tests": dim_tests,
            "weight": weight,
            "reason": "All tests skipped without reason",
        }
    return {
        "status": "PASSED",
        "tests": dim_tests,
        "weight": weight,
        "reason": "",
    }


def derive_composite_status(dimensions: dict[str, dict]) -> str:
    statuses = {d: v["status"] for d, v in dimensions.items()}

    def _all_pass(*names):
        return all(statuses.get(n) == "PASSED" for n in names)

    compiles = _all_pass("route_load", "qml_instance")
    read_only = compiles and _all_pass("model_data", "service_wiring", "read")
    partial = read_only and any(
        statuses.get(d) == "PASSED" for d in ["primary_action", "secondary_actions", "write"]
    )
    productive_basic = _all_pass("primary_action", "error_contract", "integration", "vertical_workflow")
    persistence_ok = statuses.get("persistence") in ("PASSED", "NOT_APPLICABLE")
    async_ok = statuses.get("async_execution") in ("PASSED", "NOT_APPLICABLE")
    cancel_ok = statuses.get("real_cancellation") in ("PASSED", "NOT_APPLICABLE")
    productive = productive_basic and persistence_ok and async_ok and cancel_ok

    all_applicable = all(
        v["status"] in ("PASSED", "NOT_APPLICABLE") for v in dimensions.values()
    )
    parity = productive and all_applicable

    if parity:
        return "PARITY"
    if productive:
        return "PRODUCTIVE"
    if partial:
        return "PARTIAL_WORKFLOW"
    if read_only:
        return "READ_ONLY"
    if compiles:
        return "COMPILES"
    if any(v["status"] == "PASSED" for v in dimensions.values()):
        return "SCAFFOLDED"
    return "NOT_IMPLEMENTED"


def main() -> int:
    config = load_config()
    evidence = load_evidence()
    testcases = evidence.get("testcases", [])
    marked_tests = evidence.get("marked_tests", [])

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    dimension_weights = config["dimension_weights"]

    modules_map: dict[str, dict] = {}
    for mt in marked_tests:
        mod = mt.get("module", "")
        if not mod:
            continue
        if mod not in modules_map:
            modules_map[mod] = {"dimensions": {}}
        dim = mt.get("dimension", "")
        if dim:
            modules_map[mod]["dimensions"].setdefault(dim, []).append(mt)

    modules_list = []
    for module_name in sorted(modules_map):
        dims = modules_map[module_name]["dimensions"]
        dimension_results = {}
        for dim in KNOWN_DIMENSIONS:
            weight = dimension_weights.get(dim, 5)
            if dim in dims:
                dim_marked = dims[dim]
                dim_result = build_dimension_status(dim, module_name, testcases, dim_marked, weight)
            else:
                dim_result = {"status": "NOT_APPLICABLE", "tests": [], "weight": weight, "reason": ""}
            dimension_results[dim] = dim_result

        composite_status = derive_composite_status(dimension_results)

        modules_list.append({
            "module": module_name,
            "status": composite_status,
            "dimensions": dimension_results,
        })

    manifest = {
        "version": "6.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": sha,
        "dimension_weights": dimension_weights,
        "modules": modules_list,
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Manifest V6 written to {MANIFEST_PATH}")
    print(f"SHA: {sha}")
    print(f"Modules: {len(modules_list)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
