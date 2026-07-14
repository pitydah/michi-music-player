#!/usr/bin/env python3
"""QML Manifest V8 Generator — modules from qml_modules.yaml, markers: qml_module, qml_dimension, qml_route, qml_workflow, widget_replacement."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
MODULES_YAML = REPO / "config" / "qml_modules.yaml"
EVIDENCE_FILE = ARTIFACTS / "qml-evidence-v8.json"
MANIFEST_PATH = REPO / "docs" / "qml_migration_manifest_v8.json"

V8_MARKERS = ["qml_module", "qml_dimension", "qml_route", "qml_workflow", "widget_replacement"]

MARKER_KEY_MAP = {
    "qml_module": "module",
    "qml_dimension": "dimension",
    "qml_route": "route",
    "qml_workflow": "workflow",
    "widget_replacement": "widget",
}

MODULE_STATUS_ORDER = [
    "NOT_IMPLEMENTED", "SCAFFOLDED", "COMPILES", "READ_ONLY",
    "PARTIAL_WORKFLOW", "PRODUCTIVE", "PARITY",
]


def load_modules_config() -> dict:
    with open(MODULES_YAML) as f:
        return yaml.safe_load(f)


def load_evidence() -> dict:
    if not EVIDENCE_FILE.exists():
        return {"testcases": [], "marked_tests": []}
    return json.loads(EVIDENCE_FILE.read_text())


def build_marker_status(marker_type: str, module_name: str, testcases: list, marked_tests: list, weight: int) -> dict:
    marker_tests = []
    evidence_key = MARKER_KEY_MAP.get(marker_type, marker_type)
    for mt in marked_tests:
        val = mt.get(evidence_key, "")
        if not val:
            continue
        if val != module_name:
            continue
        matched = False
        mt_nodeid = mt.get("nodeid", "")
        for tc in testcases:
            tc_nodeid = tc.get("nodeid", "")
            if tc_nodeid == mt_nodeid:
                marker_tests.append(tc)
                matched = True
                break
            combined = f"{tc.get('classname', '')}::{tc.get('name', '')}"
            if combined == mt_nodeid:
                marker_tests.append(tc)
                matched = True
                break
        if not matched:
            marker_tests.append({
                "name": mt.get("function", ""),
                "classname": mt.get("file", ""),
                "nodeid": mt_nodeid,
                "time": 0,
                "failure": None,
                "skipped": False,
                "suite": "",
                "_unmatched": True,
            })

    if not marker_tests:
        return {"status": "NOT_APPLICABLE_DECLARED", "tests": [], "weight": weight, "reason": ""}

    failures = [t for t in marker_tests if t.get("failure")]
    skips = [t for t in marker_tests if t.get("skipped") and not t.get("failure")]
    passed = [t for t in marker_tests if not t.get("failure") and not t.get("skipped") and not t.get("_unmatched")]

    if failures:
        return {"status": "FAILED", "tests": marker_tests, "weight": weight, "reason": f"{len(failures)} test(s) failed"}
    if any(t.get("_unmatched") for t in marker_tests):
        return {"status": "MISSING", "tests": marker_tests, "weight": weight, "reason": "No JUnit evidence for marked test"}
    if skips and not passed:
        return {"status": "MISSING", "tests": marker_tests, "weight": weight, "reason": "All tests skipped"}
    return {"status": "PASSED", "tests": marker_tests, "weight": weight, "reason": ""}


def main() -> int:
    config = load_modules_config()
    evidence = load_evidence()
    testcases = evidence.get("testcases", [])
    marked_tests = evidence.get("marked_tests", [])

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    module_defs = config.get("modules", {})
    modules_list = []

    for module_name, mod_cfg in sorted(module_defs.items()):
        markers_config = mod_cfg.get("dimensions", [])
        marker_results = {}
        for mt in V8_MARKERS:
            weight = mod_cfg.get("weight", 10)
            if mt in markers_config:
                marker_results[mt] = build_marker_status(mt, module_name, testcases, marked_tests, weight)
            else:
                marker_results[mt] = {"status": "NOT_APPLICABLE_DECLARED", "tests": [], "weight": weight, "reason": ""}

        total_weight = sum(m.get("weight", 0) for m in marker_results.values())
        weighted_sum = sum(
            (1.0 if m["status"] in ("PASSED", "NOT_APPLICABLE_DECLARED") else 0.0) * m.get("weight", 0)
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
        "version": "8.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sha": sha,
        "module_weights": {m: d["weight"] for m, d in module_defs.items()},
        "modules": modules_list,
        "global_score": round(global_score, 1),
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Manifest V8 written to {MANIFEST_PATH}")
    print(f"SHA: {sha}")
    print(f"Modules: {len(modules_list)}")
    print(f"Global score: {global_score:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
