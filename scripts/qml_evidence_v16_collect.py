#!/usr/bin/env python3
"""Evidence V16 collector — full validation with dimensions and module scores."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def get_git_sha() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"],
                       capture_output=True, text=True,
                       cwd=Path(__file__).parent.parent)
    return r.stdout.strip()


def load_junit(path: str) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    ts = root[0] if root.tag == "testsuites" else root
    results = {"tests": int(ts.get("tests", 0)), "failures": int(ts.get("failures", 0)),
               "errors": int(ts.get("errors", 0)), "skipped": int(ts.get("skipped", 0)),
               "modules": set(), "dimensions": set()}
    for tc in ts.findall(".//testcase"):
        props = tc.find("properties")
        if props is not None:
            for p in props:
                if p.get("name") == "qml_module":
                    results["modules"].add(p.get("value", ""))
                elif p.get("name") == "qml_dimension":
                    for d in p.get("value", "").split(","):
                        if d.strip():
                            results["dimensions"].add(d.strip())
    return results


def check_placeholders(repo_root: str) -> list[str]:
    issues = []
    r = subprocess.run(
        ["git", "grep", "-n", "object()", "--",
         "core/", "michi/", "audio/", "library/", "ui_qml_bridge/"],
        capture_output=True, text=True, cwd=repo_root,
    )
    for line in r.stdout.strip().split("\n"):
        if "object()" in line and line.strip():
            issues.append(line.strip()[:100])
    r = subprocess.run(
        ["git", "grep", "-n", "lambda: None", "--",
         "core/", "michi/", "ui_qml_bridge/"],
        capture_output=True, text=True, cwd=repo_root,
    )
    for line in r.stdout.strip().split("\n"):
        if "lambda: None" in line and line.strip():
            issues.append(line.strip()[:100])
    return issues


def compute_scores(junit: dict, issues: list[str], modules: list[str]) -> dict:
    total = junit.get("tests", 0)
    failed = junit.get("failures", 0) + junit.get("errors", 0)
    test_score = max(0, round((1 - failed / max(total, 1)) * 100))
    mod_score = len(junit.get("modules", set()))
    dim_score = len(junit.get("dimensions", set()))
    placeholder_score = 100 if not issues else 0
    return {
        "test_score": test_score,
        "module_coverage": mod_score,
        "dimension_coverage": dim_score,
        "placeholder_score": placeholder_score,
        "overall": round((test_score + placeholder_score) / 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True)
    parser.add_argument("--expected-sha", default="")
    args = parser.parse_args()

    repo = Path(__file__).parent.parent
    actual = get_git_sha()
    expected = args.expected_sha or actual
    junit = load_junit(args.junit) if os.path.exists(args.junit) else {}
    issues = check_placeholders(str(repo))

    modules_config = {}
    mp = repo / "config" / "qml_modules_v16.yaml"
    if mp.exists():
        try:
            import yaml
            with open(mp) as f:
                modules_config = yaml.safe_load(f) or {}
        except Exception:
            pass

    mod_list = list(modules_config.get("modules", {}).keys())
    scores = compute_scores(junit, issues, mod_list)

    evidence = {
        "version": "v16",
        "sha": actual,
        "expected_sha": expected,
        "sha_match": actual == expected or not args.expected_sha,
        "junit": {"tests": junit.get("tests", 0), "failures": junit.get("failures", 0),
                  "errors": junit.get("errors", 0), "skipped": junit.get("skipped", 0)},
        "modules": list(junit.get("modules", set())),
        "dimensions": list(junit.get("dimensions", set())),
        "modules_expected": mod_list,
        "module_count": len(mod_list),
        "pass": junit.get("errors", 0) == 0 and junit.get("failures", 0) == 0,
        "issues": issues,
        "scores": scores,
    }

    out = repo / "artifacts" / "qml-evidence-v16.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(evidence, f, indent=2)

    print(f"Evidence V16: {out}")
    print(f"  SHA: {actual} {'✓' if evidence['sha_match'] else '✗'}")
    print(f"  Tests: {junit.get('tests')} | Fail: {junit.get('failures')} | Err: {junit.get('errors')}")
    print(f"  Modules: {evidence['module_count']}")
    print(f"  Issues: {len(issues)}")
    print(f"  Score: {scores['overall']}%")

    if not evidence["pass"] or issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
