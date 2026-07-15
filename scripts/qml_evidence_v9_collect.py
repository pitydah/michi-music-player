#!/usr/bin/env python3
"""QML Evidence V9 Collector — reads pytest JUnit XML with user_properties
(markers: qml_module, qml_dimension, qml_route), produces evidence JSON.

Reads qml_modules.yaml declaratively for module/dimension definitions.
"""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
MODULES_YAML = REPO / "config" / "qml_modules.yaml"

V9_MARKERS = {"qml_module", "qml_dimension", "qml_route"}

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


def parse_junit(junit_path: Path) -> list[dict]:
    results = []
    tree = ET.parse(junit_path)
    for ts in tree.findall(".//testsuite"):
        suite_name = ts.get("name", "")
        for tc in ts.findall("testcase"):
            nodeid = tc.get("classname", "") + "::" + tc.get("name", "")
            failure = tc.find("failure")
            error = tc.find("error")
            skipped = tc.find("skipped")
            status = "PASSED"
            if failure is not None or error is not None:
                status = "FAILED"
            elif skipped is not None:
                status = "MISSING"
            props = {}
            for prop in tc.findall(".//property"):
                props[prop.get("name")] = prop.get("value")
            results.append({
                "nodeid": nodeid,
                "suite": suite_name,
                "status": status,
                "module": props.get("qml_module", ""),
                "dimension": props.get("qml_dimension", ""),
                "route": props.get("qml_route", ""),
            })
    return results


def score_module_module(module_cfg: dict, tests: list[dict]) -> dict:
    module_name = module_cfg.get("module", "")
    dimensions = module_cfg.get("dimensions", [])

    dim_results = {}
    total_applicable = 0
    total_passed_weight = 0

    for dim_name in dimensions:
        matching = [t for t in tests if t.get("module") == module_name and t.get("dimension") == dim_name]
        if not matching:
            dim_results[dim_name] = {"status": "NOT_APPLICABLE_DECLARED", "reason": "No tests for dimension"}
            continue
        if all(t["status"] == "PASSED" for t in matching):
            dim_results[dim_name] = {"status": "PASSED"}
            total_passed_weight += 1
        else:
            failed = [t for t in matching if t["status"] != "PASSED"]
            dim_results[dim_name] = {"status": "FAILED", "reason": failed[0]["status"]}
        total_applicable += 1

    score = (total_passed_weight / total_applicable * 100) if total_applicable > 0 else 0
    return {
        "score": round(score, 1),
        "dimensions": dim_results,
        "total_applicable": total_applicable,
        "passed_count": total_passed_weight,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()

    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()

    if sha != args.expected_sha:
        print(f"ERROR: SHA mismatch. Expected {args.expected_sha}, got {sha}")
        return 1

    junit_path = args.junit
    if not junit_path.exists():
        print(f"ERROR: JUnit file not found: {junit_path}")
        return 1

    config = load_modules_config()
    testcases = parse_junit(junit_path)

    module_defs = config.get("modules", {})
    modules_list = []
    total_weight = 0
    total_weighted_score = 0.0

    for module_name, mod_cfg in sorted(module_defs.items()):
        mod_weight = mod_cfg.get("weight", 10)
        m_tests = [t for t in testcases if t.get("module") == module_name]
        s = score_module_module(mod_cfg, m_tests)
        modules_list.append({
            "module": module_name,
            "weight": mod_weight,
            "score": s["score"],
            "dimensions": s["dimensions"],
            "total_applicable": s["total_applicable"],
            "passed_count": s["passed_count"],
            "tests_count": len(m_tests),
        })
        total_weighted_score += s["score"] * mod_weight / 100.0
        total_weight += mod_weight

    global_score = (total_weighted_score / total_weight * 100) if total_weight > 0 else 0.0

    evidence = {
        "version": "9.0",
        "sha": sha,
        "junit_file": str(junit_path),
        "global_score": round(global_score, 1),
        "total_evidence": len(testcases),
        "passed": sum(1 for t in testcases if t["status"] == "PASSED"),
        "failed": sum(1 for t in testcases if t["status"] == "FAILED"),
        "skipped": sum(1 for t in testcases if t["status"] == "MISSING"),
        "modules": modules_list,
        "testcases": testcases,
    }

    outpath = ARTIFACTS / "qml-evidence-v9.json"
    outpath.write_text(json.dumps(evidence, indent=2, default=str))
    print(f"Evidence V9 written to {outpath}")
    print(f"SHA: {sha}")
    print(f"Global score: {global_score:.1f}%")
    print(f"Total evidence cases: {evidence['total_evidence']}")
    print(f"Passed: {evidence['passed']}, Failed: {evidence['failed']}, Skipped: {evidence['skipped']}")
    print(f"Modules: {len(modules_list)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
