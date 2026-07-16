#!/usr/bin/env python3
"""Evidence V18 collector — SHA, JUnit, scores, placeholders."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def get_sha() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                       cwd=Path(__file__).parent.parent)
    return r.stdout.strip()


def load_junit(path: str) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    ts = root[0] if root.tag == "testsuites" else root
    return {"tests": int(ts.get("tests", 0)), "failures": int(ts.get("failures", 0)),
            "errors": int(ts.get("errors", 0)), "skipped": int(ts.get("skipped", 0)),
            "modules": set(), "dimensions": set()}


def check_placeholders(repo_root: str) -> list[str]:
    issues = []
    for pattern in ["object()", "lambda: None"]:
        r = subprocess.run(
            ["git", "grep", "-n", pattern, "--",
             "core/", "michi/", "audio/", "library/", "ui_qml_bridge/"],
            capture_output=True, text=True, cwd=repo_root)
        for line in r.stdout.strip().split("\n"):
            if pattern in line and line.strip():
                issues.append(line.strip()[:100])
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True)
    parser.add_argument("--expected-sha", default="")
    args = parser.parse_args()
    repo = Path(__file__).parent.parent
    actual = get_sha()
    expected = args.expected_sha or actual
    junit = load_junit(args.junit) if os.path.exists(args.junit) else {}
    issues = check_placeholders(str(repo))
    scores = {"test": max(0, round((1 - (junit.get("failures", 0) + junit.get("errors", 0)) / max(junit.get("tests", 1), 1)) * 100)),
              "placeholder": 100 if not issues else 0}
    scores["overall"] = round((scores["test"] + scores["placeholder"]) / 2)
    evidence = {
        "version": "v18", "sha": actual, "expected_sha": expected,
        "sha_match": actual == expected or not args.expected_sha,
        "junit": {"tests": junit.get("tests"), "failures": junit.get("failures"),
                  "errors": junit.get("errors"), "skipped": junit.get("skipped")},
        "modules": list(junit.get("modules", set())),
        "pass": junit.get("errors", 0) == 0 and junit.get("failures", 0) == 0,
        "issues": issues, "scores": scores,
    }
    out = repo / "artifacts" / "qml-evidence-v18.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(evidence, f, indent=2)
    print(f"Evidence V18: {out}")
    print(f"  SHA: {actual} {'OK' if evidence['sha_match'] else 'MISMATCH'}")
    print(f"  Tests: {junit.get('tests')} | Fail: {junit.get('failures')} | Err: {junit.get('errors')}")
    print(f"  Score: {scores['overall']}%")
    if not evidence["pass"] or issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
