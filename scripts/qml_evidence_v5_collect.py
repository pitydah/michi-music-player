#!/usr/bin/env python3
"""QML Evidence V5 Collector — collect evidence from JUnit XML and test markers."""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def find_marked_tests(repo: Path) -> list[dict]:
    """Find tests decorated with @pytest.mark.qml_module or @pytest.mark.qml_dimension."""
    results = []
    testdir = repo / "tests/qml"
    if not testdir.exists():
        return results

    import ast
    for pyfile in sorted(testdir.rglob("test_*.py")):
        text = pyfile.read_text()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                markers = []
                for deco in node.decorator_list:
                    if isinstance(deco, ast.Attribute) and isinstance(deco.value, ast.Attribute) and deco.value.attr in ("qml_module", "qml_dimension"):
                        markers.append(deco.value.attr)
                    elif isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) and isinstance(deco.func.value, ast.Attribute) and deco.func.value.attr in ("qml_module", "qml_dimension"):
                        markers.append(deco.func.value.attr)
                if markers:
                    relpath = str(pyfile.relative_to(repo))
                    results.append({
                        "file": relpath,
                        "function": node.name,
                        "markers": markers,
                        "line": node.lineno,
                    })
    return results


def parse_junit(junit_path: Path) -> list[dict]:
    """Parse JUnit XML and return test case results."""
    tree = ET.parse(junit_path)
    root = tree.getroot()
    testcases = []
    for ts in root:
        suite_name = ts.get("name", "")
        for tc in ts:
            failure_el = tc.find("failure")
            skipped_el = tc.find("skipped")
            testcases.append({
                "name": tc.get("name", ""),
                "classname": tc.get("classname", ""),
                "time": float(tc.get("time", 0)),
                "failure": failure_el.text if failure_el is not None else None,
                "skipped": skipped_el is not None,
                "suite": suite_name,
            })
    return testcases


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

    testcases = parse_junit(junit_path)
    marked_tests = find_marked_tests(REPO)

    total_evidence = len(testcases)
    passed = sum(1 for tc in testcases if not tc["failure"] and not tc["skipped"])
    failed = sum(1 for tc in testcases if tc["failure"])
    skipped = sum(1 for tc in testcases if tc["skipped"])

    evidence = {
        "sha": sha,
        "junit_file": str(junit_path.resolve().relative_to(REPO)),
        "total_evidence": total_evidence,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "testcases": testcases,
        "marked_tests": marked_tests,
        "marked_test_count": len(marked_tests),
    }

    outpath = ARTIFACTS / "qml-evidence-v5.json"
    outpath.write_text(json.dumps(evidence, indent=2, default=str))
    print(f"Evidence V5 written to {outpath}")
    print(f"SHA: {sha}")
    print(f"Total evidence cases: {total_evidence}")
    print(f"Passed: {passed}, Failed: {failed}, Skipped: {skipped}")
    print(f"Marked tests (@pytest.mark.qml_module/qml_dimension): {len(marked_tests)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
