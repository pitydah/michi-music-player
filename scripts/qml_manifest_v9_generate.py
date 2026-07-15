#!/usr/bin/env python3
"""QML Manifest V9 Generator — modules from qml_modules.yaml, markers: qml_module, qml_dimension, qml_route.

Reads evidence V9 JSON, produces manifest with per-module scores and global score.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
MODULES_YAML = REPO / "config" / "qml_modules.yaml"
EVIDENCE_FILE = ARTIFACTS / "qml-evidence-v9.json"
MANIFEST_PATH = REPO / "docs" / "qml_migration_manifest_v9.json"

VALID_STATUSES = {"PASSED", "FAILED", "MISSING", "NOT_APPLICABLE_DECLARED", "DEFERRED_PHYSICAL"}
SCORE_MAP = {
    "PASSED": 1.0,
    "FAILED": 0.0,
    "MISSING": 0.0,
    "NOT_APPLICABLE_DECLARED": 1.0,
    "DEFERRED_PHYSICAL": 1.0,
}


def load_modules_config():
    try:
        import yaml
        return yaml.safe_load(MODULES_YAML.read_text())
    except Exception:
        return {}


def load_evidence():
    if not EVIDENCE_FILE.exists():
        return {"modules": [], "testcases": []}
    return json.loads(EVIDENCE_FILE.read_text())


def build_dimension_status(dim_name: str, module_name: str, testcases: list, marked_tests: list, weight: int) -> dict:
    dim_tests = []
    for mt in marked_tests:
        if mt.get("dimension") != dim_name:
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
        return {"status": "NOT_APPLICABLE_DECLARED", "tests": [], "weight": weight, "reason": ""}

    failures = [t for t in dim_tests if t.get("failure")]
    skips = [t for t in dim_tests if t.get("skipped") and not t.get("failure")]
    passed = [t for t in dim_tests if not t.get("failure") and not t.get("skipped") and not t.get("_unmatched")]

    if failures:
        return {"status": "FAILED", "tests": dim_tests, "weight": weight, "reason": f"{len(failures)} test(s) failed"}
    if any(t.get("_unmatched") for t in dim_tests):
        return {"status": "MISSING", "tests": dim_tests, "weight": weight, "reason": "No JUnit evidence for marked test"}
    if skips and not passed:
        return {"status": "MISSING", "tests": dim_tests, "weight": weight, "reason": "All tests skipped"}
    if not passed:
        return {"status": "MISSING", "tests": dim_tests, "weight": weight, "reason": "No passing tests"}
    return {"status": "PASSED", "tests": dim_tests, "weight": weight, "reason": ""}


def main():
    config = load_modules_config()
    evidence = load_evidence()
    testcases = evidence.get("testcases", [])
    module_defs = config.get("modules", {})

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    modules_list = []
    for module_name, mod_cfg in sorted(module_defs.items()):
        dimensions_config = mod_cfg.get("dimensions", [])
        marker_results = {}
        for dim_name in dimensions_config:
            weight = mod_cfg.get("weight", 10)
            marker_results[dim_name] = build_dimension_status(dim_name, module_name, testcases, evidence.get("testcases", []), weight)

        for dm in ("qml_module", "qml_dimension", "qml_route"):
            if dm not in marker_results:
                marker_results[dm] = {"status": "NOT_APPLICABLE_DECLARED", "tests": [], "weight": mod_cfg.get("weight", 10), "reason": ""}

        total_weight = sum(m.get("weight", 0) for m in marker_results.values())
        weighted_sum = sum(
            SCORE_MAP.get(m["status"], 0.0) * m.get("weight", 0)
            for m in marker_results.values()
        )
        score = (weighted_sum / total_weight * 100.0) if total_weight > 0 else 0.0

        modules_list.append({
            "module": module_name,
            "weight": mod_cfg.get("weight", 10),
            "score": round(score, 1),
            "markers": marker_results,
        })

    total_score = 0.0
    total_mod_weight = 0
    for mod in modules_list:
        total_score += mod["score"] * mod["weight"]
        total_mod_weight += mod["weight"]
    global_score = (total_score / total_mod_weight) if total_mod_weight > 0 else 0.0

    manifest = {
        "version": "9.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": sha,
        "module_weights": {m: d["weight"] for m, d in module_defs.items()},
        "modules": modules_list,
        "global_score": round(global_score, 1),
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Manifest V9 written to {MANIFEST_PATH}")
    print(f"SHA: {sha}")
    print(f"Modules: {len(modules_list)}")
    print(f"Global score: {global_score:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
