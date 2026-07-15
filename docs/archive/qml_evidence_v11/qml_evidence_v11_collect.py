#!/usr/bin/env python3
"""Evidence V11 collector — real results, no inflated scores."""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config" / "qml_modules.yaml"
DIMENSIONS = [
    "qml_compile", "load", "instance", "interaction", "vertical_workflow",
    "negative_paths", "service_wiring", "job_integration", "cancellation",
    "confirmation", "capability", "navigation", "accessibility", "responsive",
    "runtime_cleanup", "widget_independence",
]


def load_config():
    try:
        import yaml
        return yaml.safe_load(CONFIG.read_text())
    except Exception:
        return json.loads(CONFIG.read_text())


def parse_junit(path):
    results = []
    tree = ET.parse(path)
    for ts in tree.findall(".//testsuite"):
        for tc in ts.findall("testcase"):
            nodeid = f"{tc.get('classname', '')}::{tc.get('name', '')}"
            status = "passed"
            if tc.find("failure") is not None:
                status = "failed"
            elif tc.find("error") is not None:
                status = "error"
            elif tc.find("skipped") is not None:
                status = "skipped"
            props = {p.get("name"): p.get("value") for p in tc.findall(".//property")}
            results.append({
                "nodeid": nodeid,
                "status": status,
                "module": props.get("qml_module", ""),
                "dimension": props.get("qml_dimension", ""),
            })
    return results


def compute_module_scores(modules, tests, dim_weights):
    scores = {}
    for mod in modules:
        name = mod["module"]
        applicable = mod.get("applicable_dimensions", [])
        total_w = sum(dim_weights.get(d, 5) for d in applicable)
        passed_w = 0
        dims = {}
        for d in applicable:
            dw = dim_weights.get(d, 5)
            matching = [t for t in tests if t["module"] == name and t["dimension"] == d]
            if not matching:
                dims[d] = {"status": "MISSING", "weight": dw}
                continue
            ok = all(t["status"] == "passed" for t in matching)
            dims[d] = {"status": "PASSED" if ok else "FAILED", "weight": dw}
            if ok:
                passed_w += dw
        score = (passed_w / total_w * 100) if total_w > 0 else 0
        scores[name] = {"score": round(score, 1), "dimensions": dims, "applicable_weight": total_w, "passed_weight": passed_w}
    return scores


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--junit", required=True, type=Path)
    p.add_argument("--expected-sha", required=True)
    args = p.parse_args()

    head_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head_sha != args.expected_sha:
        print(f"ERROR: SHA mismatch {head_sha} != {args.expected_sha}")
        sys.exit(1)

    cfg = load_config()
    tests = parse_junit(args.junit)
    dw = cfg.get("dimension_weights", {d: 5 for d in DIMENSIONS})
    modules = cfg.get("modules", [])

    scores = compute_module_scores(modules, tests, dw)
    aw = cfg.get("area_weights", {})

    area_scores = {}
    for mod in modules:
        name = mod["module"]
        area = mod.get("area", "")
        if name in scores:
            area_scores[area] = area_scores.get(area, 0) + scores[name]["score"] * mod.get("module_weight", 10) / 100.0

    total = sum(area_scores.get(a, 0) * aw.get(a, 0) / 100.0 for a in aw)

    out = {
        "sha": head_sha,
        "score": round(total, 1),
        "area_scores": {a: round(area_scores.get(a, 0), 1) for a in aw},
        "modules": {m["module"]: scores.get(m["module"], {"score": 0}) for m in modules},
        "total_tests": len(tests),
        "passed": sum(1 for t in tests if t["status"] == "passed"),
        "failed": sum(1 for t in tests if t["status"] in ("failed", "error")),
    }

    outpath = REPO / "artifacts" / "qml-evidence-v11.json"
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(out, indent=2))
    print(f"Evidence V11 written to {outpath}")
    print(f"Score: {out['score']}%  Tests: {out['total_tests']}  Passed: {out['passed']}  Failed: {out['failed']}")


if __name__ == "__main__":
    main()
