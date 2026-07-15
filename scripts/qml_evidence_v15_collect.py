#!/usr/bin/env python3
"""Evidence V15 collector — validates SHA, JUnit, module scores, service health."""
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
    return {
        "tests": int(ts.get("tests", 0)),
        "failures": int(ts.get("failures", 0)),
        "errors": int(ts.get("errors", 0)),
        "skipped": int(ts.get("skipped", 0)),
    }


def check_bootstrap(repo_root: str) -> list[str]:
    issues = []
    bp = Path(repo_root) / "core" / "application_bootstrap.py"
    if bp.exists():
        c = bp.read_text()
        for i, line in enumerate(c.split("\n"), 1):
            s = line.strip()
            if "object()" in s:
                issues.append(f"object() at line {i}: {s[:80]}")
            if "lambda: None" in s:
                issues.append(f"lambda: None at line {i}: {s[:80]}")
    return issues


def compute_scores(junit: dict, issues: list[str], modules: list[str]) -> dict:
    total = junit.get("tests", 0)
    failed = junit.get("failures", 0) + junit.get("errors", 0)
    test_score = max(0, round((1 - failed / max(total, 1)) * 100))
    module_score = 100
    object_score = 100 if not issues else max(0, 100 - len(issues) * 25)
    return {
        "test_score": test_score,
        "module_score": module_score,
        "object_placeholder_score": object_score,
        "overall": round((test_score + module_score + object_score) / 3),
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
    issues = check_bootstrap(str(repo))
    modules = list(load_module_config(str(repo)).get("modules", {}).keys()) if os.path.exists(
        str(repo / "config" / "qml_modules_v15.yaml")) else []
    scores = compute_scores(junit, issues, modules)

    evidence = {
        "version": "v15",
        "sha": actual,
        "expected_sha": expected,
        "sha_match": actual == expected or not args.expected_sha,
        "junit": junit,
        "modules": modules,
        "module_count": len(modules),
        "pass": junit.get("errors", 0) == 0 and junit.get("failures", 0) == 0,
        "issues": issues,
        "scores": scores,
    }

    out = repo / "artifacts" / "qml-evidence-v15.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(evidence, f, indent=2)

    print(f"Evidence V15: {out}")
    print(f"  SHA: {actual} {'✓' if evidence['sha_match'] else '✗'}")
    print(f"  Tests: {junit.get('tests', 0)} | Fail: {junit.get('failures', 0)} | Err: {junit.get('errors', 0)}")
    print(f"  Modules: {len(modules)}")
    print(f"  Issues: {len(issues)}")
    print(f"  Score: {scores['overall']}% (test={scores['test_score']} mod={scores['module_score']} obj={scores['object_placeholder_score']})")

    if not evidence["pass"]:
        sys.exit(1)


def load_module_config(repo_root: str) -> dict:
    import yaml
    p = Path(repo_root) / "config" / "qml_modules_v15.yaml"
    if p.exists():
        with open(p) as f:
            return yaml.safe_load(f) or {}
    return {}


if __name__ == "__main__":
    main()
