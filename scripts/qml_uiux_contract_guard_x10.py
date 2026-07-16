#!/usr/bin/env python3
"""Contract guard: detect changes to protected files, patterns, and anti-patterns."""

import argparse
import json
import os
import re
import subprocess
import sys
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXCEPTIONS_FILE = os.path.join(PROJECT_ROOT, "docs", "uiux", "X10_UIUX_CONTRACT_EXCEPTIONS.yaml")
OBJECT_NAMES_REF = None

PROTECTED_PATHS = [
    "ui_qml_bridge/",
    "core/",
    "tests/qml/productive_workflows/",
]
AUDIO_PATH = "audio/"
AUDIO_EXCEPTION_DOC = "scheduled audio refactor (see docs/audio/)"

PROHIBITED_IMPORTS = [
    "QtWidgets",
]
PROHIBITED_CREATIONS = [
    re.compile(r"(?:new\s+)?(Service|Manager|Engine|Bridge)\s*\("),
]
MOCK_DATA_PATTERN = re.compile(
    r"^\s*(ListModel|ListElement)\s*\{"
)
FAKE_SUCCESS = re.compile(
    r"\breturn\s+ok\b|\bok\s*=\s*True\b",
    re.IGNORECASE,
)


def load_exceptions():
    if os.path.isfile(EXCEPTIONS_FILE):
        try:
            with open(EXCEPTIONS_FILE) as f:
                data = yaml.safe_load(f) or {}
            return data.get("exceptions", [])
        except (yaml.YAMLError, OSError):
            return []
    return []


def is_excepted(file_rel, exceptions):
    return any(exc.get("file") == file_rel for exc in exceptions)


def check_diff(exceptions):
    violations = []
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main..."],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )

    changed_files = [f for f in result.stdout.strip().split("\n") if f]
    for f in changed_files:
        if is_excepted(f, exceptions):
            continue
        for protected in PROTECTED_PATHS:
            if f.startswith(protected):
                violations.append({
                    "type": "protected_path_change",
                    "file": f,
                    "detail": f"Changes in protected path: {protected}",
                })
        if f.startswith(AUDIO_PATH):
            violations.append({
                "type": "protected_path_change",
                "file": f,
                "detail": f"Changes in audio/ (exception: {AUDIO_EXCEPTION_DOC})",
            })

    if OBJECT_NAMES_REF and os.path.isfile(OBJECT_NAMES_REF):
        try:
            with open(OBJECT_NAMES_REF) as f:
                ref_names = set(line.strip() for line in f if line.strip())
            diff_obj = subprocess.run(
                ["git", "diff", "origin/main...", "--", "ui_qml/"],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
            added = re.findall(
                r'^\+\s*objectName\s*:\s*["\']([^"\']+)["\']',
                diff_obj.stdout, re.MULTILINE,
            )
            removed = re.findall(
                r'^-\s*objectName\s*:\s*["\']([^"\']+)["\']',
                diff_obj.stdout, re.MULTILINE,
            )
            for name in removed:
                if name in ref_names and name not in added:
                    violations.append({
                        "type": "objectName_removed",
                        "file": "ui_qml/",
                        "detail": f"objectName '{name}' removed from reference",
                    })
        except OSError:
            pass

    return violations


def full_scan(exceptions):
    violations = []
    ui_qml_dir = os.path.join(PROJECT_ROOT, "ui_qml")

    if not os.path.isdir(ui_qml_dir):
        return violations

    for root, _dirs, files in os.walk(ui_qml_dir):
        for f in files:
            if not f.endswith(".qml"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, PROJECT_ROOT)
            if is_excepted(rel, exceptions):
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    content = fh.read()
            except (OSError, UnicodeDecodeError):
                continue

            for imp in PROHIBITED_IMPORTS:
                pattern = re.compile(rf'import\s+{re.escape(imp)}\b')
                if pattern.search(content):
                    violations.append({
                        "type": "prohibited_import",
                        "file": rel,
                        "detail": f"Import of {imp} is prohibited in QML",
                    })

            for cre in PROHIBITED_CREATIONS:
                if cre.search(content):
                    violations.append({
                        "type": "service_creation",
                        "file": rel,
                        "detail": "Direct service/manager creation detected",
                    })
                    break

            if root.endswith("pages") or "/pages/" in path:
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if MOCK_DATA_PATTERN.search(line) and "ListModel" in line:
                        violations.append({
                            "type": "mock_data",
                            "file": rel,
                            "line": i,
                            "detail": "Hardcoded ListModel data in pages/",
                        })

                for i, line in enumerate(lines, 1):
                    if FAKE_SUCCESS.search(line):
                        before = lines[max(0, i - 3):i]
                        before_text = "\n".join(before)
                        if not re.search(
                            r"(verify|check|validate|confirm|test|from_backend|backend\.)",
                            before_text, re.IGNORECASE,
                        ):
                            violations.append({
                                "type": "fake_success",
                                "file": rel,
                                "line": i,
                                "detail": "Possible fake success without backend verification",
                            })

    return violations


def main():
    parser = argparse.ArgumentParser(description="Contract guard for protected QML/backend paths")
    parser.add_argument("--diff", action="store_true", help="Check diff against origin/main")
    parser.add_argument("--scan", action="store_true", help="Full scan of ui_qml/ for anti-patterns")
    args = parser.parse_args()

    if not args.diff and not args.scan:
        parser.print_help()
        sys.exit(1)

    exceptions = load_exceptions()
    all_violations = []

    if args.diff:
        all_violations.extend(check_diff(exceptions))

    if args.scan:
        all_violations.extend(full_scan(exceptions))

    if all_violations:
        report = json.dumps(all_violations, indent=2)
        print(report, file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
