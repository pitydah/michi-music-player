#!/usr/bin/env python3
"""QML Evidence V7 Collector — run pytest, parse JUnit XML, compute normalized scores by module."""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
CONFIG_FILE = REPO / "config" / "qml_modules.yaml"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

KNOWN_DIMENSIONS = [
    "route_load", "qml_instance", "model_data", "service_wiring",
    "read", "primary_action", "secondary_actions", "write",
    "error_contract", "async_execution", "real_cancellation",
    "persistence", "integration", "vertical_workflow",
    "performance", "accessibility",
]

COMPOSITE_ORDER = [
    "NOT_IMPLEMENTED", "SCAFFOLDED", "COMPILES", "READ_ONLY",
    "PARTIAL_WORKFLOW", "PRODUCTIVE", "PARITY",
]


def load_modules_config() -> dict:
    import yaml
    data = yaml.safe_load(CONFIG_FILE.read_text())
    modules = {}
    for m in data.get("modules", []):
        modules[m["module"]] = {
            "area": m["area"],
            "module_weight": m["module_weight"],
            "applicable_dimensions": m.get("applicable_dimensions", KNOWN_DIMENSIONS),
            "widget_replacement": m.get("widget_replacement", {}),
        }
    return modules


def load_area_weights() -> dict:
    return {
        "shell_nav": 10,
        "library_playback": 25,
        "core_workflows": 20,
        "advanced_tools": 20,
        "ecosystem_network": 15,
        "quality_release": 10,
    }


def parse_junit(junit_path: Path) -> list[dict]:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    testcases = []
    for ts in root:
        suite_name = ts.get("name", "")
        for tc in ts:
            props = {}
            for prop in tc.findall(".//property"):
                props[prop.get("name")] = prop.get("value")
            failure_el = tc.find("failure")
            error_el = tc.find("error")
            skipped_el = tc.find("skipped")
            classname = tc.get("classname", "")
            name = tc.get("name", "")
            testcases.append({
                "name": name,
                "classname": classname,
                "nodeid": f"{classname}::{name}" if classname else name,
                "time": float(tc.get("time", 0)),
                "failure": failure_el.text if failure_el is not None else error_el.text if error_el is not None else None,
                "skipped": skipped_el is not None,
                "suite": suite_name,
                "user_properties": props,
            })
    return testcases


def derive_composite_status(dim_scores: dict[str, dict]) -> str:
    def _all_pass(*names):
        return all(dim_scores.get(n, {}).get("status") == "PASSED" for n in names)

    def _any_pass(*names):
        return any(dim_scores.get(d, {}).get("status") == "PASSED" for d in names)

    def _not_failed_or_na(name):
        s = dim_scores.get(name, {}).get("status")
        return s in ("PASSED", "NOT_APPLICABLE")

    compiles = _all_pass("route_load", "qml_instance")
    read_only = compiles and _all_pass("model_data", "service_wiring", "read")
    partial = read_only and _any_pass("primary_action", "secondary_actions", "write")
    productive_basic = _all_pass("primary_action", "error_contract", "integration", "vertical_workflow")
    persistence_ok = _not_failed_or_na("persistence")
    async_ok = _not_failed_or_na("async_execution")
    cancel_ok = _not_failed_or_na("real_cancellation")
    productive = productive_basic and persistence_ok and async_ok and cancel_ok
    all_applicable = all(
        v["status"] in ("PASSED", "NOT_APPLICABLE") for v in dim_scores.values()
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
    return "NOT_IMPLEMENTED"


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

    modules_config = load_modules_config()
    testcases = parse_junit(junit_path)

    dim_weights = {
        "route_load": 8, "qml_instance": 7, "model_data": 8,
        "service_wiring": 10, "read": 8, "primary_action": 12,
        "secondary_actions": 8, "write": 8, "error_contract": 7,
        "async_execution": 6, "real_cancellation": 5, "persistence": 5,
        "integration": 8, "vertical_workflow": 8, "performance": 5,
        "accessibility": 5,
    }

    module_results = []
    for mod_name, mod_cfg in sorted(modules_config.items()):
        applicable = mod_cfg["applicable_dimensions"]
        dim_scores = {}
        for dim in KNOWN_DIMENSIONS:
            if dim not in applicable:
                dim_scores[dim] = {"status": "NOT_APPLICABLE", "weight": dim_weights.get(dim, 5)}
                continue
            dim_tests = [tc for tc in testcases if
                         tc.get("user_properties", {}).get("qml_module") == mod_name
                         and tc.get("user_properties", {}).get("qml_dimension") == dim]
            if not dim_tests:
                dim_scores[dim] = {"status": "NOT_APPLICABLE", "weight": dim_weights.get(dim, 5)}
                continue
            failures = [t for t in dim_tests if t.get("failure")]
            if failures:
                dim_scores[dim] = {"status": "FAILED", "weight": dim_weights.get(dim, 5), "failures": len(failures)}
            else:
                dim_scores[dim] = {"status": "PASSED", "weight": dim_weights.get(dim, 5)}

        composite = derive_composite_status(dim_scores)

        total_applicable_weight = sum(
            dim_weights.get(d, 5) for d in applicable if d in KNOWN_DIMENSIONS
        )
        passed_weight = sum(
            dim_weights.get(d, 5) for d in applicable
            if d in KNOWN_DIMENSIONS and dim_scores.get(d, {}).get("status") == "PASSED"
        )
        normalized_score = (passed_weight / total_applicable_weight * 100) if total_applicable_weight > 0 else 0

        module_results.append({
            "module": mod_name,
            "area": mod_cfg["area"],
            "module_weight": mod_cfg["module_weight"],
            "status": composite,
            "normalized_score": round(normalized_score, 1),
            "dimensions": dim_scores,
            "widget_replacement": mod_cfg["widget_replacement"],
        })

    total_weighted_score = 0
    total_weight = 0
    for mr in module_results:
        total_weighted_score += mr["normalized_score"] * mr["module_weight"]
        total_weight += mr["module_weight"]

    global_score = round(total_weighted_score / total_weight, 1) if total_weight > 0 else 0

    evidence = {
        "sha": sha,
        "junit_file": str(junit_path.resolve().relative_to(REPO)),
        "total_evidence": len(testcases),
        "passed": sum(1 for tc in testcases if not tc.get("failure") and not tc.get("skipped")),
        "failed": sum(1 for tc in testcases if tc.get("failure")),
        "skipped": sum(1 for tc in testcases if tc.get("skipped")),
        "global_score": global_score,
        "modules": module_results,
        "testcases": testcases,
    }

    outpath = ARTIFACTS / "qml-evidence-v7.json"
    outpath.write_text(json.dumps(evidence, indent=2, default=str))
    print(f"Evidence V7 written to {outpath}")
    print(f"SHA: {sha}")
    print(f"Total evidence cases: {len(testcases)}")
    print(f"Global score V7: {global_score:.1f}%")
    print(f"Modules: {len(module_results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
