#!/usr/bin/env python3
"""Evidence V7 collector — reads pytest JUnit XML with user_properties, calculates scores per module."""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
YAML_PATH = REPO / "config" / "qml_modules.yaml"


def load_yaml():
    try:
        import yaml
        return yaml.safe_load(YAML_PATH.read_text())
    except Exception:
        return json.loads(YAML_PATH.read_text())


def parse_junit(junit_path: Path) -> list[dict]:
    results = []
    tree = ET.parse(junit_path)
    for ts in tree.findall(".//testsuite"):
        suite_name = ts.get("name", "")
        for tc in ts.findall("testcase"):
            nodeid = tc.get("classname", "") + "::" + tc.get("name", "")
            status = "passed"
            failure = tc.find("failure")
            error = tc.find("error")
            skipped = tc.find("skipped")
            if failure is not None:
                status = "failed"
            elif error is not None:
                status = "error"
            elif skipped is not None:
                status = "skipped"
            props = {}
            for prop in tc.findall(".//property"):
                props[prop.get("name")] = prop.get("value")
            results.append({
                "nodeid": nodeid,
                "suite": suite_name,
                "status": status,
                "module": props.get("qml_module", ""),
                "dimension": props.get("qml_dimension", ""),
            })
    return results


def score_module(module_cfg: dict, tests: list[dict]) -> dict:
    dim_weights = {}
    try:
        import yaml
        cfg = yaml.safe_load(YAML_PATH.read_text()) if YAML_PATH.suffix == ".yaml" else json.loads(YAML_PATH.read_text())
    except Exception:
        cfg = {}
    dim_weights = cfg.get("dimension_weights", {})
    applicable = module_cfg.get("applicable_dimensions", [])
    total_weight = sum(dim_weights.get(d, 5) for d in applicable)
    passed_weight = 0
    dim_status = {}
    for d in applicable:
        dw = dim_weights.get(d, 5)
        matching = [t for t in tests if t.get("module") == module_cfg["module"] and t.get("dimension") == d]
        if not matching:
            dim_status[d] = {"status": "MISSING", "weight": dw, "reason": "No evidence"}
            continue
        passed = all(t["status"] == "passed" for t in matching)
        if passed:
            dim_status[d] = {"status": "PASSED", "weight": dw}
            passed_weight += dw
        else:
            failed = [t for t in matching if t["status"] != "passed"]
            dim_status[d] = {"status": "FAILED", "weight": dw, "reason": failed[0]["status"]}
    score = (passed_weight / total_weight * 100) if total_weight > 0 else 0
    return {"score": round(score, 1), "dimensions": dim_status, "total_weight": total_weight, "passed_weight": passed_weight}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--junit", required=True, type=Path)
    p.add_argument("--expected-sha", required=True)
    args = p.parse_args()

    head_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head_sha != args.expected_sha:
        print(f"ERROR: SHA mismatch. Expected {args.expected_sha}, got {head_sha}")
        sys.exit(1)

    cfg = load_yaml()
    tests = parse_junit(args.junit)
    modules = cfg.get("modules", [])
    cfg.get("dimension_weights", {})
    area_weights = cfg.get("area_weights", {})

    results = []
    area_scores = {}
    for mod in modules:
        m_tests = [t for t in tests if t.get("module") == mod["module"]]
        s = score_module(mod, m_tests)
        results.append({
            "module": mod["module"],
            "area": mod["area"],
            "weight": mod["module_weight"],
            "score": s["score"],
            "dimensions": s["dimensions"],
            "total_weight": s["total_weight"],
            "passed_weight": s["passed_weight"],
            "tests_count": len(m_tests),
        })
        area_scores[mod["area"]] = area_scores.get(mod["area"], 0) + s["score"] * mod["module_weight"] / 100.0

    total = 0
    for area, aw in sorted(area_weights.items(), key=lambda x: -x[1]):
        s = area_scores.get(area, 0)
        total += s * aw / 100.0

    out = {
        "sha": head_sha,
        "score": round(total, 1),
        "area_scores": {a: round(area_scores.get(a, 0), 1) for a in area_weights},
        "modules": results,
        "total_tests": len(tests),
        "passed_tests": sum(1 for t in tests if t["status"] == "passed"),
        "failed_tests": sum(1 for t in tests if t["status"] in ("failed", "error")),
    }
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
