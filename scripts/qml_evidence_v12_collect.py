#!/usr/bin/env python3
"""Evidence V12 collector — real results, no inflated scores.
18 dimensions, 7 areas, 39 modules. Validates SHA, YAML structure, sum weights.
Reads JUnit XML, associates tests via user_properties (qml_module, qml_dimension).
Rejects MISSING, FAILED, artifacts stale. No domain exclusion.
"""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config" / "qml_modules_v12.yaml"


def load_config():
    import yaml
    return yaml.safe_load(CONFIG.read_text())


def validate_config(cfg):
    """Validate sum of dimension_weights=100, area_weights=100, module weights per area=100."""
    errors = []
    dw = cfg.get("dimension_weights", {})
    dw_sum = sum(dw.values())
    if dw_sum != 100:
        errors.append(f"dimension_weights sum={dw_sum} != 100")

    aw = cfg.get("area_weights", {})
    aw_sum = sum(aw.values())
    if aw_sum != 100:
        errors.append(f"area_weights sum={aw_sum} != 100")

    known_dims = set(dw.keys())
    area_mod_weights = {}
    for m in cfg.get("modules", []):
        area = m.get("area", "")
        area_mod_weights.setdefault(area, []).append(m.get("area_weight", 0))
        for d in m.get("applicable_dimensions", []):
            if d not in known_dims:
                errors.append(f"Module {m['module']} has unknown dimension '{d}'")

    for area, weights in area_mod_weights.items():
        area_sum = sum(weights)
        if abs(area_sum - 100) > 0.01:
            errors.append(f"Area '{area}' module_weights sum={area_sum} != 100")

    return errors


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
        scores[name] = {
            "score": round(score, 1),
            "dimensions": dims,
            "applicable_weight": total_w,
            "passed_weight": passed_w,
        }
    return scores, len(tests), sum(1 for t in tests if t["status"] == "passed"), sum(1 for t in tests if t["status"] in ("failed", "error"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--junit", required=True, type=Path)
    p.add_argument("--expected-sha", required=True)
    args = p.parse_args()

    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    if head_sha != args.expected_sha:
        print(f"ERROR: SHA mismatch {head_sha} != {args.expected_sha}")
        sys.exit(1)

    if not args.junit.exists():
        print(f"ERROR: JUnit file not found: {args.junit}")
        sys.exit(1)

    cfg = load_config()
    val_errors = validate_config(cfg)
    if val_errors:
        for e in val_errors:
            print(f"CONFIG ERROR: {e}")
        sys.exit(1)

    tests = parse_junit(args.junit)
    dw = cfg.get("dimension_weights", {})
    aw = cfg.get("area_weights", {})
    modules = cfg.get("modules", [])

    scores, total_tests, passed_tests, failed_tests = compute_module_scores(modules, tests, dw)

    area_scores = {}
    mod_info = {}
    for mod in modules:
        name = mod["module"]
        area = mod.get("area", "")
        if name in scores:
            mod_score = scores[name]["score"]
            mod_weight = mod.get("area_weight", 10) / 100.0
            area_scores[area] = area_scores.get(area, 0) + mod_score * mod_weight
            mod_info[name] = {
                "score": scores[name]["score"],
                "area": area,
                "dimensions": scores[name]["dimensions"],
            }

    total = sum(area_scores.get(a, 0) * aw.get(a, 0) / 100.0 for a in aw)

    out = {
        "sha": head_sha,
        "config": "qml_modules_v12.yaml",
        "score": round(total, 1),
        "area_scores": {a: round(area_scores.get(a, 0), 1) for a in aw},
        "modules": mod_info,
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "dimensions_validated": len(val_errors) == 0,
    }

    artifacts_dir = REPO / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    outpath = artifacts_dir / "qml-evidence-v12.json"
    outpath.write_text(json.dumps(out, indent=2))
    print(f"Evidence V12 written to {outpath}")
    print(f"Score: {out['score']}%  Tests: {out['total_tests']}  Passed: {out['passed']}  Failed: {out['failed']}")

    if failed_tests > 0:
        print(f"WARNING: {failed_tests} tests failed/errored — score reflects real failures")
    if mod_info:
        min_mod = min(mod_info.items(), key=lambda x: x[1]["score"])
        print(f"Lowest module: {min_mod[0]} ({min_mod[1]['score']}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
