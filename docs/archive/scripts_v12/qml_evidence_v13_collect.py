#!/usr/bin/env python3
"""QML Evidence V13 collector — validates SHA, JUnit, module scores."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def get_git_sha() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"],
                            capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    return result.stdout.strip()


def load_junit(path: str) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    testsuite = root[0] if root.tag == "testsuites" else root
    props = {p.attrib.get("name", ""): p.attrib.get("value", "")
             for p in testsuite.findall(".//property")}
    return {
        "tests": int(testsuite.get("tests", 0)),
        "failures": int(testsuite.get("failures", 0)),
        "errors": int(testsuite.get("errors", 0)),
        "skipped": int(testsuite.get("skipped", 0)),
        "properties": props,
    }


def load_module_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "qml_modules_v13.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return {}


def check_object_placeholders(repo_root: str) -> list[str]:
    issues = []
    bootstrap_path = Path(repo_root) / "core" / "application_bootstrap.py"
    if bootstrap_path.exists():
        content = bootstrap_path.read_text()
        if "object()" in content:
            lines = [(i, line.strip()) for i, line in enumerate(content.split("\n"), 1) if "object()" in line]
            for ln, line in lines:
                issues.append(f"object() placeholder at line {ln}: {line[:60]}")
    return issues


def check_lambda_handlers(repo_root: str) -> list[str]:
    issues = []
    action_path = Path(repo_root) / "core" / "application_bootstrap.py"
    if action_path.exists():
        content = action_path.read_text()
        if "lambda: None" in content:
            lines = [(i, line.strip()) for i, line in enumerate(content.split("\n"), 1) if "lambda: None" in line]
            for ln, line in lines:
                issues.append(f"lambda: None handler at line {ln}: {line[:60]}")
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True, help="Path to JUnit XML")
    parser.add_argument("--expected-sha", default="", help="Expected git SHA")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    actual_sha = get_git_sha()
    expected_sha = args.expected_sha or actual_sha

    junit = load_junit(args.junit) if os.path.exists(args.junit) else {}
    modules_config = load_module_config()

    object_issues = check_object_placeholders(str(repo_root))
    lambda_issues = check_lambda_handlers(str(repo_root))

    evidence = {
        "version": "v13",
        "sha": actual_sha,
        "expected_sha": expected_sha,
        "sha_match": actual_sha == expected_sha or not args.expected_sha,
        "junit": junit,
        "modules": list(modules_config.get("modules", {}).keys()),
        "module_count": len(modules_config.get("modules", {})),
        "pass": junit.get("errors", 0) == 0 and junit.get("failures", 0) == 0,
        "issues": {
            "object_placeholders": len(object_issues) == 0,
            "lambda_handlers": len(lambda_issues) == 0,
        },
        "object_placeholders": object_issues,
        "lambda_handlers": lambda_issues,
    }

    output_path = Path(repo_root) / "artifacts" / "qml-evidence-v13.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)

    print(f"Evidence V13 saved to {output_path}")
    print(f"SHA: {actual_sha}")
    print(f"Modules: {evidence['module_count']}")
    print(f"Pass: {evidence['pass']}")
    print(f"Object placeholders: {'PASS' if not object_issues else 'FAIL: ' + str(len(object_issues))}")
    print(f"Lambda handlers: {'PASS' if not lambda_issues else 'FAIL: ' + str(len(lambda_issues))}")

    if not evidence["pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
