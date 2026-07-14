#!/usr/bin/env python3
"""QML Evidence V8 Collector — collects markers (qml_module, qml_dimension, qml_route, qml_workflow, widget_replacement), JUnit data, produces evidence JSON."""
import argparse
import ast
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

V8_MARKERS = {"qml_module", "qml_dimension", "qml_route", "qml_workflow", "widget_replacement"}


def _extract_marker_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and node.attr in V8_MARKERS:
        return node.attr
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in V8_MARKERS:
        return node.func.attr
    return None


def _get_call_arg(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    for kw in node.keywords:
        if kw.arg in ("module", "dimension", "route", "workflow", "widget") and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    return None


def _get_enclosing_class(tree: ast.Module, func_node: ast.FunctionDef) -> str | None:
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if item is func_node:
                    return node.name
    return None


def find_marked_tests(repo: Path) -> list[dict]:
    results = []
    testdir = repo / "tests/qml"
    if not testdir.exists():
        return results
    for pyfile in sorted(testdir.rglob("test_*.py")):
        text = pyfile.read_text()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        module_markers = {}
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                name = _extract_marker_name(elt)
                                if name:
                                    module_markers[name] = _get_call_arg(elt) if isinstance(elt, ast.Call) and _get_call_arg(elt) else name
                        elif isinstance(node.value, ast.Call):
                            name = _extract_marker_name(node.value)
                            if name:
                                module_markers[name] = _get_call_arg(node.value) if _get_call_arg(node.value) else name
                        elif isinstance(node.value, ast.Attribute):
                            name = _extract_marker_name(node.value)
                            if name:
                                module_markers[name] = name
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                markers = dict(module_markers)
                for deco in node.decorator_list:
                    name = _extract_marker_name(deco)
                    if name:
                        arg = _get_call_arg(deco) if isinstance(deco, ast.Call) else name
                        markers[name] = arg or name
                if not markers:
                    continue
                cls_node = _get_enclosing_class(tree, node)
                relpath = str(pyfile.relative_to(repo))
                entry = {
                    "nodeid": f"{relpath}::{node.name}" if not cls_node else f"{relpath}::{cls_node}::{node.name}",
                    "module": markers.get("qml_module", ""),
                    "dimension": markers.get("qml_dimension", ""),
                    "route": markers.get("qml_route", ""),
                    "workflow": markers.get("qml_workflow", ""),
                    "widget": markers.get("widget_replacement", ""),
                    "file": relpath,
                    "class": cls_node or "",
                    "function": node.name,
                }
                results.append(entry)
    return results


def parse_junit(junit_path: Path) -> list[dict]:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    testcases = []
    for ts in root:
        suite_name = ts.get("name", "")
        for tc in ts:
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
        "junit_file": str(junit_path),
        "total_evidence": total_evidence,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "testcases": testcases,
        "marked_tests": marked_tests,
        "marked_test_count": len(marked_tests),
    }

    outpath = ARTIFACTS / "qml-evidence-v8.json"
    outpath.write_text(json.dumps(evidence, indent=2, default=str))
    print(f"Evidence V8 written to {outpath}")
    print(f"SHA: {sha}")
    print(f"Total evidence cases: {total_evidence}")
    print(f"Passed: {passed}, Failed: {failed}, Skipped: {skipped}")
    print(f"Marked tests (V8 markers): {len(marked_tests)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
